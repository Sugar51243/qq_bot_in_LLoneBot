// 极简 YAML 子集解析器（零依赖）
// 仅覆盖本项目两份配置用到的语法：扁平 key: value、行内列表 [a, b]、按缩进嵌套的映射、
// 单/双引号字符串、# 注释、数字/布尔/null 标量。不支持块状 - 列表（本项目配置未用到）。
'use strict';

// 去掉注释（引号内的 # 保留）
function stripComment(line) {
  let quote = null;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (quote) {
      if (ch === quote && line[i - 1] !== '\\') quote = null;
    } else if (ch === '"' || ch === "'") {
      quote = ch;
    } else if (ch === '#') {
      return line.slice(0, i);
    }
  }
  return line;
}

function countIndent(line) {
  let n = 0;
  for (const ch of line) {
    if (ch === ' ') n += 1;
    else if (ch === '\t') n += 4;
    else break;
  }
  return n;
}

// 找引号外的第一个冒号（键值分隔符），没有则返回 -1
function findKeySep(line) {
  let quote = null;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (quote) {
      if (ch === quote && line[i - 1] !== '\\') quote = null;
    } else if (ch === '"' || ch === "'") {
      quote = ch;
    } else if (ch === ':') {
      return i;
    }
  }
  return -1;
}

function parseScalar(s) {
  if (s === null || s === undefined) return null;
  const t = s.trim();
  if (t === '' || t === 'null' || t === '~') return null;
  const quoted = t.match(/^(['"])([\s\S]*)\1$/);
  if (quoted) return quoted[2];
  if (t === 'true') return true;
  if (t === 'false') return false;
  if (/^-?\d+$/.test(t)) return parseInt(t, 10);
  if (/^-?\d+\.\d+$/.test(t)) return parseFloat(t);
  return t;
}

// 行内列表 [a, b, "c"]（支持引号内的逗号）
function parseInlineList(s) {
  const t = s.trim();
  const inner = t.match(/^\[([\s\S]*)\]$/);
  if (!inner) return null;
  if (inner[1].trim() === '') return [];
  const items = [];
  let cur = '';
  let quote = null;
  for (let i = 0; i < inner[1].length; i++) {
    const ch = inner[1][i];
    if (quote) {
      if (ch === quote && inner[1][i - 1] !== '\\') quote = null;
      cur += ch;
    } else if (ch === '"' || ch === "'") {
      quote = ch;
      cur += ch;
    } else if (ch === ',') {
      items.push(parseScalar(cur));
      cur = '';
    } else {
      cur += ch;
    }
  }
  if (cur.trim() !== '') items.push(parseScalar(cur));
  return items;
}

function parse(text) {
  const root = {};
  // 栈：按缩进维护容器（对象）路径
  const stack = [{ indent: -1, obj: root }];
  const lines = String(text).split(/\r?\n/);

  for (const raw of lines) {
    const noComment = stripComment(raw);
    if (!noComment.trim()) continue;
    const indent = countIndent(noComment);
    const line = noComment.trim();

    if (line.startsWith('- ')) {
      throw new Error(`不支持的 YAML 语法（块状列表）: ${line}`);
    }

    const sep = findKeySep(line);
    if (sep < 0) continue; // 容错：跳过无法解析的行
    const key = line.slice(0, sep).trim();
    if (!key) continue;
    const rest = line.slice(sep + 1).trim();

    // 弹出比当前缩进更深的容器
    while (stack.length > 1 && stack[stack.length - 1].indent >= indent) stack.pop();
    const cur = stack[stack.length - 1].obj;

    if (!rest) {
      const obj = {};
      cur[key] = obj;
      stack.push({ indent, obj });
    } else if (rest.startsWith('[')) {
      const list = parseInlineList(rest);
      cur[key] = list === null ? parseScalar(rest) : list;
    } else {
      cur[key] = parseScalar(rest);
    }
  }
  return root;
}

module.exports = { parse };
