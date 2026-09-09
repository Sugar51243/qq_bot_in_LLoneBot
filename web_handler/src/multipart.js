// 零依赖 multipart/form-data 解析（Buffer 级边界切分）
// 支持：Content-Disposition 的 name/filename（含 filename*=UTF-8'' 百分号编码）
'use strict';

function decodePartName(s) {
  try {
    return decodeURIComponent(s.replace(/\+/g, ' '));
  } catch {
    return s;
  }
}

// buffer 中从头查找指定子串的索引（Buffer.indexOf 需要子 Buffer，用循环实现安全搜索）
function parseMultipart(buffer, contentTypeHeader) {
  const m = /boundary=(?:"([^"]+)"|([^;]+))/i.exec(String(contentTypeHeader || ''));
  if (!m) return null;
  const boundary = '--' + (m[1] || m[2]).trim();
  const bBuf = Buffer.from(boundary, 'utf8');

  // 收集所有边界出现位置
  const starts = [];
  let from = 0;
  while (true) {
    const idx = buffer.indexOf(bBuf, from);
    if (idx < 0) break;
    starts.push(idx);
    from = idx + bBuf.length;
  }
  if (starts.length < 2) return null;

  const fields = {};
  const files = [];
  const CRLF = Buffer.from('\r\n');

  for (let i = 0; i < starts.length - 1; i++) {
    let seg = buffer.subarray(starts[i] + bBuf.length, starts[i + 1]);
    // 去边界后的 \r\n（首段）与结尾 \r\n（末段）
    if (seg.subarray(0, 2).equals(CRLF)) seg = seg.subarray(2);
    if (seg.length >= 2 && seg.subarray(seg.length - 2).equals(CRLF)) seg = seg.subarray(0, seg.length - 2);

    const headerEnd = seg.indexOf(CRLF + CRLF); // 头部与正文之间是 \r\n\r\n
    if (headerEnd < 0) continue;
    const headersText = seg.subarray(0, headerEnd).toString('utf8');
    const body = seg.subarray(headerEnd + 4);

    const cd = /content-disposition:\s*form-data[^\r\n]*/i.exec(headersText);
    if (!cd) continue;
    const nameM = /;\s*name="([^"]*)"/.exec(cd[0]);
    if (!nameM) continue;
    const fieldName = nameM[1];
    const fileAscii = /;\s*filename="([^"]*)"/.exec(cd[0]);
    const fileUtf8 = /;\s*filename\*=utf-8''([^;\r\n]*)/i.exec(cd[0]);

    if (fileAscii || fileUtf8) {
      let filename = fileUtf8 ? decodePartName(fileUtf8[1]) : fileAscii[1];
      // 去掉 filename 中可能的路径部分（浏览器一般只发文件名，双保险）
      filename = filename.replace(/\\/g, '/').split('/').pop();
      files.push({ field: fieldName, filename, data: body });
    } else {
      fields[fieldName] = body.toString('utf8');
    }
  }
  return { fields, files };
}

module.exports = { parseMultipart };
