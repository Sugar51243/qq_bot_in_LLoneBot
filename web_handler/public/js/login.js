// 登录页逻辑（文案走 i18n；OneBot 提示区由状态缓存重渲染，支持语言切换）
'use strict';

(function () {
  const form = document.getElementById('login-form');
  const errBox = document.getElementById('login-error');
  const btn = document.getElementById('btn-login');
  const hint = document.getElementById('onebot-hint');
  let onebotOnline = null; // true=在线 false=离线 null=无法连接

  function showError(msg, isWarn) {
    errBox.hidden = false;
    errBox.textContent = msg;
    errBox.className = 'error-box' + (isWarn ? ' warn' : '');
  }

  // OneBot 在线状态提示（未登录时接口只返回在线布尔值，不暴露机器人QQ）
  function renderHint() {
    if (onebotOnline === true) {
      hint.innerHTML = '<span class="ok">●</span> ' + t('login.hintOnline');
    } else if (onebotOnline === false) {
      hint.innerHTML = '<span class="off">●</span> ' + t('login.hintOffline');
    } else {
      hint.innerHTML = '<span class="off">●</span> ' + t('login.hintNoConn');
    }
  }
  window.__i18nRerender.push(renderHint);

  api('/api/onebot/status')
    .then((st) => { onebotOnline = !!st.online; renderHint(); })
    .catch(() => { onebotOnline = null; renderHint(); });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    errBox.hidden = true;
    btn.disabled = true;
    btn.textContent = t('login.loggingIn');
    const fd = new FormData(form);
    try {
      const r = await api('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: fd.get('username'),
          password: fd.get('password'),
          botQq: fd.get('botQq'),
        }),
      });
      if (r.ok) {
        toast(t('login.success'), 'success');
        if (!r.onebotOnline) toast(t('login.staticOnly'), 'info', 4200);
        location.href = '/index.html';
      }
    } catch (err) {
      // 401 = 账号密码错（红）；403 = 机器人账号问题（橙）；文案来自服务端
      showError(err.message, err.status === 403);
      btn.disabled = false;
      btn.textContent = t('login.btn');
    }
  });
})();
