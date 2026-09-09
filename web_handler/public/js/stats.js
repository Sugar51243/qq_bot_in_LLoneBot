// 数据统计页逻辑：分类分区卡片 + 详情弹窗（年/月/日/小时 · 折线图/文本）
// 文案全部走 i18n 键（titleKey/descKey/labelKey），切换语言后由 __i18nRerender 重渲染
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
      titleKey: 'stats.secMsg', descKey: 'stats.secMsgDesc',
      tiles: [
        { labelKey: 'stats.msg_receive_n', kind: 'num', get: (d) => c(d).msg_receive, detail: { key: 'msg_receive' } },
        { labelKey: 'stats.msg_send_n', kind: 'num', get: (d) => c(d).msg_send, detail: { key: 'msg_send' } },
        { labelKey: 'stats.msg_total_n', kind: 'num', get: (d) => (c(d).msg_receive || 0) + (c(d).msg_send || 0), detail: { key: 'msg_total' } },
        { labelKey: 'stats.msg_receive_f', kind: 'freq', get: (d) => d.freq.msg_receive, detail: { key: 'msg_receive' } },
        { labelKey: 'stats.msg_send_f', kind: 'freq', get: (d) => d.freq.msg_send, detail: { key: 'msg_send' } },
        { labelKey: 'stats.msg_total_f', kind: 'freq', get: (d) => d.freq.msg_total, detail: { key: 'msg_total' } },
        { labelKey: 'stats.api_up_n', kind: 'num', get: (d) => c(d).api_up, detail: { key: 'api_up' } },
        { labelKey: 'stats.api_down_n', kind: 'num', get: (d) => c(d).api_down, detail: { key: 'api_down' } },
        { labelKey: 'stats.api_total_n', kind: 'num', get: (d) => (c(d).api_up || 0) + (c(d).api_down || 0), detail: { key: 'api_total' } },
      ],
    },
    {
      titleKey: 'stats.secCmd', descKey: 'stats.secCmdDesc',
      tiles: [
        { labelKey: 'stats.cmd_trigger_n', kind: 'num', get: (d) => c(d).cmd_trigger, detail: { key: 'cmd_trigger' } },
        { labelKey: 'stats.cmd_trigger_f', kind: 'freq', get: (d) => d.freq.cmd_trigger, detail: { key: 'cmd_trigger' } },
        { labelKey: 'stats.cmd_all_top', kind: 'top', get: (d) => d.top.cmd_all, detail: { key: 'cmd_all', defaultUnit: 'month' } },
        { labelKey: 'stats.cmd_plugin_top', kind: 'top', get: (d) => d.top.cmd_plugin, detail: { key: 'cmd_plugin', defaultUnit: 'month' } },
      ],
    },
    {
      titleKey: 'stats.secScene', descKey: 'stats.secSceneDesc',
      tiles: [
        { labelKey: 'stats.scene_total', kind: 'num', get: (d) => (d.scenes ? d.scenes.total : null), detail: { key: 'scene_new' } },
        { labelKey: 'stats.scene_group', kind: 'num', get: (d) => (d.scenes ? d.scenes.group : null), detail: { key: 'scene_new', kind: 'group' } },
        { labelKey: 'stats.scene_private', kind: 'num', get: (d) => (d.scenes ? d.scenes.private : null), detail: { key: 'scene_new', kind: 'private' } },
        { labelKey: 'stats.scene_enabled_total', kind: 'num', get: (d) => (d.scenesEnabled ? d.scenesEnabled.total : null) },
        { labelKey: 'stats.scene_enabled_group', kind: 'num', get: (d) => (d.scenesEnabled ? d.scenesEnabled.group : null) },
        { labelKey: 'stats.scene_enabled_private', kind: 'num', get: (d) => (d.scenesEnabled ? d.scenesEnabled.private : null) },
      ],
    },
  ];

  const UNITS = [['year', 'stats.unitYear'], ['month', 'stats.unitMonth'], ['day', 'stats.unitDay'], ['hour', 'stats.unitHour']];
  const UNIT_WINDOW = { hour: 'stats.windowHour', day: 'stats.windowDay', month: 'stats.windowMonth', year: 'stats.windowYear' };

  // ==== 分区渲染 ====
  const num = (v) => (v == null ? '—' : Number(v).toLocaleString(locale()));

  function renderSections(data) {
    if (!data || !data.available) {
      sectionsEl.innerHTML = `<div class="empty-hint">${escapeHtml(t('common.statsUnavailable'))}</div>`;
      return;
    }
    sectionsEl.innerHTML = SECTIONS.map((sec) => `
      <section class="stats-section">
        <div class="stats-section-head">
          <h3>${escapeHtml(t(sec.titleKey))}</h3>
          <span class="fmeta">${escapeHtml(t(sec.descKey))}</span>
        </div>
        <div class="stat-grid">
          ${sec.tiles.map((tile) => renderTile(tile, data)).join('')}
        </div>
      </section>`).join('');
    sectionsEl.querySelectorAll('.stat-tile[data-detail]').forEach((el) => {
      el.addEventListener('click', () => {
        const tinfo = JSON.parse(el.getAttribute('data-detail'));
        openDetail(tinfo.title, tinfo.detail);
      });
    });
  }

  function renderTile(tile, data) {
    const val = tile.get(data);
    let body;
    if (tile.kind === 'top') {
      const rows = val || [];
      body = rows.length
        ? `<div class="stat-top">${rows.map((r, i) => `<div class="stat-top-row"><span class="rank-i">${i + 1}.</span><span class="rank-name">${escapeHtml(r.name)}</span><span class="rank-n">×${num(r.n)}</span></div>`).join('')}</div>`
        : '<div class="stat-num">—</div>';
    } else if (tile.kind === 'freq') {
      body = `<div class="stat-num">${num(val)}</div><div class="stat-unit">${escapeHtml(t('stats.perDay'))}</div>`;
    } else {
      body = `<div class="stat-num">${num(val)}</div>`;
    }
    const clickable = tile.detail ? ` data-detail="${escapeHtml(JSON.stringify({ title: t(tile.labelKey), detail: tile.detail }))}"` : '';
    return `<div class="stat-tile${tile.detail ? ' clickable' : ''}"${clickable}>
      ${body}
      <div class="stat-label">${escapeHtml(t(tile.labelKey))}</div>
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
          <button class="btn small" data-act="close">${escapeHtml(t('common.close'))}</button>
        </div>
        <div class="detail-controls">
          <span class="seg-group" id="d-units">
            ${UNITS.map(([u, key]) => `<button class="btn small seg-btn" data-unit="${u}">${escapeHtml(t(key))}</button>`).join('')}
          </span>
          ${isScene ? `<span class="seg-group" id="d-kinds">
            <button class="btn small seg-btn" data-kind="">${escapeHtml(t('stats.all'))}</button>
            <button class="btn small seg-btn" data-kind="group">${escapeHtml(t('stats.group'))}</button>
            <button class="btn small seg-btn" data-kind="private">${escapeHtml(t('stats.private'))}</button>
          </span>` : ''}
          ${isRank ? '' : `<span class="seg-group" id="d-modes">
            <button class="btn small seg-btn" data-mode="chart">${escapeHtml(t('stats.chart'))}</button>
            <button class="btn small seg-btn" data-mode="text">${escapeHtml(t('stats.text'))}</button>
          </span>`}
        </div>
        <div class="detail-body" id="d-body"><div class="empty-hint">${escapeHtml(t('common.loading'))}</div></div>
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
      winEl.textContent = t('stats.range', { w: t(UNIT_WINDOW[unit]) });
      bodyEl.innerHTML = `<div class="empty-hint">${escapeHtml(t('common.loading'))}</div>`;
      let url = `/api/stats/detail?key=${encodeURIComponent(opts.key)}&unit=${encodeURIComponent(unit)}`;
      if (isScene && kind) url += '&kind=' + encodeURIComponent(kind);
      try {
        const r = await api(url);
        if (r.kindType === 'rank') renderRank(bodyEl, r);
        else renderCount(bodyEl, mode, r);
      } catch (err) {
        bodyEl.innerHTML = `<div class="empty-hint">${escapeHtml(t('stats.loadFail', { e: err.message }))}</div>`;
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
      bodyEl.innerHTML = `<div class="empty-hint">${escapeHtml(t('stats.noData'))}</div>`;
      return;
    }
    if (r.total === 0) {
      bodyEl.innerHTML = `<div class="empty-hint">${escapeHtml(t('stats.zeroCount'))}</div>`;
      return;
    }
    if (mode === 'text') {
      bodyEl.innerHTML = `<table class="data detail-table"><thead><tr><th>${escapeHtml(t('stats.thTime'))}</th><th>${escapeHtml(t('stats.thCount'))}</th></tr></thead><tbody>
        ${r.buckets.map((b) => `<tr><td>${escapeHtml(b.t)}</td><td>${num(b.n)}</td></tr>`).join('')}
        <tr class="total-row"><td>${escapeHtml(t('stats.total'))}</td><td>${num(r.total)}</td></tr></tbody></table>`;
      return;
    }
    bodyEl.innerHTML = '<div class="detail-chart"></div>';
    drawLineChart(bodyEl.querySelector('.detail-chart'), r.buckets);
  }

  function renderRank(bodyEl, r) {
    if (!r.rows.length) {
      bodyEl.innerHTML = `<div class="empty-hint">${escapeHtml(t('stats.noCmd'))}</div>`;
      return;
    }
    bodyEl.innerHTML = `<table class="data detail-table"><thead><tr><th style="width:40px">#</th><th>${r.key === 'cmd_plugin' ? escapeHtml(t('stats.thPlugin')) : escapeHtml(t('stats.thCmd'))}</th><th>${escapeHtml(t('stats.thTriggers'))}</th><th>${escapeHtml(t('stats.thShare'))}</th>${r.key === 'cmd_plugin' ? `<th>${escapeHtml(t('stats.thTopCmd'))}</th>` : ''}</tr></thead><tbody>
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

  // 轴刻度数字：中文用 亿/万 缩略，其他语言用小缩写（1.2M / 850K）
  function fmtAxisNum(v) {
    if (locale().startsWith('zh')) {
      const yi = locale() === 'zh-TW' ? '億' : '亿';
      const wan = locale() === 'zh-TW' ? '萬' : '万';
      if (v >= 1e8) return (v / 1e8).toFixed(v % 1e8 === 0 ? 0 : 1) + yi;
      if (v >= 1e4) return (v / 1e4).toFixed(v % 1e4 === 0 ? 0 : 1) + wan;
    }
    if (v >= 1e6) return new Intl.NumberFormat(locale(), { notation: 'compact', maximumFractionDigits: 1 }).format(v);
    return v.toLocaleString(locale());
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
      const lines = [`${buckets[i].t}`, t('stats.chartTip', { n: num(buckets[i].n) })];
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
      ? t('index.lastUpdate', { t: new Date().toLocaleTimeString(locale(), { hour12: false }) })
      : t('stats.none');
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

  // 语言切换时重渲染分区卡片
  window.__i18nRerender.push(() => loadStats());

  loadStats().then(schedule);
})();
