// HTTP 错误与请求体读取工具（零依赖）
'use strict';

class HttpError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

function httpErr(status, message) {
  return new HttpError(status, message);
}

// 全局安全响应头（API 与页面统一）
const SECURITY_HEADERS = {
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY', // 防点击劫持（面板禁止被 iframe 嵌入）
  'Referrer-Policy': 'no-referrer',
  // CSP：脚本/连接/媒体仅同源；样式允许内联；禁止 frame 祖先与 form 外跳
  'Content-Security-Policy': [
    "default-src 'none'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data:",
    "media-src 'self'",
    "connect-src 'self'",
    "frame-src 'self'",
    "base-uri 'none'",
    "frame-ancestors 'none'",
    "form-action 'self'",
  ].join('; '),
};

function sendJson(res, status, data) {
  const body = JSON.stringify(data);
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(body),
    'Cache-Control': 'no-store',
    ...SECURITY_HEADERS,
  });
  res.end(body);
}

// 读取原始请求体，超过上限立即以 413 拒绝
function readBody(req, maxBytes) {
  return new Promise((resolve, reject) => {
    // 先看 Content-Length，超限直接拒绝，不读数据
    const cl = Number(req.headers['content-length']);
    if (Number.isFinite(cl) && cl > maxBytes) {
      reject(httpErr(413, `请求体超过 ${Math.floor(maxBytes / 1024 / 1024)}MB 上限`));
      return;
    }
    const chunks = [];
    let total = 0;
    let settled = false;
    const settle = (fn, v) => {
      if (settled) return;
      settled = true;
      fn(v);
    };
    req.on('data', (c) => {
      if (settled) return;
      total += c.length;
      if (total > maxBytes) {
        settle(reject, httpErr(413, `请求体超过 ${Math.floor(maxBytes / 1024 / 1024)}MB 上限`));
        req.destroy(); // 中止接收，客户端会看到连接中断（浏览器会放弃上传）
        return;
      }
      chunks.push(c);
    });
    req.on('end', () => settle(resolve, Buffer.concat(chunks)));
    req.on('error', (e) => settle(reject, e));
  });
}

async function readJsonBody(req, maxBytes = 2 * 1024 * 1024) {
  const buf = await readBody(req, maxBytes);
  if (buf.length === 0) return {};
  try {
    return JSON.parse(buf.toString('utf8'));
  } catch {
    throw httpErr(400, '请求体不是合法的 JSON');
  }
}

module.exports = { HttpError, httpErr, sendJson, readBody, readJsonBody, SECURITY_HEADERS };
