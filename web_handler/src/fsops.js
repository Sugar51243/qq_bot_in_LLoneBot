// 文件系统操作：列目录/读文本/写文本/建目录/递归删除/改名/保存上传
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { isHidden, isWriteProtected, rel } = require('./paths');
const { isTextFile, isInline, isDbFile } = require('./mime');
const { httpErr } = require('./http_util');

const MAX_TEXT = 2 * 1024 * 1024; // 文本读写上限 2MB
const MAX_LIST = 10000; // 单目录列出上限
const LOG_TAIL = 1 * 1024 * 1024; // 日志首次打开只取尾部 1MB
const LOG_CHUNK = 2 * 1024 * 1024; // 日志单次增量读取上限，超过则跳到最新尾部

// Windows 保留名与非法字符校验（新建/改名/上传共用）
const RESERVED = /^(con|prn|aux|nul|com[1-9]|lpt[1-9])(\..*)?$/i;
function sanitizeName(raw) {
  const name = String(raw == null ? '' : raw).trim();
  if (!name || name === '.' || name === '..') throw httpErr(400, '非法的文件名');
  if (name.length > 200) throw httpErr(400, '文件名过长（超过 200 字符）');
  if (/[\\/:*?"<>|]/.test(name)) throw httpErr(400, '文件名包含非法字符 \\ / : * ? " < > |');
  if (/[. ]$/.test(name)) throw httpErr(400, '文件名不能以空格或点结尾');
  if (RESERVED.test(name)) throw httpErr(400, `"${name}" 是 Windows 保留名，无法使用`);
  return name;
}

function listDir(abs) {
  const st = fs.statSync(abs);
  if (!st.isDirectory()) throw httpErr(400, '目标不是目录');
  const names = fs.readdirSync(abs);
  const entries = [];
  for (const name of names) {
    const child = path.join(abs, name);
    if (isHidden(child)) continue; // 隐藏面板自身口令配置
    try {
      const cs = fs.statSync(child);
      entries.push({
        name,
        type: cs.isDirectory() ? 'dir' : 'file',
        size: cs.size,
        mtimeMs: Math.round(cs.mtimeMs),
        ext: path.extname(name).toLowerCase(),
        isDb: cs.isFile() && isDbFile(name),
        editable: cs.isFile() && isTextFile(name) && cs.size <= MAX_TEXT,
        preview: cs.isFile() && isInline(name),
        writable: !isWriteProtected(child), // 面板自身目录只读，防止自毁/静态资源投毒
      });
    } catch { /* 单个条目读取失败跳过 */ }
  }
  entries.sort((a, b) => {
    if (a.type !== b.type) return a.type === 'dir' ? -1 : 1;
    return a.name.localeCompare(b.name, 'zh-Hans-CN');
  });
  const truncated = entries.length > MAX_LIST;
  if (truncated) entries.length = MAX_LIST;
  return {
    path: rel(abs),
    parent: rel(path.dirname(abs)),
    truncated,
    writable: !isWriteProtected(abs),
    entries,
  };
}

function readText(abs) {
  const st = fs.statSync(abs);
  if (!st.isFile()) throw httpErr(400, '目标不是文件');
  if (!isTextFile(path.basename(abs))) throw httpErr(415, '该类型文件不支持在线编辑（可能是二进制）');
  if (st.size > MAX_TEXT) throw httpErr(413, '文件超过 2MB，请下载后本地查看');
  const buf = fs.readFileSync(abs);
  try {
    // fatal: true → 含非法 UTF-8 字节即判为二进制，拒绝编辑
    const content = new TextDecoder('utf-8', { fatal: true }).decode(buf).replace(/^﻿/, '');
    return { path: rel(abs), content };
  } catch {
    throw httpErr(415, '文件包含非文本内容（可能是二进制），不支持在线编辑');
  }
}

// 日志只读实时查看：从 offset（字节）起增量读取。返回 truncated=true 表示
// 跳过了部分内容（首次截尾 / 文件被轮转清空 / 增量过大），前端应重置视图。
function readLogTail(abs, offset, tail) {
  const st = fs.statSync(abs);
  if (!st.isFile()) throw httpErr(400, '目标不是文件');
  if (!isTextFile(path.basename(abs))) throw httpErr(415, '该类型文件不支持日志查看');
  let start = Number.isInteger(offset) && offset > 0 ? offset : 0;
  let truncated = false;
  const firstTail = Number.isInteger(tail) && tail > 0 ? Math.min(tail, LOG_TAIL) : LOG_TAIL;
  if (start === 0 && st.size > firstTail) {
    start = st.size - firstTail; // 首次打开：大文件只取尾部
    truncated = true;
  } else if (start > st.size) {
    start = Math.max(0, st.size - firstTail); // 文件被轮转/清空
    truncated = true;
  }
  if (st.size - start > LOG_CHUNK) {
    start = st.size - LOG_CHUNK; // 瞬间大量写入：跳到最新窗口
    truncated = true;
  }
  const len = st.size - start;
  let content = '';
  if (len > 0) {
    const buf = Buffer.alloc(len);
    const fd = fs.openSync(abs, 'r');
    try {
      let pos = 0;
      while (pos < len) {
        const n = fs.readSync(fd, buf, pos, len - pos, start + pos);
        if (n <= 0) break;
        pos += n;
      }
    } finally {
      fs.closeSync(fd);
    }
    // 起始处可能截断多字节字符：跳过 UTF-8 续字节（10xxxxxx）
    let i = 0;
    while (i < buf.length && (buf[i] & 0xc0) === 0x80) i++;
    if (i > 0) truncated = true;
    content = new TextDecoder('utf-8', { fatal: false })
      .decode(buf.subarray(i)).replace(/^﻿/, '');
  }
  return {
    path: rel(abs),
    size: st.size,
    mtimeMs: Math.round(st.mtimeMs),
    offset: st.size, // 已消费到文件末尾，下次从此继续
    content,
    truncated,
  };
}

function writeText(abs, content) {
  if (isWriteProtected(abs)) throw httpErr(403, '该路径受面板保护，禁止写入');
  if (typeof content !== 'string') throw httpErr(400, '内容必须是字符串');
  const buf = Buffer.from(content, 'utf8');
  if (buf.length > MAX_TEXT) throw httpErr(413, '内容超过 2MB，无法保存');
  fs.mkdirSync(path.dirname(abs), { recursive: true }); // 父目录不存在时自动创建
  fs.writeFileSync(abs, buf);
  return { size: buf.length };
}

function mkdir(abs) {
  if (isWriteProtected(abs)) throw httpErr(403, '该路径受面板保护，禁止操作');
  if (fs.existsSync(abs)) throw httpErr(409, '同名目录或文件已存在');
  fs.mkdirSync(abs); // 父目录必须存在，ENOENT 由路由层转为提示
}

function remove(abs) {
  if (isWriteProtected(abs)) throw httpErr(403, '该路径受面板保护，禁止删除');
  if (!fs.existsSync(abs)) throw httpErr(404, '目标不存在');
  try {
    fs.rmSync(abs, { recursive: true, force: false });
  } catch (e) {
    if (e.code === 'EBUSY' || e.code === 'EPERM' || e.code === 'ENOTEMPTY') {
      throw httpErr(409, '文件被占用或权限不足，无法删除');
    }
    throw e;
  }
}

function rename(abs, newName) {
  if (isWriteProtected(abs)) throw httpErr(403, '该路径受面板保护，禁止重命名');
  const name = sanitizeName(newName);
  if (!fs.existsSync(abs)) throw httpErr(404, '目标不存在');
  const dest = path.join(path.dirname(abs), name);
  if (isWriteProtected(dest)) throw httpErr(403, '目标路径受面板保护，禁止写入'); // 防改名覆盖面板口令配置
  if (fs.existsSync(dest)) throw httpErr(409, '同名文件已存在');
  fs.renameSync(abs, dest);
}

function saveUpload(dirAbs, rawFilename, buf, overwrite = false) {
  const name = sanitizeName(rawFilename);
  const dest = path.join(dirAbs, name);
  if (isWriteProtected(dest)) throw httpErr(403, '该路径受面板保护，禁止写入');
  if (!fs.existsSync(dirAbs) || !fs.statSync(dirAbs).isDirectory()) throw httpErr(404, '目标目录不存在');
  if (fs.existsSync(dest)) {
    if (!overwrite) throw httpErr(409, `"${name}" 已存在，是否覆盖？`);
    fs.rmSync(dest, { recursive: true, force: false });
  }
  fs.writeFileSync(dest, buf);
  return { name, size: buf.length };
}

module.exports = { listDir, readText, readLogTail, writeText, mkdir, remove, rename, saveUpload, sanitizeName, MAX_TEXT };
