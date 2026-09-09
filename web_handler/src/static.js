// public/ 静态资源服务（防穿越、HTML 一律 no-store 防缓存）
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { URL } = require('node:url');
const { contentType } = require('./mime');
const { SECURITY_HEADERS } = require('./http_util');

const PUBLIC_DIR = path.resolve(__dirname, '..', 'public');
const ROOT_LOWER = PUBLIC_DIR.toLowerCase() + path.sep.toLowerCase();

function serveStatic(req, res) {
  let pathname;
  try {
    pathname = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  } catch {
    res.writeHead(400, { 'Content-Type': 'text/plain; charset=utf-8' });
    res.end('请求路径编码错误');
    return;
  }
  if (pathname === '/') pathname = '/index.html';
  const abs = path.resolve(PUBLIC_DIR, '.' + pathname.split('/').join(path.sep));
  const absLower = abs.toLowerCase();
  if (absLower !== PUBLIC_DIR.toLowerCase() && !absLower.startsWith(ROOT_LOWER)) {
    res.writeHead(403, { 'Content-Type': 'text/plain; charset=utf-8' });
    res.end('Forbidden');
    return;
  }
  fs.stat(abs, (err, st) => {
    if (err || !st.isFile()) {
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
      res.end('Not Found');
      return;
    }
    const headers = {
      'Content-Type': contentType(abs),
      'Content-Length': st.size,
      ...SECURITY_HEADERS,
    };
    if (absLower.endsWith('.html')) headers['Cache-Control'] = 'no-store';
    res.writeHead(200, headers);
    if (req.method === 'HEAD') {
      res.end();
      return;
    }
    const stream = fs.createReadStream(abs);
    stream.on('error', () => res.destroy());
    stream.pipe(res);
  });
}

module.exports = { serveStatic };
