// 登录页逻辑
'use strict';

(function () {
  const form = document.getElementById('login-form');
  const errBox = document.getElementById('login-error');
  const btn = document.getElementById('btn-login');
  const hint = document.getElementById('onebot-hint');

  function showError(msg, isWarn) {
    errBox.hidden = false;
    errBox.textContent = msg;
    errBox.className = 'error-box' + (isWarn ? ' warn' : '');
  }

  // OneBot 在线状态提示（未登录时接口只返回在线布尔值，不暴露机器人QQ）
  api('/api/onebot/status')
    .then((st) => {
      if (st.online) {
        hint.innerHTML = '<span class="ok">●</span> OneBot 已在线：登录将进行<b>双重机器人账号核对</b>（静态比对 + 实时核对）';
      } else {
        hint.innerHTML = '<span class="off">●</span> OneBot 离线：登录仅做<b>静态机器人账号比对</b>（web_handler/config.yaml 的 botQq）';
      }
    })
    .catch(() => {
      hint.innerHTML = '<span class="off">●</span> 无法连接 OneBot，登录仅做静态机器人账号比对';
    });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    errBox.hidden = true;
    btn.disabled = true;
    btn.textContent = '登录中…';
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
        toast('登录成功，正在进入…', 'success');
        if (!r.onebotOnline) toast('OneBot 离线，本次仅做了静态机器人账号比对', 'info', 4200);
        location.href = '/index.html';
      }
    } catch (err) {
      // 401 = 账号密码错（红）；403 = 机器人账号问题（橙）
      showError(err.message, err.status === 403);
      btn.disabled = false;
      btn.textContent = '登 录';
    }
  });
})();
