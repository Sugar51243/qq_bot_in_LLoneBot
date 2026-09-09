// 主页逻辑（登录信息与 OneBot 状态缓存后重渲染，支持语言切换）
'use strict';

(async function () {
  loadTopbar('index.html');
  let session = null;
  let onebot = null;

  function renderInfo() {
    const userEl = document.getElementById('login-user');
    if (userEl) userEl.textContent = session ? session.username : '…';
    const el = document.getElementById('login-onebot');
    if (!el) return;
    if (!onebot) {
      el.textContent = t('index.detecting');
      return;
    }
    if (onebot.online) {
      el.textContent = onebot.userId ? t('index.onlineQQ', { qq: onebot.userId }) : t('index.onlineNoQQ');
    } else {
      el.textContent = t('index.offlineStatic');
    }
  }

  session = await api('/api/session').catch(() => null);
  onebot = await api('/api/onebot/status').catch(() => null);
  renderInfo();

  // —— 数据统计（每 10 秒刷新）——
  const statsEl = document.getElementById('home-stats');
  const timeEl = document.getElementById('stat-time');
  async function loadStats() {
    const data = await api('/api/stats').catch(() => null);
    renderStats(statsEl, data);
    if (timeEl) timeEl.textContent = data && data.available
      ? t('index.lastUpdate', { t: new Date().toLocaleTimeString(locale(), { hour12: false }) })
      : '';
  }
  loadStats();
  setInterval(loadStats, 10000);

  // 语言切换时重渲染
  window.__i18nRerender.push(() => { renderInfo(); loadStats(); });
})();
