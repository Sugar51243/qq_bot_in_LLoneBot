// 面板配置加载（web_handler/config.yaml）+ 根项目 OneBot uri 的降级链解析
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { parse: parseYaml } = require('./yaml');
const { PROJECT_ROOT } = require('./paths');

const CONFIG_PATH = path.resolve(__dirname, '..', 'config.yaml');

const DEFAULTS = {
  port: 8570,
  host: '127.0.0.1', // 仅本机；公网部署需显式改为 0.0.0.0
  botQq: 0,
  onebotUri: '',
  sessionDays: 30,
  httpsCert: '', // HTTPS 证书/私钥路径（PEM）；两者都填才启用 HTTPS
  httpsKey: '',
  cookieSecure: false, // 经 HTTPS 反代部署时设为 true（直接启用 httpsCert 时自动生效）
  trustProxy: false, // 仅在可信反代（nginx等）之后设为 true，登录限速才按真实IP计算
};

function randomHex(bytes) {
  return crypto.randomBytes(bytes).toString('hex');
}

function collectAdmins(raw) {
  const admins = {};
  if (raw && typeof raw === 'object' && !Array.isArray(raw)) {
    for (const [u, p] of Object.entries(raw)) {
      if (typeof p === 'string' && p.trim() !== '') admins[u.trim()] = p;
    }
  }
  return admins;
}

function normalizePort(v) {
  const n = Number(v);
  return Number.isInteger(n) && n >= 1 && n <= 65535 ? n : DEFAULTS.port;
}

// 允许的监听地址：回环、通配或合法 IP（防止配置笔误把面板绑到别处）
function normalizeHost(v) {
  const h = String(v == null ? '' : v).trim();
  if (/^(127\.0\.0\.1|localhost|0\.0\.0\.0|::|::1)$/.test(h)) return h;
  if (/^(\d{1,3}\.){3}\d{1,3}$/.test(h)) return h; // IPv4 点分形式
  return DEFAULTS.host;
}

function normalizeBotQq(v) {
  if (typeof v === 'string') {
    const t = v.trim();
    if (t === '') return 0;
    const n = Number(t);
    return Number.isFinite(n) ? n : 0;
  }
  const n = Number(v);
  return Number.isFinite(n) ? n : DEFAULTS.botQq;
}

// 生成完整的规范 config.yaml（仅首次生成/重建时使用）
function writeConfig(out) {
  const lines = [
    '# ============ 小生物v2 网页管理面板配置 ============',
    '# 修改本文件后需重启面板（双击 start.bat 或 node server.js）生效',
    '',
    '# 面板 HTTP 监听端口',
    `port: ${out.port}`,
    '',
    '# 监听地址：127.0.0.1=仅本机（默认，安全）；公网部署改为 0.0.0.0（务必配合 HTTPS）',
    `host: ${JSON.stringify(out.host)}`,
    '',
    '# 管理员列表（用户名: 密码），支持多个管理员；密码明文存放于本文件，改密即编辑本文件',
    '# 本文件已被项目根 .gitignore 的 config.yaml 模式自动忽略，不会被 git 提交',
    'admins:',
  ];
  for (const [u, p] of Object.entries(out.admins)) lines.push(`  ${u}: ${JSON.stringify(p)}`);
  lines.push(
    '',
    '# 机器人账号静态校验值：机器人自己的 QQ 号（登录页"机器人账号"的比对基准）',
    '# 0 表示未配置，此时禁止登录',
    `botQq: ${out.botQq}`,
    '',
    '# OneBot WS 地址；留空则自动按顺序解析：',
    '#   1) 项目根 config.yaml 的 uri  2) samples/onebot_config.json 的 uri  3) ws://127.0.0.1:3001',
    `onebotUri: ${JSON.stringify(out.onebotUri)}`,
    '',
    '# 会话签名密钥：面板首次启动自动生成，请勿泄露、勿改动（改动后所有已登录会话失效）',
    `sessionSecret: ${JSON.stringify(out.sessionSecret)}`,
    '',
    '# 登录会话有效期（天），浏览器 Cookie 在此期限内自动登录',
    `sessionDays: ${out.sessionDays}`,
    '',
    '# HTTPS 证书文件路径（PEM）；httpsCert 与 httpsKey 都填写才启用 HTTPS',
    `httpsCert: ${JSON.stringify(out.httpsCert)}`,
    '# HTTPS 私钥文件路径（PEM）',
    `httpsKey: ${JSON.stringify(out.httpsKey)}`,
    '# 会话 Cookie 加 Secure 标记：经 HTTPS 反代部署时设为 true（启用 httpsCert 时自动生效）',
    `cookieSecure: ${out.cookieSecure}`,
    '# 是否信任反向代理的 X-Forwarded-For（仅在可信反代之后设为 true，登录限速才按真实IP计算）',
    `trustProxy: ${out.trustProxy}`,
    '',
  );
  fs.writeFileSync(CONFIG_PATH, lines.join('\n'), 'utf8');
}

// 已有配置文件中补齐/替换缺失的 sessionSecret（尽量保留原文件其余内容与注释）
function patchSecret(secret) {
  let text = fs.readFileSync(CONFIG_PATH, 'utf8');
  if (/^\s*sessionSecret\s*:/m.test(text)) {
    text = text.replace(/^(\s*sessionSecret\s*:\s*).*$/m, `$1${JSON.stringify(secret)}`);
  } else {
    text = text.replace(/\s*$/, '') +
      `\n\n# 会话签名密钥：面板首次启动自动生成，请勿泄露、勿改动（改动后所有已登录会话失效）\nsessionSecret: ${JSON.stringify(secret)}\n`;
  }
  fs.writeFileSync(CONFIG_PATH, text, 'utf8');
}

// 已有配置文件末尾追加管理员（当现有 admins 为空时使用）
function appendAdmin(username, password) {
  let text = fs.readFileSync(CONFIG_PATH, 'utf8');
  text = text.replace(/\s*$/, '') +
    `\n\n# 自动追加的默认管理员（原配置中 admins 为空）\nadmins:\n  ${username}: ${JSON.stringify(password)}\n`;
  fs.writeFileSync(CONFIG_PATH, text, 'utf8');
}

// 已有配置文件补齐缺失的新增字段（保留原有内容与注释）
const EXTRA_KEYS_DOC = [
  ['host', '# 面板 HTTP 监听地址：127.0.0.1=仅本机；公网部署需改为 0.0.0.0（务必配合 HTTPS 使用）'],
  ['httpsCert', '# HTTPS 证书文件路径（PEM）；httpsCert 与 httpsKey 都填写才启用 HTTPS'],
  ['httpsKey', '# HTTPS 私钥文件路径（PEM）'],
  ['cookieSecure', '# 会话 Cookie 加 Secure 标记：经 HTTPS 反代部署时设为 true（启用 httpsCert 时自动生效）'],
  ['trustProxy', '# 是否信任反向代理的 X-Forwarded-For（仅在可信反代之后设为 true，登录限速才按真实IP计算）'],
];
function appendMissingKeys(parsed) {
  let text = fs.readFileSync(CONFIG_PATH, 'utf8');
  const missing = EXTRA_KEYS_DOC.filter(([key]) => !(key in parsed));
  if (!missing.length) return;
  let add = '';
  for (const [key, doc] of missing) add += `\n${doc}\n${key}: ${JSON.stringify(DEFAULTS[key])}\n`;
  fs.writeFileSync(CONFIG_PATH, text.replace(/\s*$/, '') + '\n\n# ===== 以下字段由面板自动补齐 =====\n' + add, 'utf8');
}

// 加载面板配置；缺失的 secret/管理员自动生成并写回
function loadPanelConfig() {
  let cfg = null;
  let fileExists = false;
  try {
    const text = fs.readFileSync(CONFIG_PATH, 'utf8');
    fileExists = true;
    const parsed = parseYaml(text);
    if (parsed && typeof parsed === 'object') cfg = parsed;
    else throw new Error('解析结果为空');
  } catch (e) {
    if (fileExists) {
      // 文件存在但无法解析：宁可报错退出，也不覆盖用户手写的配置
      throw new Error(`web_handler/config.yaml 无法解析（${e.message}），请检查文件格式后重试`);
    }
    cfg = null;
  }
  if (!cfg) cfg = {};

  const out = {
    port: normalizePort(cfg.port),
    host: normalizeHost(cfg.host),
    onebotUri: typeof cfg.onebotUri === 'string' ? cfg.onebotUri.trim() : '',
    botQq: normalizeBotQq(cfg.botQq),
    sessionDays: (() => {
      const n = Number(cfg.sessionDays);
      return Number.isFinite(n) && n > 0 ? Math.min(365, Math.floor(n)) : DEFAULTS.sessionDays;
    })(),
    admins: collectAdmins(cfg.admins),
    httpsCert: typeof cfg.httpsCert === 'string' ? cfg.httpsCert.trim() : '',
    httpsKey: typeof cfg.httpsKey === 'string' ? cfg.httpsKey.trim() : '',
    cookieSecure: !!cfg.cookieSecure,
    trustProxy: !!cfg.trustProxy,
  };

  if (fileExists) appendMissingKeys(cfg); // 补齐新字段到磁盘配置（保留原有内容）

  let generatedPassword = null;
  let needFullWrite = false;

  if (!Object.keys(out.admins).length) {
    generatedPassword = randomHex(9); // 18 位十六进制
    out.admins = { admin: generatedPassword };
    if (fileExists) appendAdmin('admin', generatedPassword);
    else needFullWrite = true;
  }

  let secret = typeof cfg.sessionSecret === 'string' ? cfg.sessionSecret.trim() : '';
  if (!secret) {
    secret = randomHex(32);
    if (fileExists && !needFullWrite) patchSecret(secret);
    else needFullWrite = true;
  }
  out.sessionSecret = secret;
  out.generatedPassword = generatedPassword;

  if (needFullWrite) writeConfig(out);
  return out;
}

// OneBot WS 地址降级链：面板配置 → 根 config.yaml → samples/onebot_config.json → 默认值
function resolveOneBotUri(panelCfg) {
  if (panelCfg.onebotUri) return panelCfg.onebotUri;
  try {
    const text = fs.readFileSync(path.join(PROJECT_ROOT, 'config.yaml'), 'utf8');
    const cfg = parseYaml(text);
    if (cfg && typeof cfg.uri === 'string' && cfg.uri.trim()) return cfg.uri.trim();
  } catch { /* 根 config.yaml 缺失或解析失败，继续降级 */ }
  try {
    const j = JSON.parse(fs.readFileSync(path.join(PROJECT_ROOT, 'samples', 'onebot_config.json'), 'utf8'));
    if (j && typeof j.uri === 'string' && j.uri.trim()) return j.uri.trim();
  } catch { /* 样本缺失，继续降级 */ }
  return 'ws://127.0.0.1:3001';
}

module.exports = { loadPanelConfig, resolveOneBotUri, CONFIG_PATH };
