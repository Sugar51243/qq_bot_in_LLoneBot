// 主页逻辑
'use strict';

(async function () {
  loadTopbar('index.html');
  const s = await api('/api/session').catch(() => null);
  if (s) document.getElementById('login-user').textContent = s.username;
  const st = await api('/api/onebot/status').catch(() => null);
  const el = document.getElementById('login-onebot');
  if (st) {
    el.textContent = st.online
      ? `在线${st.userId ? '（QQ ' + st.userId + '，双重核对生效）' : '（双重核对生效）'}`
      : '离线（登录仅静态比对）';
  }
})();
