// 路由表分发：页面认证跳转 + REST API + 错误映射
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { URL } = require('node:url');
const { sendJson, readJsonBody, readBody, httpErr } = require('./http_util');
const { verifyLogin, getSession, requireAuth, setSessionCookie, clearSessionCookie } = require('./auth');
const { safeResolve, isProtected } = require('./paths');
const fsops = require('./fsops');
const dbmod = require('./db');
const { getLoginInfo } = require('./onebot');
const { parseMultipart } = require('./multipart');
const { isInline, contentType } = require('./mime');
const { serveStatic } = require('./static');

const UPLOAD_MAX = 64 * 1024 * 1024; // 上传上限 64MB

// OneBot 在线状态缓存（仅展示用，登录核对始终实时查询）
let statusCache = { t: 0, data: null };
async function onebotStatus(config) {
  if (statusCache.data && Date.now() - statusCache.t < 5000) return statusCache.data;
  const info = await getLoginInfo(config.onebotUri, 3000);
  const data = {
    online: info.online,
    userId: info.userId != null ? info.userId : null,
    nickname: info.nickname || null,
    uri: config.onebotUri,
    error: info.error || null,
  };
  statusCache = { t: Date.now(), data };
  return data;
}

// CSRF 防线（叠加在 SameSite=Lax 之上）：浏览器请求若带 Origin/Referer，其主机必须与请求 Host 一致
function isSameOrigin(req) {
  const host = req.headers.host;
  if (!host) return true;
  const hostLower = String(host).toLowerCase();
  const check = (h) => {
    try {
      return new URL(h).host.toLowerCase() === hostLower;
    } catch {
      return false;
    }
  };
  const origin = req.headers.origin;
  if (origin !== undefined) return check(origin);
  const referer = req.headers.referer;
  if (referer !== undefined) return check(referer);
  return true; // 无来源头（curl/脚本）放行，浏览器攻击场景由 Origin 拦截
}

function mapFsError(e) {
  if (e && e.status) return e; // 已是 HttpError
  switch (e && e.code) {
    case 'ENOENT': return httpErr(404, '路径不存在');
    case 'EACCES': case 'EPERM': return httpErr(403, '没有权限访问该路径');
    case 'ENOTDIR': return httpErr(400, '路径类型错误');
    case 'EBUSY': return httpErr(409, '文件被占用，无法操作');
    case 'ENOTEMPTY': return httpErr(409, '目录非空');
    case 'ENAMETOOLONG': return httpErr(400, '文件名过长');
    case 'EISDIR': return httpErr(400, '目标是目录，不能按文件操作');
    default: return httpErr(500, '文件操作失败：' + (e && e.message));
  }
}

// 文件 API 通用：解析并校验路径（GET 走 query，POST 走 body 字符串）
function resolveFsPath(query) {
  const r = safeResolve(query.get('path') || '');
  if (!r.ok) throw httpErr(400, '非法路径');
  return r.abs;
}

function resolveFsPathFromValue(p) {
  const r = safeResolve(typeof p === 'string' ? p : '');
  if (!r.ok) throw httpErr(400, '非法路径');
  return r.abs;
}

function createRouter(config) {
  // 客户端真实 IP（仅在 trustProxy 开启时信任 X-Forwarded-For，防止伪造头绕过限速）
  function getClientIp(req) {
    if (config.trustProxy) {
      const xff = req.headers['x-forwarded-for'];
      if (xff) {
        const first = String(xff).split(',')[0].trim();
        if (first) return first;
      }
    }
    return req.socket.remoteAddress || '';
  }

  // 路由表：[method, 路径正则, 需要认证, handler(req, res, ctx)]
  // ctx: {session, query, body}
  const routes = [
    // ============ 认证 ============
    ['POST', /^\/api\/login$/, false, async (req, res, ctx) => {
      const body = await readJsonBody(req);
      const username = String(body.username == null ? '' : body.username).trim();
      const ip = getClientIp(req);
      const result = await verifyLogin(config, username, body.password, body.botQq, ip);
      if (!result.ok) {
        if (result.code === 'rate_limited') return sendJson(res, 429, { error: result.message });
        if (result.code !== 'bot_unconfigured') {
          console.log(`[小生物v2面板] 登录失败 ip=${ip} 账号=${username || '(空)'} 原因=${result.code}`);
        }
        if (result.code === 'bad_credentials') return sendJson(res, 401, { error: '账号或密码错误' });
        if (result.code === 'bot_unconfigured') {
          return sendJson(res, 403, { error: '机器人账号未配置：请先在 web_handler/config.yaml 中填写 botQq（机器人自己的QQ号）' });
        }
        if (result.onebotOnline) {
          return sendJson(res, 403, { error: `机器人账号验证失败：OneBot 实际在线账号为 ${result.onebotUserId}，与配置不符，请检查 web_handler/config.yaml 的 botQq` });
        }
        return sendJson(res, 403, { error: '机器人账号验证失败：与 web_handler/config.yaml 中配置的 botQq 不一致' });
      }
      console.log(`[小生物v2面板] 登录成功 ip=${ip} 账号=${username}`);
      setSessionCookie(res, config, username);
      sendJson(res, 200, {
        ok: true, username,
        onebotOnline: result.onebotOnline,
        onebotUserId: result.onebotUserId != null ? result.onebotUserId : null,
        nickname: result.nickname || null,
      });
    }],
    ['POST', /^\/api\/logout$/, false, (req, res) => {
      clearSessionCookie(res);
      sendJson(res, 200, { ok: true });
    }],
    ['GET', /^\/api\/session$/, true, (req, res, ctx) => {
      sendJson(res, 200, { username: ctx.session.username, expiresAt: ctx.session.expiresAt });
    }],
    ['GET', /^\/api\/onebot\/status$/, false, async (req, res) => {
      // 脱敏：未登录仅暴露在线布尔值，不泄露机器人QQ号/连接地址
      const session = getSession(req, config);
      const st = await onebotStatus(config);
      sendJson(res, 200, session ? st : { online: st.online });
    }],

    // ============ 文件管理 ============
    ['GET', /^\/api\/fs\/list$/, true, (req, res, ctx) => {
      try {
        sendJson(res, 200, fsops.listDir(resolveFsPath(ctx.query)));
      } catch (e) { throw mapFsError(e); }
    }],
    ['GET', /^\/api\/fs\/read$/, true, (req, res, ctx) => {
      try {
        sendJson(res, 200, fsops.readText(resolveFsPath(ctx.query)));
      } catch (e) { throw mapFsError(e); }
    }],
    ['GET', /^\/api\/fs\/log$/, true, (req, res, ctx) => {
      // 日志只读实时跟踪：offset=已消费字节数，tail=首次打开取尾部字节数
      try {
        sendJson(res, 200, fsops.readLogTail(
          resolveFsPath(ctx.query),
          Number(ctx.query.get('offset')) || 0,
          Number(ctx.query.get('tail')) || 0
        ));
      } catch (e) { throw mapFsError(e); }
    }],
    ['GET', /^\/api\/fs\/raw$/, true, (req, res, ctx) => {
      let abs;
      try { abs = resolveFsPath(ctx.query); } catch (e) { throw mapFsError(e); }
      let st;
      try { st = fs.statSync(abs); } catch (e) { throw mapFsError(e); }
      if (!st.isFile()) throw httpErr(400, '目标不是文件');
      const name = path.basename(abs);
      res.writeHead(200, {
        'Content-Type': contentType(name),
        'Content-Length': st.size,
        'Content-Disposition': isInline(name)
          ? 'inline'
          : `attachment; filename*=UTF-8''${encodeURIComponent(name)}`,
        'Cache-Control': 'no-store',
        'X-Content-Type-Options': 'nosniff',
      });
      const stream = fs.createReadStream(abs);
      stream.on('error', () => res.destroy());
      stream.pipe(res);
    }],
    ['POST', /^\/api\/fs\/write$/, true, async (req, res, ctx) => {
      const body = await readJsonBody(req);
      let abs;
      try { abs = resolveFsPathFromValue(body.path); }
      catch (e) { throw mapFsError(e); }
      if (isProtected(abs)) throw httpErr(403, '该路径受面板保护，禁止写入');
      try {
        const r = fsops.writeText(abs, body.content);
        sendJson(res, 200, { ok: true, size: r.size });
      } catch (e) { throw mapFsError(e); }
    }],
    ['POST', /^\/api\/fs\/mkdir$/, true, async (req, res, ctx) => {
      const body = await readJsonBody(req);
      let abs;
      try { abs = resolveFsPathFromValue(body.path); }
      catch (e) { throw mapFsError(e); }
      if (isProtected(abs)) throw httpErr(403, '该路径受面板保护，禁止操作');
      try {
        fsops.mkdir(abs);
        sendJson(res, 200, { ok: true });
      } catch (e) { throw mapFsError(e); }
    }],
    ['POST', /^\/api\/fs\/upload$/, true, async (req, res, ctx) => {
      const buf = await readBody(req, UPLOAD_MAX);
      const parsed = parseMultipart(buf, req.headers['content-type']);
      if (!parsed) throw httpErr(400, '上传格式错误（multipart/form-data）');
      const file = parsed.files.find((f) => f.field === 'file');
      if (!file) throw httpErr(400, '未找到上传文件字段 file');
      const dirPath = safeResolve(parsed.fields.path || '');
      if (!dirPath.ok) throw httpErr(400, '非法目录路径');
      const overwrite = parsed.fields.overwrite === 'true';
      try {
        const r = fsops.saveUpload(dirPath.abs, file.filename, file.data, overwrite);
        sendJson(res, 200, { ok: true, name: r.name, size: r.size });
      } catch (e) { throw mapFsError(e); }
    }],
    ['POST', /^\/api\/fs\/delete$/, true, async (req, res, ctx) => {
      const body = await readJsonBody(req);
      let abs;
      try { abs = resolveFsPathFromValue(body.path); }
      catch (e) { throw mapFsError(e); }
      try {
        fsops.remove(abs);
        sendJson(res, 200, { ok: true });
      } catch (e) { throw mapFsError(e); }
    }],
    ['POST', /^\/api\/fs\/rename$/, true, async (req, res, ctx) => {
      const body = await readJsonBody(req);
      let abs;
      try { abs = resolveFsPathFromValue(body.path); }
      catch (e) { throw mapFsError(e); }
      try {
        fsops.rename(abs, body.newName);
        sendJson(res, 200, { ok: true });
      } catch (e) { throw mapFsError(e); }
    }],

    // ============ 数据统计 ============
    ['GET', /^\/api\/stats$/, true, (req, res) => {
      // 计数由机器人运行时写入 data/db/stats.db；库不存在/读取失败一律按无数据返回（不 404）
      if (!dbmod.findDb('stats')) return sendJson(res, 200, { available: false, counters: {} });
      try {
        const db = dbmod.openDb('stats', { readOnly: true });
        try {
          const counters = {};
          for (const r of db.prepare('SELECT key, value FROM counters').all()) counters[r.key] = Number(r.value);
          sendJson(res, 200, { available: true, counters });
        } finally { db.close(); }
      } catch (e) {
        console.log(`[小生物v2面板] 读取统计失败：${e.message}`);
        sendJson(res, 200, { available: false, counters: {} });
      }
    }],

    // ============ 数据库管理 ============
    ['GET', /^\/api\/db\/list$/, true, (req, res) => {
      sendJson(res, 200, { dbs: dbmod.listDbs() });
    }],
    ['GET', /^\/api\/db\/tables$/, true, (req, res, ctx) => {
      const name = ctx.query.get('db') || '';
      const d = dbmod.findDb(name);
      if (!d) throw httpErr(404, `数据库不存在：${name}`);
      const db = dbmod.openDb(name, { readOnly: true });
      try {
        sendJson(res, 200, {
          db: name,
          dbPath: ['data', 'db', d.file].join('/'),
          tables: dbmod.listTables(db),
        });
      } finally { db.close(); }
    }],
    ['GET', /^\/api\/db\/schema$/, true, (req, res, ctx) => {
      const name = ctx.query.get('db') || '';
      const table = ctx.query.get('table') || '';
      const d = dbmod.findDb(name);
      if (!d) throw httpErr(404, `数据库不存在：${name}`);
      const db = dbmod.openDb(name, { readOnly: true });
      try {
        const info = dbmod.tableInfo(db, table);
        sendJson(res, 200, {
          db: name,
          dbPath: ['data', 'db', d.file].join('/'),
          table,
          columns: info.columns,
          count: info.count,
          indexes: dbmod.listIndexes(db, table),
        });
      } finally { db.close(); }
    }],
    ['GET', /^\/api\/db\/rows$/, true, (req, res, ctx) => {
      const name = ctx.query.get('db') || '';
      const table = ctx.query.get('table') || '';
      const db = dbmod.openDb(name, { readOnly: true });
      try {
        const r = dbmod.fetchRows(db, table, ctx.query.get('page'), ctx.query.get('pageSize'), ctx.query.get('sort'), ctx.query.get('q'));
        sendJson(res, 200, {
          db: name,
          dbPath: ['data', 'db', dbmod.findDb(name).file].join('/'),
          table,
          ...r,
        });
      } finally { db.close(); }
    }],
    ['GET', /^\/api\/db\/row$/, true, (req, res, ctx) => {
      const name = ctx.query.get('db') || '';
      const table = ctx.query.get('table') || '';
      const rowid = Number(ctx.query.get('rowid'));
      const db = dbmod.openDb(name, { readOnly: true });
      try {
        const r = dbmod.fetchRow(db, table, rowid);
        sendJson(res, 200, { db: name, table, ...r });
      } finally { db.close(); }
    }],
    ['POST', /^\/api\/db\/update$/, true, async (req, res, ctx) => {
      const body = await readJsonBody(req);
      const db = dbmod.openDb(body.db, { readOnly: false });
      try {
        dbmod.updateRow(db, body.table, Number(body.rowid), body.data);
        sendJson(res, 200, { ok: true });
      } finally { db.close(); }
    }],
    ['POST', /^\/api\/db\/insert$/, true, async (req, res, ctx) => {
      const body = await readJsonBody(req);
      const db = dbmod.openDb(body.db, { readOnly: false });
      try {
        const r = dbmod.insertRow(db, body.table, body.data);
        sendJson(res, 200, { ok: true, rowid: r.rowid });
      } finally { db.close(); }
    }],
    ['POST', /^\/api\/db\/delete$/, true, async (req, res, ctx) => {
      const body = await readJsonBody(req);
      const db = dbmod.openDb(body.db, { readOnly: false });
      try {
        dbmod.deleteRow(db, body.table, Number(body.rowid));
        sendJson(res, 200, { ok: true });
      } finally { db.close(); }
    }],
  ];

  return async function (req, res) {
    const u = new URL(req.url, 'http://xsw.local');
    const pathname = u.pathname;

    // —— 页面路由（认证跳转）——
    if (req.method === 'GET') {
      if (pathname === '/') {
        res.writeHead(302, { Location: getSession(req, config) ? '/index.html' : '/login.html' });
        res.end();
        return;
      }
      if (pathname === '/login.html') {
        if (getSession(req, config)) {
          res.writeHead(302, { Location: '/index.html' });
          res.end();
          return;
        }
        // 无会话 → 落入静态服务正常展示登录页
      } else if (pathname === '/index.html' || pathname === '/files.html' || pathname === '/db.html' || pathname === '/stats.html') {
        if (!requireAuth(req, res, config, false)) return;
      }
    }

    // —— API 路由 ——
    if (pathname.startsWith('/api/')) {
      // CSRF：所有写方法校验浏览器来源（Origin/Referer 与 Host 一致）
      if (req.method === 'POST' || req.method === 'PUT' || req.method === 'DELETE') {
        if (!isSameOrigin(req)) {
          return sendJson(res, 403, { error: '跨站请求被拒绝' });
        }
      }
      for (const [method, re, auth, handler] of routes) {
        if (req.method !== method || !re.test(pathname)) continue;
        const ctx = { query: u.searchParams, session: null, body: null };
        if (auth) {
          const session = requireAuth(req, res, config, true);
          if (!session) return;
          ctx.session = session;
        }
        return handler(req, res, ctx);
      }
    }

    // —— 静态资源 ——
    if (req.method === 'GET' || req.method === 'HEAD') {
      return serveStatic(req, res);
    }
    sendJson(res, 404, { error: '未找到该接口' });
  };
}

module.exports = { createRouter };
