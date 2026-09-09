// 数据统计页逻辑：7 项计数卡片 + 10 秒自动刷新（页面隐藏时暂停）
'use strict';

(function () {
  const gridEl = document.getElementById('stats-grid');
  const timeEl = document.getElementById('stat-time');

  loadTopbar('stats.html');

  let timer = 0;

  async function loadStats() {
    const data = await api('/api/stats').catch(() => null);
    renderStats(gridEl, data);
    if (timeEl) timeEl.textContent = data && data.available
      ? '最后更新 ' + new Date().toLocaleTimeString('zh-CN', { hour12: false })
      : '暂无统计数据';
  }

  function schedule() {
    clearTimeout(timer);
    // 页面隐藏时暂停刷新，回到前台立即刷新一次
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
