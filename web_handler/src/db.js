// SQLite 数据库管理（node:sqlite，零依赖）
// 只读操作使用 readOnly 连接避免写锁；写操作 busy_timeout + 一次重试，与 Python 端并发共存
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { DatabaseSync } = require('node:sqlite');
const { PROJECT_ROOT } = require('./paths');
const { httpErr } = require('./http_util');

const DB_DIR = path.join(PROJECT_ROOT, 'data', 'db');
const CELL_TRUNC = 100 * 1024; // 单元格截断阈值 100KB
const PAGE_MAX = 1000;

// SQL 标识符双引号转义（库名/表名已过白名单，此层为最后防线）
function q(name) {
  return '"' + String(name).replace(/"/g, '""') + '"';
}

function sleepSync(ms) {
  try {
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
  } catch { /* 环境不支持时直接返回 */ }
}

function isBusyError(e) {
  if (!e) return false;
  if (e.errcode === 5 || e.code === 'SQLITE_BUSY') return true;
  return /busy|locked/i.test(String(e.errstr || e.message || ''));
}

function mapDbError(e) {
  const m = String((e && e.message) || '');
  if (/NOT NULL|UNIQUE|CHECK|FOREIGN KEY|datatype|constraint/i.test(m)) {
    throw httpErr(400, '写入失败（约束检查未通过）：' + m);
  }
  if (isBusyError(e)) throw httpErr(503, '数据库忙（机器人可能正在写入），请重试');
  throw httpErr(500, '数据库操作失败：' + m);
}

function withRetry(fn) {
  try {
    return fn();
  } catch (e) {
    if (isBusyError(e)) {
      sleepSync(300);
      try {
        return fn();
      } catch (e2) {
        if (isBusyError(e2)) throw httpErr(503, '数据库忙（机器人可能正在写入），请重试');
        throw mapDbError(e2);
      }
    }
    throw mapDbError(e);
  }
}

// 列出 data/db 下所有数据库文件（库名白名单的唯一来源，防任意路径）
function listDbs() {
  if (!fs.existsSync(DB_DIR)) return [];
  return fs.readdirSync(DB_DIR)
    .filter((n) => n.toLowerCase().endsWith('.db'))
    .map((n) => {
      const p = path.join(DB_DIR, n);
      const st = fs.statSync(p);
      return {
        name: n.slice(0, -3), // 去掉 .db 作为库名
        file: n,
        size: st.size,
        mtimeMs: Math.round(st.mtimeMs),
      };
    })
    .sort((a, b) => a.name.localeCompare(b.name, 'zh-Hans-CN'));
}

function findDb(name) {
  return listDbs().find((d) => d.name === name) || null;
}

// 打开数据库（库名必须命中白名单；连接用完由调用方 close）
function openDb(name, { readOnly = false } = {}) {
  const d = findDb(name);
  if (!d) throw httpErr(404, `数据库不存在：${name}`);
  const db = new DatabaseSync(path.join(DB_DIR, d.file), { readOnly });
  db.exec('PRAGMA busy_timeout = 5000'); // 等待 Python 端写锁释放（不改 journal_mode，保持对方行为）
  return db;
}

function listTables(db) {
  return db.prepare(
    `SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name`
  ).all().map((r) => r.name);
}

function assertTable(db, table) {
  if (!listTables(db).includes(table)) throw httpErr(404, `表不存在：${table}`);
}

function tableInfo(db, table) {
  assertTable(db, table);
  const cols = db.prepare(`PRAGMA table_info(${q(table)})`).all();
  const count = db.prepare(`SELECT COUNT(*) AS c FROM ${q(table)}`).get();
  return {
    columns: cols.map((c) => ({ name: c.name, type: c.type, notnull: !!c.notnull, pk: !!c.pk })),
    count: count.c,
  };
}

// 列出表的所有索引（含主键/唯一约束自动索引），供前端"按索引排序"预设。
// 用 index_xinfo 保留各键列的声明方向（DESC 索引），并过滤掉非键列（INCLUDE 列/隐式 rowid）。
function listIndexes(db, table) {
  assertTable(db, table);
  return db.prepare(`PRAGMA index_list(${q(table)})`).all().map((ix) => ({
    name: ix.name,
    unique: !!ix.unique,
    origin: ix.origin,
    cols: db.prepare(`PRAGMA index_xinfo(${q(ix.name)})`).all()
      .filter((c) => c.key)
      .sort((a, b) => a.seqno - b.seqno)
      .map((c) => ({ name: c.name, desc: !!c.desc })),
  }));
}

// 单元格序列化：大文本截断（truncate=true）、BLOB 标记、bigint 转 number
function serializeCell(v, truncate) {
  if (v === null || typeof v === 'number' || typeof v === 'boolean') return v;
  if (typeof v === 'bigint') return Number(v);
  if (typeof v === 'string') {
    if (truncate && v.length > CELL_TRUNC) return { __truncated: true, value: v.slice(0, CELL_TRUNC) };
    return v;
  }
  if (v instanceof Uint8Array) {
    return { __blob: Buffer.from(v).toString('base64'), size: v.length };
  }
  return String(v);
}

function serializeRow(row, truncate = true) {
  const out = {};
  for (const [k, v] of Object.entries(row)) out[k] = serializeCell(v, truncate);
  return out;
}

// 解析排序参数（JSON 数组 [{col, dir}]，最多 5 列），并校验列名（rowid 伪列允许）
function parseSort(raw, columns) {
  if (!raw) return [];
  let arr;
  try { arr = JSON.parse(raw); } catch { throw httpErr(400, '排序参数格式错误'); }
  if (!Array.isArray(arr) || !arr.length || arr.length > 5) throw httpErr(400, '排序参数格式错误');
  const names = columns.map((c) => c.name);
  return arr.map((s) => {
    const colOk = typeof s === 'object' && s !== null && typeof s.col === 'string' &&
      (names.includes(s.col) || s.col === 'rowid');
    if (!colOk) throw httpErr(400, '排序参数格式错误');
    return { col: s.col, dir: s.dir === 'desc' ? 'desc' : 'asc' };
  });
}

// 关键词过滤：对全列（含 rowid）做大小写不敏感（ASCII）子串匹配。
// LIKE 特殊字符（% _ \）转义后按字面匹配；返回 null 表示无过滤。
function buildFilter(qRaw, columns) {
  const kw = String(qRaw == null ? '' : qRaw).trim().slice(0, 200);
  if (!kw) return null;
  const esc = kw.replace(/[\\%_]/g, (m) => '\\' + m);
  const pattern = '%' + esc + '%';
  const targets = ['rowid', ...columns.map((c) => c.name)];
  return {
    where: ' WHERE ' + targets.map((t) => `CAST(${q(t)} AS TEXT) LIKE ? ESCAPE '\\'`).join(' OR '),
    params: targets.map(() => pattern),
    kw,
  };
}

// 分页读取行（所有表均为普通 rowid 表，以 rowid 定位；排序以 rowid 兜底保证翻页稳定）
function fetchRows(db, table, page, pageSize, sortRaw, qRaw) {
  const info = tableInfo(db, table);
  const sort = parseSort(sortRaw, info.columns);
  const filter = buildFilter(qRaw, info.columns);
  const p = Math.max(1, Math.floor(Number(page)) || 1);
  const ps = Math.min(PAGE_MAX, Math.max(1, Math.floor(Number(pageSize)) || 100));
  const offset = (p - 1) * ps;
  const orderSql = sort.length
    ? sort.map((s) => `${q(s.col)} ${s.dir === 'desc' ? 'DESC' : 'ASC'}`).join(', ') + ', rowid'
    : 'rowid';
  const where = filter ? filter.where : '';
  const whereParams = filter ? filter.params : [];
  const total = filter
    ? withRetry(() => db.prepare(`SELECT COUNT(*) AS c FROM ${q(table)}${where}`).get(...whereParams)).c
    : info.count;
  const rows = withRetry(() =>
    db.prepare(`SELECT rowid AS _rowid, * FROM ${q(table)}${where} ORDER BY ${orderSql} LIMIT ? OFFSET ?`)
      .all(...whereParams, ps, offset)
  );
  return {
    columns: info.columns,
    rows: rows.map((r) => serializeRow(r)),
    total, // 过滤后行数（分页依据）
    unfilteredTotal: filter ? info.count : null,
    q: filter ? filter.kw : '',
    page: p,
    pageSize: ps,
    sort,
  };
}

// 读取单行（不截断，供编辑弹窗取完整值）
function fetchRow(db, table, rowid) {
  const info = tableInfo(db, table);
  if (!Number.isSafeInteger(rowid)) throw httpErr(400, '非法的行 ID');
  const row = withRetry(() =>
    db.prepare(`SELECT rowid AS _rowid, * FROM ${q(table)} WHERE rowid = ?`).get(rowid)
  );
  if (!row) throw httpErr(404, '该行不存在（可能已被删除）');
  return { columns: info.columns, row: serializeRow(row) };
}

// 值类型收窄：仅接受 number/string/null
function normalizeValue(v) {
  if (v === null || v === undefined) return null;
  if (typeof v === 'number' && Number.isFinite(v)) return v;
  if (typeof v === 'string') return v;
  throw httpErr(400, '不支持的值类型');
}

// 收集列更新数据（跳过 rowid 伪列；未知列直接报错）
function collectData(table, columns, data) {
  const names = columns.map((c) => c.name);
  const out = [];
  for (const [k, v] of Object.entries(data || {})) {
    if (k === '_rowid' || k === 'rowid') continue;
    if (!names.includes(k)) throw httpErr(400, `未知列：${k}`);
    out.push([k, normalizeValue(v)]);
  }
  return out;
}

function updateRow(db, table, rowid, data) {
  if (!Number.isSafeInteger(rowid)) throw httpErr(400, '非法的行 ID');
  const info = tableInfo(db, table);
  const pairs = collectData(table, info.columns, data);
  if (!pairs.length) throw httpErr(400, '没有需要更新的列');
  const sets = pairs.map(([k]) => `${q(k)} = ?`).join(', ');
  const params = pairs.map(([, v]) => v);
  params.push(rowid);
  return withRetry(() => db.prepare(`UPDATE ${q(table)} SET ${sets} WHERE rowid = ?`).run(...params));
}

function insertRow(db, table, data) {
  const info = tableInfo(db, table);
  const pairs = collectData(table, info.columns, data)
    .filter(([k, v]) => !(v === null || v === '')); // 空值跳过 → 使用默认值（如 INTEGER 主键自动分配）
  const sql = pairs.length
    ? `INSERT INTO ${q(table)} (${pairs.map(([k]) => q(k)).join(', ')}) VALUES (${pairs.map(() => '?').join(', ')})`
    : `INSERT INTO ${q(table)} DEFAULT VALUES`;
  const params = pairs.map(([, v]) => v);
  const res = withRetry(() => db.prepare(sql).run(...params));
  return { rowid: Number(res.lastInsertRowid) };
}

function deleteRow(db, table, rowid) {
  if (!Number.isSafeInteger(rowid)) throw httpErr(400, '非法的行 ID');
  assertTable(db, table);
  return withRetry(() => db.prepare(`DELETE FROM ${q(table)} WHERE rowid = ?`).run(rowid));
}

module.exports = { DB_DIR, listDbs, findDb, openDb, listTables, tableInfo, listIndexes, fetchRows, fetchRow, updateRow, insertRow, deleteRow };
