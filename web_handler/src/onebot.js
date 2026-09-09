// OneBot WS 客户端：调用 get_login_info 获取机器人真实账号（原生 WebSocket，零依赖）
// 单次尝试、不重试、不缓存（登录核对要求实时性）；总耗时不超过 timeoutMs
'use strict';

function getLoginInfo(uri, timeoutMs = 3000) {
  return new Promise((resolve) => {
    let ws = null;
    let settled = false;
    const finish = (r) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      try { ws && ws.close(); } catch { /* 忽略关闭异常 */ }
      resolve(r);
    };
    const timer = setTimeout(() => finish({ online: false, error: 'timeout' }), timeoutMs);

    try {
      ws = new WebSocket(uri);
    } catch (e) {
      finish({ online: false, error: 'invalid_uri' });
      return;
    }

    ws.onopen = () => {
      try {
        ws.send(JSON.stringify({ action: 'get_login_info', params: {}, echo: 'xsw_panel_' + Date.now() }));
      } catch {
        finish({ online: false, error: 'send_failed' });
      }
    };
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(typeof ev.data === 'string' ? ev.data : String(ev.data));
        if (msg && msg.status === 'ok' && msg.data && typeof msg.data.user_id !== 'undefined') {
          finish({ online: true, userId: msg.data.user_id, nickname: msg.data.nickname || '' });
        }
      } catch { /* 非 JSON 消息，忽略 */ }
    };
    ws.onerror = () => finish({ online: false, error: 'ws_error' });
    ws.onclose = () => finish({ online: false, error: 'closed' });
  });
}

module.exports = { getLoginInfo };
