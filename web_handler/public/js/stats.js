// 数据统计页逻辑：分类分区卡片 + 详情弹窗（年/月/日/小时 · 折线图/文本）
'use strict';

(function () {
  const sectionsEl = document.getElementById('stats-sections');
  const timeEl = document.getElementById('stat-time');

  loadTopbar('stats.html');

  // ==== 分区与卡片定义 ====
  // kind: num=总次数 / freq=频率(条/day) / top=排行预览（top3）
  // detail: 点击打开的详情 {key, kind(场景过滤), defaultUnit}
  const c = (d) => d.counters || {};
  const SECTIONS = [
    {
      title: '消息与接口', desc: '信息 = QQ 消息收发；接口 = 与 OneBot 的全部协议流量（不含心跳）',
      tiles: [
        { label: '信息接收次数', kind: 'num', get: (d) => c(d).msg_receive, detail: { key: 'msg_receive' } },
        { label: '信息发送次数', kind: 'num', get: (d) => c(d).msg_send, detail: { key: 'msg_send' } },
        { label: '信息接收发送总次数', kind: 'num', get: (d) => (c(d).msg_receive || 0) + (c(d).msg_send || 0), detail: { key: 'msg_total' } },
        { label: '信息接收频率', kind: 'freq', get: (d) => d.freq.msg_receive, detail: { key: 'msg_receive' } },
        { label: '信息发送频率', kind: 'freq', get: (d) => d.freq.msg_send, detail: { key: 'msg_send' } },
        { label: '信息收发总频率', kind: 'freq', get: (d) => d.freq.msg_total, detail: { key: 'msg_total' } },
        { label: '接口上行次数', kind: 'num', get: (d) => c(d).api_up, detail: { key: 'api_up' } },
        { label: '接口下行次数', kind: 'num', get: (d) => c(d).api_down, detail: { key: 'api_down' } },
        { label: '接口上下行总次数', kind: 'num', get: (d) => (c(d).api_up || 0) + (c(d).api_down || 0), detail: { key: 'api_total' } },
      ],
    },
    {
      title: '指令', desc: '指令触发 = 被核心内置功能或插件成功处理的消息事件',
      tiles: [
        { label: '指令触发次数', kind: 'num', get: (d) => c(d).cmd_trigger, detail: { key: 'cmd_trigger' } },
        { label: '指令触发频率', kind: 'freq', get: (d) => d.freq.cmd_trigger, detail: { key: 'cmd_trigger' } },
        { label: '最常触发指令（不计插件）', kind: 'top', get: (d) => d.top.cmd_all, detail: { key: 'cmd_all', defaultUnit: 'month' } },
        { label: '最常触发指令（按插件分类）', kind: 'top', get: (d) => d.top.cmd_plugin, detail: { key: 'cmd_plugin', defaultUnit: 'month' } },
      ],
    },
    {
      title: '场景', desc: '群聊场景来自 get_group_list 轮询（计入接口下行）与消息事件；私聊场景自统计上线累计',
      tiles: [
        { label: '已添加场景数', kind: 'num', get: (d) => (d.scenes ? d.scenes.total : null), detail: { key: 'scene_new' } },
        { label: '群聊场景数', kind: 'num', get: (d) => (d.scenes ? d.scenes.group : null), detail: { key: 'scene_new', kind: 'group' } },
        { label: '私聊场景数', kind: 'num', get: (d) => (d.scenes ? d.scenes.private : null), detail: { key: 'scene_new', kind: 'private' } },
        { label: '已启用插件场景数', kind: 'num', get: (d) => (d.scenesEnabled ? d.scenesEnabled.total : null) },
        { label: '已启用插件群聊场景数', kind: 'num', get: (d) => (d.scenesEnabled ? d.scenesEnabled.group : null) },
        { label: '已启用插件私聊场景数', kind: 'num', get: (d) => (d.scenesEnabled ? d.scenesEnabled.private : null) },
      ],
    },
  ];

  const UNITS = [['year', '年'], ['month', '月'], ['day', '日'], ['hour', '小时']];
  const UNIT_WINDOW = { hour: '最近 24 小时', day: '最近 30 天', month: '最近 12 个月', year: '全部' };

  // ==== 分区渲染 ====
  const num = (v) => (v == null ? '—' : Number(v).toLocaleString('zh-CN'));

  function renderSections(data) {
    if (!data || !data.available) {
      sectionsEl.innerHTML = '<div class="empty-hint">暂无统计数据（机器人尚未运行或尚未产生统计）</div>';
      return;
    }
    sectionsEl.innerHTML = SECTIONS.map((sec) => `
      <section class="stats-section">
        <div class="stats-section-head">
          <h3>${escapeHtml(sec.title)}</h3>
          <span class="fmeta">${escapeHtml(sec.desc)}</span>
        </div>
        <div class="stat-grid">
          ${sec.tiles.map((t) => renderTile(t, data)).join('')}
        </div>
      </section>`).join('');
    sectionsEl.querySelectorAll('.stat-tile[data-detail]').forEach((el) => {
      el.addEventListener('click', () => {
        const t = JSON.parse(el.getAttribute('data-detail'));
        openDetail(t.title, t.detail);
      });
    });
  }

  function renderTile(t, data) {
    const val = t.get(data);
    let body;
    if (t.kind === 'top') {
      const rows = val || [];
      body = rows.length
        ? `<div class="stat-top">${rows.map((r, i) => `<div class="stat-top-row"><span class="rank-i">${i + 1}.</span><span class="rank-name">${escapeHtml(r.name)}</span><span class="rank-n">×${num(r.n)}</span></div>`).join('')}</div>`
        : '<div class="stat-num">—</div>';
    } else if (t.kind === 'freq') {
      body = `<div class="stat-num">${num(val)}</div><div class="stat-unit">条/day</div>`;
    } else {
      body = `<div class="stat-num">${num(val)}</div>`;
    }
    const clickable = t.detail ? ` data-detail="${escapeHtml(JSON.stringify({ title: t.label, detail: t.detail }))}"` : '';
    return `<div class="stat-tile${t.detail ? ' clickable' : ''}"${clickable}>
      ${body}
      <div class="stat-label">${escapeHtml(t.label)}</div>
    </div>`;
  }

  // ==== 详情弹窗 ====
  function openDetail(title, opts) {
    const isRank = opts.key === 'cmd_all' || opts.key === 'cmd_plugin';
    const isScene = opts.key === 'scene_new';
    const { overlay, close } = showModal(`
      <div class="modal-box wide detail-modal">
        <div class="detail-head">
          <h3>${escapeHtml(title)}</h3>
          <span class="fmeta" id="d-window"></span>
          <span class="spacer"></span>
          <button class="btn small" data-act="close">关闭</button>
        </div>
        <div class="detail-controls">
          <span class="seg-group" id="d-units">
            ${UNITS.map(([u, label]) => `<button class="btn small seg-btn" data-unit="${u}">${label}</button>`).join('')}
          </span>
          ${isScene ? `<span class="seg-group" id="d-kinds">
            <button class="btn small seg-btn" data-kind="">全部</button>
            <button class="btn small seg-btn" data-kind="group">群聊</button>
            <button class="btn small seg-btn" data-kind="private">私聊</button>
          </span>` : ''}
          ${isRank ? '' : `<span class="seg-group" id="d-modes">
            <button class="btn small seg-btn" data-mode="chart">折线图</button>
            <button class="btn small seg-btn" data-mode="text">文本</button>
          </span>`}
        </div>
        <div class="detail-body" id="d-body"><div class="empty-hint">加载中…</div></div>
      </div>`);
    let unit = opts.defaultUnit || (isRank ? 'month' : 'day');
    let mode = isRank ? 'text' : 'chart';
    let kind = opts.kind || null;
    const bodyEl = overlay.querySelector('#d-body');
    const winEl = overlay.querySelector('#d-window');

    const markUnits = () => {
      overlay.querySelectorAll('#d-units .seg-btn').forEach((b) => b.classList.toggle('active', b.getAttribute('data-unit') === unit));
    };
    const markKinds = () => {
      overlay.querySelectorAll('#d-kinds .seg-btn').forEach((b) => b.classList.toggle('active', (b.getAttribute('data-kind') || null) === kind));
    };
    const markModes = () => {
      overlay.querySelectorAll('#d-modes .seg-btn').forEach((b) => b.classList.toggle('active', b.getAttribute('data-mode') === mode));
    };
    const load = async () => {
      markUnits(); markKinds(); markModes();
      winEl.textContent = '范围：' + UNIT_WINDOW[unit];
      bodyEl.innerHTML = '<div class="empty-hint">加载中…</div>';
      let url = `/api/stats/detail?key=${encodeURIComponent(opts.key)}&unit=${encodeURIComponent(unit)}`;
      if (isScene && kind) url += '&kind=' + encodeURIComponent(kind);
      try {
        const r = await api(url);
        if (r.kindType === 'rank') renderRank(bodyEl, r);
        else renderCount(bodyEl, mode, r);
      } catch (err) {
        bodyEl.innerHTML = `<div class="empty-hint">加载失败：${escapeHtml(err.message)}</div>`;
      }
    };

    overlay.querySelector('#d-units').addEventListener('click', (e) => {
      const b = e.target.closest('.seg-btn');
      if (!b) return;
      unit = b.getAttribute('data-unit');
      load();
    });
    if (isScene) {
      overlay.querySelector('#d-kinds').addEventListener('click', (e) => {
        const b = e.target.closest('.seg-btn');
        if (!b) return;
        kind = b.getAttribute('data-kind') || null;
        load();
      });
    }
    if (!isRank) {
      overlay.querySelector('#d-modes').addEventListener('click', (e) => {
        const b = e.target.closest('.seg-btn');
        if (!b) return;
        mode = b.getAttribute('data-mode');
        load();
      });
    }
    overlay.querySelector('[data-act="close"]').addEventListener('click', close);
    load();
  }

  // ==== 详情渲染 ====
  function renderCount(bodyEl, mode, r) {
    if (r.buckets.length === 0) {
      bodyEl.innerHTML = '<div class="empty-hint">该时间段内暂无数据</div>';
      return;
    }
    if (r.total === 0) {
      bodyEl.innerHTML = '<div class="empty-hint">该时间段内计数为 0（尚无数据）</div>';
      return;
    }
    if (mode === 'text') {
      bodyEl.innerHTML = `<table class="data detail-table"><thead><tr><th>时间</th><th>次数</th></tr></thead><tbody>
        ${r.buckets.map((b) => `<tr><td>${escapeHtml(b.t)}</td><td>${num(b.n)}</td></tr>`).join('')}
        <tr class="total-row"><td>合计</td><td>${num(r.total)}</td></tr></tbody></table>`;
      return;
    }
    bodyEl.innerHTML = '<div class="detail-chart"></div>';
    drawLineChart(bodyEl.querySelector('.detail-chart'), r.buckets);
  }

  function renderRank(bodyEl, r) {
    if (!r.rows.length) {
      bodyEl.innerHTML = '<div class="empty-hint">该时间段内暂无指令记录</div>';
      return;
    }
    bodyEl.innerHTML = `<table class="data detail-table"><thead><tr><th style="width:40px">#</th><th>${r.key === 'cmd_plugin' ? '插件（分类）' : '指令名'}</th><th>触发次数</th><th>占比</th>${r.key === 'cmd_plugin' ? '<th>最常触发指令</th>' : ''}</tr></thead><tbody>
      ${r.rows.map((row, i) => `<tr>
        <td>${i + 1}</td>
        <td class="cell">${escapeHtml(row.name)}</td>
        <td>${num(row.n)}</td>
        <td>${r.total ? ((100 * row.n) / r.total).toFixed(1) : 0}%</td>
        ${r.key === 'cmd_plugin' ? `<td class="cell">${row.top.map((x) => escapeHtml(x.cmd) + ' ×' + num(x.n)).join('、') || '—'}</td>` : ''}
      </tr>`).join('')}
    </tbody></table>`;
  }

  // ==== 手绘 SVG 折线图（单序列，主题色）====
  const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

  function niceMax(v) {
    if (v <= 0) return 1;
    const exp = Math.floor(Math.log10(v));
    const f = v / Math.pow(10, exp);
    const nf = f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10;
    return nf * Math.pow(10, exp);
  }

  function fmtAxisNum(v) {
    if (v >= 1e8) return (v / 1e8).toFixed(v % 1e8 === 0 ? 0 : 1) + '亿';
    if (v >= 1e4) return (v / 1e4).toFixed(v % 1e4 === 0 ? 0 : 1) + '万';
    return v.toLocaleString('zh-CN');
  }

  function drawLineChart(container, buckets) {
    const W = 760, H = 320, padL = 56, padR = 16, padT = 12, padB = 34;
    const innerW = W - padL - padR, innerH = H - padT - padB;
    const accent = cssVar('--accent') || '#4f8cff';
    const muted = cssVar('--muted') || '#93a5c4';
    const border = cssVar('--border') || '#2a3a5c';
    const text = cssVar('--text') || '#e8eefb';
    const n = buckets.length;
    const yMax = niceMax(Math.max(...buckets.map((b) => b.n), 0));
    const x = (i) => padL + (n <= 1 ? innerW / 2 : (i * innerW) / (n - 1));
    const y = (v) => padT + innerH - (v / yMax) * innerH;

    // 网格线（5 条）+ y 轴刻度
    let grid = '';
    for (let g = 0; g <= 4; g++) {
      const val = (yMax * g) / 4;
      const gy = y(val);
      grid += `<line x1="${padL}" y1="${gy}" x2="${W - padR}" y2="${gy}" stroke="${border}" stroke-width="1"/>
        <text x="${padL - 8}" y="${gy + 4}" text-anchor="end" font-size="11" fill="${muted}">${fmtAxisNum(Math.round(val * 100) / 100)}</text>`;
    }
    // x 轴标签（≤6 个均匀取样）
    const labelIdx = n <= 6 ? [...Array(n).keys()] : [0, 1, 2, 3, 4, 5].map((k) => Math.round((k * (n - 1)) / 5));
    let xLabels = labelIdx.map((i) => {
      const anchor = i === 0 ? 'start' : i === n - 1 ? 'end' : 'middle';
      return `<text x="${x(i)}" y="${H - 10}" text-anchor="${anchor}" font-size="11" fill="${muted}">${escapeHtml(buckets[i].t)}</text>`;
    }).join('');

    const pts = buckets.map((b, i) => `${x(i)},${y(b.n)}`).join(' ');
    const area = `M ${x(0)},${y(0)} L ${pts.replace(/ /g, ' L ')} L ${x(n - 1)},${y(0)} Z`;
    const dots = buckets.map((b, i) => `<circle cx="${x(i)}" cy="${y(b.n)}" r="4" fill="${accent}" class="pt-dot" data-i="${i}"/>`).join('');

    container.innerHTML = `<svg viewBox="0 0 ${W} ${H}" class="line-chart" role="img">
      ${grid}${xLabels}
      <path d="${area}" fill="${accent}" fill-opacity=".12"/>
      <polyline points="${pts}" fill="none" stroke="${accent}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
      ${dots}
      <line id="ch-cross" x1="0" y1="${padT}" x2="0" y2="${H - padB}" stroke="${muted}" stroke-width="1" stroke-dasharray="3 3" visibility="hidden"/>
      <circle id="ch-hover" r="5.5" fill="none" stroke="${accent}" stroke-width="2" visibility="hidden"/>
      <text id="ch-tip" font-size="12" fill="${text}" visibility="hidden"></text>
      <rect id="ch-hit" x="${padL}" y="${padT}" width="${innerW}" height="${innerH}" fill="transparent"/>
    </svg>`;

    const svg = container.querySelector('svg');
    const cross = container.querySelector('#ch-cross');
    const hover = container.querySelector('#ch-hover');
    const tip = container.querySelector('#ch-tip');
    const hit = container.querySelector('#ch-hit');
    const svgPoint = (ev) => {
      const rect = svg.getBoundingClientRect();
      return { px: ((ev.clientX - rect.left) / rect.width) * W, py: ((ev.clientY - rect.top) / rect.height) * H };
    };
    hit.addEventListener('mousemove', (ev) => {
      const { px } = svgPoint(ev);
      const i = n <= 1 ? 0 : Math.max(0, Math.min(n - 1, Math.round(((px - padL) / innerW) * (n - 1))));
      const cx = x(i), cy = y(buckets[i].n);
      cross.setAttribute('x1', cx); cross.setAttribute('x2', cx);
      cross.setAttribute('visibility', 'visible');
      hover.setAttribute('cx', cx); hover.setAttribute('cy', cy);
      hover.setAttribute('visibility', 'visible');
      const tipW = 150;
      let tx = cx + 10;
      if (tx + tipW > W - padR) tx = cx - tipW - 10;
      const ty = Math.max(padT, cy - 24);
      tip.setAttribute('x', tx); tip.setAttribute('y', ty);
      tip.setAttribute('visibility', 'visible');
      const lines = [`${buckets[i].t}`, `次数：${num(buckets[i].n)}`];
      tip.innerHTML = lines.map((l, k) => `<tspan x="${tx}" dy="${k === 0 ? 0 : 14}">${escapeHtml(l)}</tspan>`).join('');
    });
    hit.addEventListener('mouseleave', () => {
      cross.setAttribute('visibility', 'hidden');
      hover.setAttribute('visibility', 'hidden');
      tip.setAttribute('visibility', 'hidden');
    });
  }

  // ==== 刷新调度 ====
  let timer = 0;
  async function loadStats() {
    const data = await api('/api/stats').catch(() => null);
    renderSections(data);
    if (timeEl) timeEl.textContent = data && data.available
      ? '最后更新 ' + new Date().toLocaleTimeString('zh-CN', { hour12: false })
      : '暂无统计数据';
  }
  function schedule() {
    clearTimeout(timer);
    if (!document.hidden) timer = setTimeout(loadStats, 10000);
  }
  document.getElementById('btn-refresh').addEventListener('click', () => {
    clearTimeout(timer);
    loadStats().then(schedule);
  });
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) { clearTimeout(timer); loadStats().then(schedule); }
  });

  loadStats().then(schedule);
})();
