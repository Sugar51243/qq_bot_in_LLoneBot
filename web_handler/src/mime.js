// 文件类型判定与 Content-Type 映射
'use strict';

const path = require('node:path');

// 可进编辑器编辑的文本类型（扩展名白名单）
const TEXT_EXT = new Set([
  '.py', '.yaml', '.yml', '.json', '.txt', '.md', '.markdown',
  '.js', '.mjs', '.cjs', '.ts', '.tsx', '.jsx',
  '.css', '.html', '.htm', '.xml', '.ini', '.cfg', '.conf', '.toml',
  '.sh', '.bat', '.cmd', '.csv', '.log', '.sql', '.properties',
  '.lock', '.env', '.gitignore', '.gitattributes',
]);

// 无扩展名但按文本处理的文件名
const TEXT_NAMES = new Set([
  'readme', 'license', 'licence', 'makefile', 'dockerfile',
  'pip.txt', 'requirements.txt', 'run.bat', '.gitignore', '.env',
]);

// 浏览器可内联预览的类型（图片/音频/视频/PDF）
const INLINE_EXT = new Set([
  '.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp', '.ico',
  '.mp3', '.wav', '.ogg', '.flac', '.m4a', '.mp4', '.webm', '.pdf',
]);

const MIME = {
  '.py': 'text/x-python', '.yaml': 'text/yaml', '.yml': 'text/yaml',
  '.json': 'application/json', '.txt': 'text/plain', '.md': 'text/markdown',
  '.js': 'text/javascript', '.mjs': 'text/javascript', '.ts': 'text/typescript',
  '.css': 'text/css', '.html': 'text/html', '.htm': 'text/html',
  '.xml': 'application/xml', '.ini': 'text/plain', '.toml': 'text/plain',
  '.sh': 'text/x-sh', '.bat': 'text/plain', '.csv': 'text/csv',
  '.log': 'text/plain', '.sql': 'text/plain',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
  '.gif': 'image/gif', '.webp': 'image/webp', '.svg': 'image/svg+xml',
  '.bmp': 'image/bmp', '.ico': 'image/x-icon',
  '.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.ogg': 'audio/ogg',
  '.flac': 'audio/flac', '.m4a': 'audio/mp4', '.mp4': 'video/mp4',
  '.webm': 'video/webm', '.pdf': 'application/pdf',
};

function extOf(name) {
  return path.extname(String(name)).toLowerCase();
}

function isTextFile(name) {
  const base = path.basename(String(name)).toLowerCase();
  const ext = path.extname(base);
  return (ext && TEXT_EXT.has(ext)) || (!ext && TEXT_NAMES.has(base));
}

function isInline(name) {
  return INLINE_EXT.has(extOf(name));
}

function isDbFile(name) {
  return extOf(name) === '.db';
}

function contentType(name) {
  return MIME[extOf(name)] || 'application/octet-stream';
}

module.exports = { isTextFile, isInline, isDbFile, contentType };
