// 小生物v2 网页管理面板入口（Node.js 零依赖）
// 启动：node server.js（或双击 start.bat）
// 默认仅监听 127.0.0.1；公网部署需在 web_handler/config.yaml 中设置 host: 0.0.0.0 并启用 HTTPS
'use strict';

const fs = require('node:fs');
const http = require('node:http');
const https = require('node:https');
const { loadPanelConfig, resolveOneBotUri } = require('./src/config');
const { createRouter } = require('./src/router');
const { HttpError, sendJson } = require('./src/http_util');

const LOOPBACK_HOSTS = ['127.0.0.1', 'localhost', '::1'];

function main() {
  let config;
  try {
    config = loadPanelConfig();
  } catch (e) {
    console.error('[小生物v2面板] 配置加载失败：' + e.message);
    process.exit(1);
  }
  config.onebotUri = resolveOneBotUri(config);

  const router = createRouter(config);

  const handler = (req, res) => {
    router(req, res).catch((err) => {
      if (err instanceof HttpError) {
        if (!res.headersSent) sendJson(res, err.status, { error: err.message });
        else res.end();
      } else {
        console.error('[小生物v2面板] 未处理异常：', err);
        if (!res.headersSent) sendJson(res, 500, { error: '服务器内部错误' });
        else res.end();
      }
    });
  };

  // 可选 HTTPS：httpsCert 与 httpsKey 都配置时启用（公网部署强烈建议）
  let server;
  let usingHttps = false;
  if (config.httpsCert && config.httpsKey) {
    try {
      server = https.createServer({
        cert: fs.readFileSync(config.httpsCert),
        key: fs.readFileSync(config.httpsKey),
      }, handler);
      usingHttps = true;
      config.cookieSecure = true; // HTTPS 下 Cookie 自动带 Secure
    } catch (e) {
      console.error('[小生物v2面板] 读取 HTTPS 证书/私钥失败：' + e.message);
      process.exit(1);
    }
  } else {
    server = http.createServer(handler);
  }

  // 收紧超时，缩小慢速攻击面
  server.requestTimeout = 30 * 1000;
  server.headersTimeout = 10 * 1000;

  server.on('error', (e) => {
    if (e.code === 'EADDRINUSE') {
      console.error(`[小生物v2面板] 端口 ${config.port} 已被占用，请修改 web_handler/config.yaml 的 port 字段后重启`);
      process.exit(1);
    }
    console.error('[小生物v2面板] 服务器错误：', e);
    process.exit(1);
  });

  const isLoopback = LOOPBACK_HOSTS.includes(config.host);
  server.listen(config.port, config.host, () => {
    const scheme = usingHttps ? 'https' : 'http';
    console.log('================================================');
    console.log('  小生物v2 网页管理面板已启动');
    console.log(`  访问地址：${scheme}://${config.host === '0.0.0.0' ? '127.0.0.1' : config.host}:${config.port}`);
    console.log('  管理员账号列表：' + Object.keys(config.admins).join(', '));
    if (config.generatedPassword) {
      console.log(`  [首次运行] 默认管理员 admin 的初始密码：${config.generatedPassword}`);
      console.log('  请登录后在 web_handler/config.yaml 中修改密码');
    }
    console.log(`  OneBot 地址：${config.onebotUri}`);
    console.log(`  机器人QQ静态校验值：${config.botQq || '未配置（需在 web_handler/config.yaml 填写 botQq 后才能登录）'}`);
    if (!isLoopback) {
      console.log('  ⚠⚠⚠ 面板已对公网开放（非回环地址）！请确认以下事项：');
      if (!usingHttps) console.log('  ⚠ 未启用 HTTPS：登录凭据将明文传输，强烈建议配置 httpsCert/httpsKey 或置于 nginx 等 HTTPS 反代之后');
      console.log('  ⚠ 已启用防护：登录限速（5次失败锁15分钟）、CSRF 校验、CSP、面板目录写保护');
      console.log(`  ⚠ 反代部署：若面板在 nginx 之后，请设置 trustProxy: true（否则限速按代理IP计算）`);
    }
    console.log('================================================');
  });
}

main();
