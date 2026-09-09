// 登录校验（管理员密码 + 机器人账号混合验证）与会话签发/校验
'use strict';

const crypto = require('node:crypto');
const { getLoginInfo } = require('./onebot');
const { sendJson } = require('./http_util');

const COOKIE_NAME = 'xsw_panel_session';

function sha256(s) {
  return crypto.createHash('sha256').update(String(s), 'utf8').digest();
}

function sha256Hex(s) {
  return crypto.createHash('sha256').update(String(s), 'utf8').digest('hex');
}

const delay = (ms) => new Promise((r) => setTimeout(r, ms));

// 管理员密码比对（哈希后 timingSafeEqual，防时序侧信道；不区分"用户不存在/密码错"防枚举）
// 支持两种存储格式：明文，或 "sha256:<hex>" 哈希（公网部署建议用哈希）
function checkPassword(config, username, password) {
  const expect = config.admins[username];
  if (!expect) return false;
  const given = String(password == null ? '' : password);
  if (expect.startsWith('sha256:')) {
    const want = expect.slice(7).toLowerCase();
    const got = sha256Hex(given);
    const a = Buffer.from(want, 'utf8');
    const b = Buffer.from(got, 'utf8');
    return a.length === b.length && crypto.timingSafeEqual(a, b);
  }
  const a = sha256(expect);
  const b = sha256(given);
  return crypto.timingSafeEqual(a, b);
}

// —— 登录限速（防暴力破解；内存计数，单进程生效）——
const FAIL_WINDOW = 10 * 60 * 1000; // 计数窗口 10 分钟
const USER_LIMIT = 5; // 每(IP+账号)窗口内允许失败次数
const IP_LIMIT = 20; // 每 IP 窗口内允许失败次数
const LOCK_MS = 15 * 60 * 1000; // 超限后锁 15 分钟
const failMap = new Map();

function normIp(ip) {
  let s = String(ip || 'unknown');
  if (s.startsWith('::ffff:')) s = s.slice(7);
  return s;
}

function pruneFailMap() {
  if (failMap.size < 10000) return;
  const now = Date.now();
  for (const [k, v] of failMap) {
    if (now - v.first > FAIL_WINDOW + LOCK_MS) failMap.delete(k);
  }
}

function checkRateAllowed(ip, user) {
  const now = Date.now();
  const key = normIp(ip) + '|' + user;
  const u = failMap.get(key);
  if (u && now - u.first < FAIL_WINDOW && u.count >= USER_LIMIT) {
    return { allowed: false, msg: '该账号登录失败次数过多，请 15 分钟后再试' };
  }
  const i = failMap.get(normIp(ip));
  if (i && now - i.first < FAIL_WINDOW && i.count >= IP_LIMIT) {
    return { allowed: false, msg: '当前网络登录失败次数过多，请稍后再试' };
  }
  return { allowed: true };
}

function recordFailure(ip, user) {
  const now = Date.now();
  pruneFailMap();
  const key = normIp(ip) + '|' + user;
  let u = failMap.get(key);
  if (!u || now - u.first > FAIL_WINDOW) {
    u = { count: 0, first: now };
    failMap.set(key, u);
  }
  u.count++;
  let i = failMap.get(normIp(ip));
  if (!i || now - i.first > FAIL_WINDOW) {
    i = { count: 0, first: now };
    failMap.set(normIp(ip), i);
  }
  i.count++;
}

function recordSuccess(ip, user) {
  failMap.delete(normIp(ip) + '|' + user); // 成功登录清除该账号失败计数
}

// 混合验证流程：
//   1. 限速检查（防暴力破解，先于一切验证）
//   2. 管理员账号密码必须正确
//   3. botQq 必须已配置（0 = 未配置，拒绝）
//   4. 静态比对：输入 == config.botQq
//   5. 实时核对：OneBot 在线 → 真实账号必须与 config.botQq 一致（双重保险）；离线 → 仅静态通过
// 失败统一附加 600ms 延迟拖慢暴力尝试；成功清除失败计数
async function verifyLogin(config, username, password, botQq, ip) {
  const user = username == null ? '' : String(username).trim();
  const rate = checkRateAllowed(ip, user);
  if (!rate.allowed) {
    await delay(600);
    return { ok: false, code: 'rate_limited', message: rate.msg };
  }
  if (!user || !checkPassword(config, user, password)) {
    recordFailure(ip, user);
    await delay(600);
    return { ok: false, code: 'bad_credentials' };
  }
  if (!config.botQq) {
    return { ok: false, code: 'bot_unconfigured' }; // 配置问题不计入失败
  }
  const givenQq = String(botQq == null ? '' : botQq).trim();
  const staticQq = String(config.botQq);
  if (givenQq !== staticQq) {
    recordFailure(ip, user);
    await delay(600);
    return { ok: false, code: 'bot_mismatch', onebotOnline: false };
  }
  const info = await getLoginInfo(config.onebotUri, 3000);
  if (info.online) {
    if (String(info.userId) !== staticQq) {
      recordFailure(ip, user);
      return { ok: false, code: 'bot_mismatch', onebotOnline: true, onebotUserId: info.userId };
    }
    recordSuccess(ip, user);
    return { ok: true, onebotOnline: true, onebotUserId: info.userId, nickname: info.nickname };
  }
  recordSuccess(ip, user);
  return { ok: true, onebotOnline: false, onebotError: info.error };
}

// —— 会话（HMAC 签名 Cookie，无服务端状态，Cookie 即自动登录凭证）——

function createSession(config, username) {
  // 注意：HMAC 必须对 base64url 编码后的 payload 计算（与 verifySession 保持一致）
  const payload = Buffer.from(
    JSON.stringify({ u: username, e: Date.now() + config.sessionDays * 86400e3 }),
    'utf8'
  ).toString('base64url');
  const sig = crypto.createHmac('sha256', config.sessionSecret).update(payload, 'utf8').digest('base64url');
  return payload + '.' + sig;
}

function verifySession(config, token) {
  if (typeof token !== 'string') return null;
  const idx = token.indexOf('.');
  if (idx <= 0) return null;
  const payloadPart = token.slice(0, idx);
  const sig = token.slice(idx + 1);
  const expect = crypto.createHmac('sha256', config.sessionSecret).update(payloadPart, 'utf8').digest('base64url');
  const a = Buffer.from(expect);
  const b = Buffer.from(sig);
  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return null;
  let payload;
  try {
    payload = JSON.parse(Buffer.from(payloadPart, 'base64url').toString('utf8'));
  } catch {
    return null;
  }
  if (!payload || typeof payload.u !== 'string' || typeof payload.e !== 'number') return null;
  if (payload.e < Date.now()) return null;
  if (!config.admins[payload.u]) return null; // 管理员已从配置移除 → 会话立即失效
  return { username: payload.u, expiresAt: payload.e };
}

function parseCookies(req) {
  const out = {};
  const h = req.headers.cookie;
  if (!h) return out;
  for (const part of h.split(';')) {
    const eq = part.indexOf('=');
    if (eq < 0) continue;
    out[part.slice(0, eq).trim()] = part.slice(eq + 1).trim();
  }
  return out;
}

function getSession(req, config) {
  const token = parseCookies(req)[COOKIE_NAME];
  return token ? verifySession(config, token) : null;
}

function setSessionCookie(res, config, username) {
  const token = createSession(config, username);
  // 本机 http 访问时不能加 Secure（浏览器会直接丢弃）；HTTPS/反代部署时由 cookieSecure 控制
  const secure = config.cookieSecure ? '; Secure' : '';
  res.setHeader('Set-Cookie',
    `${COOKIE_NAME}=${token}; HttpOnly; SameSite=Lax; Max-Age=${config.sessionDays * 86400}; Path=/${secure}`);
  return token;
}

function clearSessionCookie(res) {
  res.setHeader('Set-Cookie', `${COOKIE_NAME}=; HttpOnly; SameSite=Lax; Max-Age=0; Path=/`);
}

// 认证中间件：页面未登录 302 → /login.html；API 未登录 401
function requireAuth(req, res, config, isApi) {
  const session = getSession(req, config);
  if (!session) {
    if (isApi) {
      sendJson(res, 401, { error: '未登录或登录已过期' });
    } else {
      res.writeHead(302, { Location: '/login.html' });
      res.end();
    }
    return null;
  }
  return session;
}

module.exports = {
  verifyLogin, createSession, verifySession, getSession,
  setSessionCookie, clearSessionCookie, requireAuth, COOKIE_NAME,
};
