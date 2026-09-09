// 小生物v2 管理面板通用工具（fetch 封装 / toast / 弹窗 / 格式化 / 顶栏）
// 依赖先加载的 i18n.js（t/locale）与 theme.js；动态文案一律用 t()，切换语言后由 __i18nRerender 回调重渲染
'use strict';

// API 请求封装：401 统一跳登录页；非 2xx 抛带本地化 message 的 Error
async function api(path, opts = {}) {
  let res;
  try {
    res = await fetch(path, opts);
  } catch (e) {
    toast(t('common.netErr'), 'error');
    throw e;
  }
  if (res.status === 401) {
    location.href = '/login.html';
    throw new Error('未登录');
  }
  let data = null;
  try { data = await res.json(); } catch { /* 非 JSON 响应 */ }
  if (!res.ok) {
    const err = new Error((data && data.error) || `请求失败 (${res.status})`);
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

async function apiJson(path, body, method = 'POST') {
  return api(path, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

// —— Toast 提示 ——
function toast(msg, type = 'info', ms = 3200) {
  let wrap = document.querySelector('.toast-wrap');
  if (!wrap) {
    wrap = document.createElement('div');
    wrap.className = 'toast-wrap';
    document.body.appendChild(wrap);
  }
  const el = document.createElement('div');
  el.className = 'toast ' + type;
  el.textContent = msg;
  wrap.appendChild(el);
  setTimeout(() => {
    el.style.transition = 'opacity .25s';
    el.style.opacity = '0';
    setTimeout(() => el.remove(), 260);
  }, ms);
}

// —— 通用弹窗 ——
function showModal(html) {
  const overlay = document.createElement('div');
  overlay.className = 'overlay';
  overlay.innerHTML = html;
  document.body.appendChild(overlay);
  const close = () => overlay.remove();
  overlay.addEventListener('mousedown', (e) => {
    if (e.target === overlay) close();
  });
  return { overlay, close };
}

// 确认弹窗 → Promise<boolean>
function confirmDlg(title, detail, okText = t('common.ok')) {
  return new Promise((resolve) => {
    const { overlay, close } = showModal(`
      <div class="modal-box">
        <h3>${escapeHtml(title)}</h3>
        <div class="mdesc">${escapeHtml(detail)}</div>
        <div class="mactions">
          <button class="btn" data-act="cancel">${escapeHtml(t('common.cancel'))}</button>
          <button class="btn danger" data-act="ok">${escapeHtml(okText)}</button>
        </div>
      </div>`);
    overlay.querySelector('[data-act="cancel"]').onclick = () => { close(); resolve(false); };
    overlay.querySelector('[data-act="ok"]').onclick = () => { close(); resolve(true); };
  });
}

// 文本输入弹窗 → Promise<string|null>
function promptDlg(title, label, initial = '') {
  return new Promise((resolve) => {
    const { overlay, close } = showModal(`
      <div class="modal-box">
        <h3>${escapeHtml(title)}</h3>
        <div class="mbody">
          <label>${escapeHtml(label)}
            <input type="text" id="pd-input" value="${escapeHtml(initial)}" autocomplete="off">
          </label>
        </div>
        <div class="mactions">
          <button class="btn" data-act="cancel">${escapeHtml(t('common.cancel'))}</button>
          <button class="btn primary" data-act="ok">${escapeHtml(t('common.ok'))}</button>
        </div>
      </div>`);
    const input = overlay.querySelector('#pd-input');
    input.focus();
    input.select();
    const ok = () => {
      const v = input.value.trim();
      if (v === '') { toast(t('common.inputRequired'), 'error'); return; }
      close();
      resolve(v);
    };
    overlay.querySelector('[data-act="ok"]').onclick = ok;
    overlay.querySelector('[data-act="cancel"]').onclick = () => { close(); resolve(null); };
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') ok();
      if (e.key === 'Escape') { close(); resolve(null); }
    });
  });
}

// —— 格式化工具 ——
function escapeHtml(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

// 关键词高亮：返回转义后的 HTML，命中片段包裹 <mark class="hl">（ci=忽略大小写）
function highlightText(text, kw, ci = true) {
  if (!kw) return escapeHtml(text);
  const esc = escapeHtml(String(text));
  const hay = ci ? esc.toLowerCase() : esc;
  const needle = ci ? String(kw).toLowerCase() : String(kw);
  let out = '';
  let i = 0;
  while (i < esc.length) {
    const idx = hay.indexOf(needle, i);
    if (idx === -1) { out += esc.slice(i); break; }
    out += esc.slice(i, idx) + '<mark class="hl">' + esc.slice(idx, idx + needle.length) + '</mark>';
    i = idx + needle.length;
  }
  return out;
}

function fmtSize(bytes) {
  if (bytes == null) return '';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  if (bytes < 1024 * 1024 * 1024) return (bytes / 1024 / 1024).toFixed(1) + ' MB';
  return (bytes / 1024 / 1024 / 1024).toFixed(2) + ' GB';
}

function fmtTime(ms) {
  if (!ms) return '';
  const d = new Date(ms);
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

// —— 数据统计（主页精简版：仅总次数卡片）——
const HOME_STAT_DEFS = [
  { label: 'stats.msg_receive_n', desc: 'stats.dMsgReceive', get: (d) => d.counters.msg_receive },
  { label: 'stats.msg_send_n', desc: 'stats.dMsgSend', get: (d) => d.counters.msg_send },
  { label: 'stats.api_up_n', desc: 'stats.dApiUp', get: (d) => d.counters.api_up },
  { label: 'stats.api_down_n', desc: 'stats.dApiDown', get: (d) => d.counters.api_down },
  { label: 'stats.cmd_trigger_n', desc: 'stats.dCmdTrigger', get: (d) => d.counters.cmd_trigger },
  { label: 'stats.scene_total', desc: 'stats.dScene', get: (d) => (d.scenes ? d.scenes.total : null) },
  { label: 'stats.scene_enabled_total', desc: 'stats.dSceneEnabled', get: (d) => (d.scenesEnabled ? d.scenesEnabled.total : null) },
];

// 首页渲染：/api/stats 数据 → 7 张总次数卡片（缺失显示 —）
function renderStats(containerEl, data) {
  if (!containerEl) return;
  if (!data || !data.available) {
    containerEl.innerHTML = `<div class="empty-hint">${escapeHtml(t('common.statsUnavailable'))}</div>`;
    return;
  }
  const num = (v) => (v == null ? '—' : Number(v).toLocaleString(locale()));
  containerEl.innerHTML = HOME_STAT_DEFS.map((d) => `
    <div class="stat-tile" title="${escapeHtml(t(d.desc))}">
      <div class="stat-num">${num(d.get(data))}</div>
      <div class="stat-label">${escapeHtml(t(d.label))}</div>
    </div>`).join('');
}

// —— 顶栏（主页/项目架构/数据库管理共用）——
const topStatus = { username: null, onebot: null };

// 从缓存状态重绘用户与 OneBot 徽标（语言切换时也走这里）
function renderTopbarStatus() {
  document.querySelectorAll('.top-user').forEach((el) => {
    el.textContent = topStatus.username ? '👤 ' + topStatus.username : '';
  });
  const st = topStatus.onebot;
  document.querySelectorAll('.onebot-badge').forEach((badge) => {
    if (!st) {
      badge.className = 'badge onebot-badge';
      badge.textContent = t('onebot.checking');
      return;
    }
    if (st.online) {
      badge.className = 'badge onebot-badge on';
      badge.textContent = t('onebot.online', { id: st.userId != null ? st.userId : '', nick: st.nickname ? ' · ' + st.nickname : '' });
      badge.title = t('onebot.uriTitle') + st.uri;
    } else {
      badge.className = 'badge onebot-badge off';
      badge.textContent = t('onebot.offline');
      badge.title = t('onebot.uriTitle') + st.uri + '\n' + t('onebot.offlineTitle');
    }
  });
}

// 汉堡菜单（移动端）与退出登录绑定
function initTopbarUi() {
  const burger = document.getElementById('nav-burger');
  const topbar = document.querySelector('.topbar');
  if (burger && topbar) {
    burger.addEventListener('click', () => topbar.classList.toggle('open'));
    topbar.querySelectorAll('.mob-panel a').forEach((a) => {
      a.addEventListener('click', () => topbar.classList.remove('open'));
    });
  }
  const btn = document.getElementById('btn-logout');
  if (btn) {
    btn.addEventListener('click', async () => {
      try { await api('/api/logout', { method: 'POST' }); } catch { /* 忽略 */ }
      location.href = '/login.html';
    });
  }
}

async function loadTopbar(active) {
  initTopbarUi();
  document.querySelectorAll('.topbar nav a').forEach((a) => {
    if (a.getAttribute('href') === '/' + active) a.classList.add('active');
  });
  // 当前用户
  try {
    const s = await api('/api/session');
    topStatus.username = s.username;
    renderTopbarStatus();
  } catch { /* 401 已跳登录 */ }
  // OneBot 状态徽标
  try {
    const st = await api('/api/onebot/status');
    topStatus.onebot = st;
    renderTopbarStatus();
  } catch { /* 忽略 */ }
}
window.__i18nRerender.push(renderTopbarStatus);
