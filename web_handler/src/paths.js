// 路径安全解析（防目录穿越/符号链接逃逸）与受保护路径判定
'use strict';

const fs = require('node:fs');
const path = require('node:path');

// 项目根 = 小生物v2 目录（web_handler 的上级）
const PROJECT_ROOT = path.resolve(__dirname, '..', '..');
const WEB_HANDLER_DIR = path.resolve(__dirname, '..');
const PANEL_CONFIG = path.join(WEB_HANDLER_DIR, 'config.yaml');

const ROOT_LOWER = PROJECT_ROOT.toLowerCase();

// abs（或最近存在的祖先目录）的真实路径是否位于项目根内
function realWithinRoot(abs) {
  let cur = abs;
  try {
    const real = fs.realpathSync(cur);
    const rl = real.toLowerCase();
    return real === PROJECT_ROOT || rl.startsWith(ROOT_LOWER + path.sep.toLowerCase());
  } catch {
    // 目标不存在：向上找最近存在的祖先目录，检查其真实路径（防符号链接父目录逃逸）
    let dir = path.dirname(cur);
    while (true) {
      try {
        const real = fs.realpathSync(dir);
        const rl = real.toLowerCase();
        return real === PROJECT_ROOT || rl.startsWith(ROOT_LOWER + path.sep.toLowerCase());
      } catch {
        const parent = path.dirname(dir);
        if (parent === dir) return false;
        dir = parent;
      }
    }
  }
}

// 将客户端传入的相对路径解析为项目根内的绝对路径
function safeResolve(relPath) {
  if (typeof relPath !== 'string') return { ok: false, code: 'EINVAL' };
  if (relPath.includes('\0')) return { ok: false, code: 'EINVAL' };
  // 统一为 / 分隔，剥掉盘符与前导斜杠（绝对路径/盘符路径一律按根内相对路径处理）
  let p = relPath.replace(/\\/g, '/').replace(/^[a-zA-Z]:/, '').replace(/^\/+/, '');
  const abs = path.resolve(PROJECT_ROOT, p);
  // 前缀检查（小写比较：Windows 文件系统大小写不敏感）
  const absLower = abs.toLowerCase();
  if (abs !== PROJECT_ROOT && !absLower.startsWith(ROOT_LOWER + path.sep.toLowerCase())) {
    return { ok: false, code: 'ESCAPE' };
  }
  if (!realWithinRoot(abs)) return { ok: false, code: 'ESCAPE' };
  return { ok: true, abs };
}

// 隐藏对象：列目录时不显示（面板自身口令配置）
function isHidden(abs) {
  return abs.toLowerCase() === PANEL_CONFIG.toLowerCase();
}

// 写保护对象：一切写操作（写入/删除/重命名/新建/上传）拒绝
// 面板自身整个目录子树不可写：防止面板自毁、防止向 public/ 注入恶意脚本（存储型 XSS）
// 项目根本体不可删除
function isWriteProtected(abs) {
  if (abs === PROJECT_ROOT) return true;
  const a = abs.toLowerCase();
  const wh = WEB_HANDLER_DIR.toLowerCase();
  if (a === wh || a.startsWith(wh + path.sep.toLowerCase())) return true;
  return false;
}

// 兼容旧名：isProtected = 写保护（隐藏判定请用 isHidden）
function isProtected(abs) {
  return isWriteProtected(abs);
}

// 绝对路径 → 相对项目根的展示路径（/ 分隔）；根外路径钳制为 ''
function rel(abs) {
  const r = path.relative(PROJECT_ROOT, abs);
  if (r === '') return '';
  if (r.startsWith('..')) return '';
  return r.split(path.sep).join('/');
}

module.exports = { PROJECT_ROOT, WEB_HANDLER_DIR, PANEL_CONFIG, safeResolve, isHidden, isWriteProtected, isProtected, rel };
