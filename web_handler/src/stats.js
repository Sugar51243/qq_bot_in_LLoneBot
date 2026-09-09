// 数据统计聚合（机器人写入 data/db/stats.db，本模块只读查询）
// buckets=小时桶预聚合(时序/频率)、cmd_events=指令明细(排行)、scenes=场景、counters=总次数
'use strict';

const dbmod = require('./db');

const DAY_SEC = 86400;

// 计数键 → 实际 buckets 键（含合并键）
const COUNT_KEYS = {
  msg_receive: ['msg_receive'],
  msg_send: ['msg_send'],
  msg_total: ['msg_receive', 'msg_send'],
  api_up: ['api_up'],
  api_down: ['api_down'],
  api_total: ['api_up', 'api_down'],
  cmd_trigger: ['cmd_trigger'],
};
const RANK_KEYS = ['cmd_all', 'cmd_plugin'];
const UNITS = ['hour', 'day', 'month', 'year'];

const pad = (n) => String(n).padStart(2, '0');
const localMidnight = (ts) => {
  const d = new Date(ts * 1000);
  return Math.floor(new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime() / 1000);
};

// 时间窗口起点（本地时间）
function windowStart(unit, nowSec) {
  const d = new Date(nowSec * 1000);
  if (unit === 'hour') return Math.floor(nowSec / 3600) * 3600 - 23 * 3600;
  if (unit === 'day') return Math.floor(new Date(d.getFullYear(), d.getMonth(), d.getDate() - 29).getTime() / 1000);
  if (unit === 'month') return Math.floor(new Date(d.getFullYear(), d.getMonth() - 11, 1).getTime() / 1000);
  return null; // year：全量，由数据决定起点
}

// 生成完整时间序列键（与 strftime 输出格式一致）与显示标签
function buildSeries(unit, fromSec, toSec) {
  const keys = [];
  const labels = [];
  if (unit === 'hour') {
    for (let ts = fromSec; ts <= toSec; ts += 3600) {
      const d = new Date(ts * 1000);
      keys.push(`${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:00`);
      labels.push(`${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:00`);
    }
  } else if (unit === 'day') {
    for (let ts = fromSec; ts <= toSec; ts += DAY_SEC) {
      const d = new Date(ts * 1000);
      keys.push(`${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`);
      labels.push(`${pad(d.getMonth() + 1)}-${pad(d.getDate())}`);
    }
  } else if (unit === 'month') {
    const d = new Date(fromSec * 1000);
    for (let i = 0; i < 12; i++) {
      const m = new Date(d.getFullYear(), d.getMonth() + i, 1);
      keys.push(`${m.getFullYear()}-${pad(m.getMonth() + 1)}`);
      labels.push(`${m.getFullYear()}-${pad(m.getMonth() + 1)}`);
    }
  } else { // year
    const fromY = new Date(fromSec * 1000).getFullYear();
    const toY = new Date(toSec * 1000).getFullYear();
    for (let y = fromY; y <= toY; y++) {
      keys.push(String(y));
      labels.push(String(y));
    }
  }
  return { keys, labels };
}

const FMT = { hour: '%Y-%m-%d %H:00', day: '%Y-%m-%d', month: '%Y-%m', year: '%Y' };

// 计数/场景类时间序列（服务端补零，点 ≤30）
function readCountSeries(db, keyExpr, keyParams, unit, nowSec, fromTable = 'buckets', kind = null) {
  const from = windowStart(unit, nowSec);
  const whereCol = fromTable === 'buckets' ? 'bucket_ts' : 'first_ts';
  let sql = `SELECT strftime('${FMT[unit]}', ${whereCol}, 'unixepoch', 'localtime') d, ${fromTable === 'buckets' ? 'SUM(n)' : 'COUNT(*)'} n FROM ${fromTable} WHERE ${keyExpr}`;
  const params = [...keyParams];
  if (kind) { sql += ' AND kind = ?'; params.push(kind); }
  if (from != null) { sql += ` AND ${whereCol} >= ?`; params.push(from); }
  sql += ' GROUP BY 1 ORDER BY 1';
  const rows = db.prepare(sql).all(...params);
  const map = new Map(rows.map((r) => [r.d, Number(r.n)]));

  let fromSec = from;
  if (fromSec == null) {
    // year：起点取数据最早年份（无数据则空序列）
    const first = rows.length ? rows[0].d : null;
    if (!first) return { buckets: [], total: 0 };
    fromSec = Math.floor(new Date(Number(first), 0, 1).getTime() / 1000);
  }
  const { keys, labels } = buildSeries(unit, fromSec, Math.min(nowSec, Math.floor(Date.now() / 1000)));
  const buckets = keys.map((k, i) => ({ t: labels[i], n: map.get(k) || 0 }));
  return { buckets, total: buckets.reduce((s, b) => s + b.n, 0) };
}

// 汇总（主页/统计页卡片数据）
function readStatsSummary() {
  if (!dbmod.findDb('stats')) return { available: false, counters: {} };
  const db = dbmod.openDb('stats', { readOnly: true });
  try {
    const counters = {};
    for (const r of db.prepare('SELECT key, value FROM counters').all()) counters[r.key] = Number(r.value);

    // 频率 = 历史日均 = 总量 ÷ 统计天数（自首次桶起，不足 1 天按 1 天）
    const now = Math.floor(Date.now() / 1000);
    const mins = {};
    for (const r of db.prepare('SELECT key, MIN(bucket_ts) m FROM buckets GROUP BY key').all()) mins[r.key] = Number(r.m);
    const since = { ...mins };
    const days = (k) => (mins[k] != null ? Math.max((now - mins[k]) / DAY_SEC, 1) : null);
    const freqVal = (k) => (days(k) != null ? Math.round((100 * (counters[k] || 0)) / days(k)) / 100 : null);
    // 合并键（收发总计）取两键较早 MIN
    const minOf = (a, b) => {
      const vals = [mins[a], mins[b]].filter((v) => v != null);
      return vals.length ? Math.min(...vals) : null;
    };
    const msgTotalDays = (() => {
      const m = minOf('msg_receive', 'msg_send');
      return m != null ? Math.max((now - m) / DAY_SEC, 1) : null;
    })();
    const freq = {
      msg_receive: freqVal('msg_receive'),
      msg_send: freqVal('msg_send'),
      msg_total: msgTotalDays != null ? Math.round((100 * ((counters.msg_receive || 0) + (counters.msg_send || 0))) / msgTotalDays) / 100 : null,
      cmd_trigger: freqVal('cmd_trigger'),
    };

    // 排行 top3
    const top3 = (key) => db.prepare(
      'SELECT name, COUNT(*) n FROM cmd_events WHERE key = ? GROUP BY name ORDER BY n DESC, name LIMIT 3'
    ).all(key).map((r) => ({ name: r.name, n: Number(r.n) }));

    // 场景计数
    const scenes = { group: 0, private: 0 };
    for (const r of db.prepare('SELECT kind, COUNT(*) c FROM scenes GROUP BY kind').all()) scenes[r.kind] = Number(r.c);
    scenes.total = scenes.group + scenes.private;

    return {
      available: true,
      counters,
      scenes,
      scenesEnabled: readScenesEnabled(),
      freq,
      top: { cmd_all: top3('cmd_all'), cmd_plugin: top3('cmd_plugin') },
      since,
    };
  } finally { db.close(); }
}

// 已启用插件场景数（permissions.db；群聊 = scene_id LIKE 'group_%'，私聊 = 其余）
function readScenesEnabled() {
  if (!dbmod.findDb('permissions')) return { group: 0, private: 0, total: 0 };
  const db = dbmod.openDb('permissions', { readOnly: true });
  try {
    const group = Number(db.prepare(
      "SELECT COUNT(DISTINCT scene_id) c FROM permission_records WHERE enabled = 1 AND scene_id LIKE 'group_%'"
    ).get().c);
    const total = Number(db.prepare(
      'SELECT COUNT(DISTINCT scene_id) c FROM permission_records WHERE enabled = 1'
    ).get().c);
    return { group, private: total - group, total };
  } finally { db.close(); }
}

// 详情（时序折线 / 排行 / 场景增长）
function readStatsDetail(key, unit, kind) {
  if (!UNITS.includes(unit)) throw Object.assign(new Error('非法时间单位'), { status: 400 });
  const now = Math.floor(Date.now() / 1000);
  const db = dbmod.openDb('stats', { readOnly: true });
  try {
    if (COUNT_KEYS[key]) {
      const keys = COUNT_KEYS[key];
      const keyExpr = keys.length === 1 ? 'key = ?' : `key IN (${keys.map(() => '?').join(', ')})`;
      const r = readCountSeries(db, keyExpr, keys, unit, now, 'buckets', null);
      const from = windowStart(unit, now);
      return {
        key, unit, kindType: 'count',
        window: from != null ? { from, to: now } : null,
        total: r.total,
        buckets: r.buckets,
      };
    }
    if (key === 'scene_new') {
      if (kind != null && !['group', 'private'].includes(kind)) throw Object.assign(new Error('非法场景类型'), { status: 400 });
      const r = readCountSeries(db, '1=1', [], unit, now, 'scenes', kind);
      const from = windowStart(unit, now);
      return {
        key, unit, kindType: 'count',
        window: from != null ? { from, to: now } : null,
        total: r.total,
        buckets: r.buckets,
      };
    }
    if (RANK_KEYS.includes(key)) {
      const from = windowStart(unit, now) || 0;
      const rows = db.prepare(
        'SELECT name, COUNT(*) n FROM cmd_events WHERE key = ? AND ts >= ? GROUP BY name ORDER BY n DESC, name LIMIT 10'
      ).all(key, from).map((r) => ({ name: r.name, n: Number(r.n), top: [] }));
      let total = 0;
      for (const row of rows) {
        total += row.n;
        if (key === 'cmd_plugin') {
          row.top = db.prepare(
            'SELECT cmd, COUNT(*) n FROM cmd_events WHERE key = ? AND name = ? AND ts >= ? AND cmd != \'\' GROUP BY cmd ORDER BY n DESC, cmd LIMIT 3'
          ).all(key, row.name, from).map((x) => ({ cmd: x.cmd, n: Number(x.n) }));
        }
      }
      return { key, unit, kindType: 'rank', window: { from, to: now }, total, rows };
    }
    throw Object.assign(new Error('未知统计项'), { status: 400 });
  } finally { db.close(); }
}

module.exports = { readStatsSummary, readStatsDetail };
