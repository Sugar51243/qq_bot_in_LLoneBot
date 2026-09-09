

# == 数据统计 ==

# 机器人侧计数采集，写入 data/db/stats.db（面板只读展示）。
# 口径：
#   信息接收 = 收到的 QQ 消息事件(post_type=message)；信息发送 = 调用发送消息 API 次数
#   接口上行 = 从 OneBot 收到的全部事件(消息/通知/请求/元事件，心跳在连接器层已过滤)
#   接口下行 = 调用 OneBot API 的总次数(含查资料/踢人等，含统计自身 get_group_list 轮询)
#   指令触发 = 被核心/插件成功处理的消息事件
#   频率(条/day) = 历史日均 = 总量 ÷ 统计天数(自首次记录，不足1天按1天，面板计算)
#   指令排行：cmd_all = 不分插件统一按指令名；cmd_plugin = 按 plugin_id(核心归"核心内置")
#   场景 = scene_id(group_<gid>/私聊<uid>)：群聊来自 get_group_list 轮询 + 消息事件，
#         私聊来自私聊消息事件(自统计上线累计)
# 存储：counters=总次数、buckets=小时桶预聚合(时序/频率)、cmd_events=指令明细、scenes=场景

import time

from OneBotConnecter.loger.log_info import error
from src.db_handler.plugin_db import PluginDB, start_background_once

# 发送消息类 API：命中时在"接口下行"之外再计一次"信息发送"
MSG_SEND_ACTIONS = {"send_private_msg", "send_group_msg",
                    "send_private_forward_msg", "send_group_forward_msg"}

# 保留策略与轮询周期（模块常量）
RETAIN_DAYS = 730          # 时序/指令明细保留约 2 年
GROUP_POLL_SEC = 300       # 群列表轮询间隔
CLEANUP_SEC = 6 * 3600     # 清理间隔

_db = PluginDB("stats", {
    "counters": "CREATE TABLE IF NOT EXISTS counters(key TEXT PRIMARY KEY, value INTEGER NOT NULL DEFAULT 0)",
    "buckets": ("CREATE TABLE IF NOT EXISTS buckets("
                "key TEXT NOT NULL, bucket_ts INTEGER NOT NULL, n INTEGER NOT NULL DEFAULT 0, "
                "PRIMARY KEY(key, bucket_ts))"),
    "cmd_events": ("CREATE TABLE IF NOT EXISTS cmd_events("
                   "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                   "key TEXT NOT NULL, name TEXT NOT NULL DEFAULT '', cmd TEXT NOT NULL DEFAULT '', "
                   "ts INTEGER NOT NULL)"),
    "cmd_idx_key_ts": "CREATE INDEX IF NOT EXISTS idx_cmd_events_key_ts ON cmd_events(key, ts)",
    "cmd_idx_key_name": "CREATE INDEX IF NOT EXISTS idx_cmd_events_key_name ON cmd_events(key, name)",
    "cmd_idx_ts": "CREATE INDEX IF NOT EXISTS idx_cmd_events_ts ON cmd_events(ts)",
    "scenes": ("CREATE TABLE IF NOT EXISTS scenes("
               "scene_id TEXT PRIMARY KEY, kind TEXT NOT NULL, "
               "first_ts INTEGER NOT NULL, last_ts INTEGER NOT NULL)"),
}, db_name="stats")  # -> data/db/stats.db，面板数据库管理自动可见


def _write_retry(sta: str, params: tuple) -> bool:
    """写入失败重试 3 次（防 SQLITE_BUSY 丢数据）"""
    for _ in range(3):
        if _db.execute(sta, params):
            return True
        time.sleep(0.05)
    error(f"[stats] 写入失败: {sta.split(' ')[0]} {params}")
    return False


def incr(key: str, n: int = 1) -> bool:
    """总次数 +n（UPSERT 原子自增）"""
    sta = ("INSERT INTO counters(key, value) VALUES(?, ?) "
           "ON CONFLICT(key) DO UPDATE SET value = value + excluded.value")
    return _write_retry(sta, (key, n))


def _bucket_incr(key: str) -> None:
    """当前小时桶 +1（UTC 对齐整点，UTC+8 本地标签恰为 :00）"""
    bucket_ts = int(time.time()) // 3600 * 3600
    sta = ("INSERT INTO buckets(key, bucket_ts, n) VALUES(?, ?, 1) "
           "ON CONFLICT(key, bucket_ts) DO UPDATE SET n = n + 1")
    _write_retry(sta, (key, bucket_ts))


def _scene_seen(scene_id: str, kind: str) -> None:
    """记录场景（UPSERT 更新最近活跃时间）"""
    if not scene_id:
        return
    now = int(time.time())
    sta = ("INSERT INTO scenes(scene_id, kind, first_ts, last_ts) VALUES(?, ?, ?, ?) "
           "ON CONFLICT(scene_id) DO UPDATE SET kind = excluded.kind, last_ts = excluded.last_ts")
    _write_retry(sta, (str(scene_id), kind, now, now))


def _cmd_event(key: str, name: str, cmd: str = "") -> None:
    """指令明细（排行用）；name 为空跳过，超长截断"""
    name = str(name or "").strip()[:64]
    cmd = str(cmd or "").strip()[:64]
    if not name:
        return
    sta = "INSERT INTO cmd_events(key, name, cmd, ts) VALUES(?, ?, ?, ?)"
    _write_retry(sta, (key, name, cmd, int(time.time())))


# == 上游（OneBot → 机器人）==

def record_upstream(message) -> None:
    """每条从 OneBot 收到的非心跳事件 +1；消息事件另计信息接收与场景"""
    incr("api_up")
    _bucket_incr("api_up")
    if message.raw_data.get("post_type") == "message":
        incr("msg_receive")
        _bucket_incr("msg_receive")
        # 场景记录：群聊 -> group_<gid>，私聊 -> <uid>
        raw = message.raw_data
        if raw.get("group_id") is not None:
            _scene_seen(f"group_{raw.get('group_id')}", "group")
        else:
            _scene_seen(raw.get("user_id"), "private")


# == 下游（机器人 → OneBot）==

def record_downstream(action: str) -> None:
    """每次调用 OneBot API +1；发送消息类 API 再计一次信息发送"""
    incr("api_down")
    _bucket_incr("api_down")
    if action in MSG_SEND_ACTIONS:
        incr("msg_send")
        _bucket_incr("msg_send")


# == 指令 ==

def record_command() -> None:
    incr("cmd_trigger")
    _bucket_incr("cmd_trigger")


def record_cmd_any(command) -> None:
    """不计插件：所有插件+内置指令统一按指令名排行"""
    _cmd_event("cmd_all", command)


def record_cmd_plugin(category, command) -> None:
    """按插件分类：category = plugin_id（核心指令统一归"核心内置"）"""
    _cmd_event("cmd_plugin", category, command)


# == 群列表轮询（已添加场景）==

def _group_list_loop(handler) -> None:
    last_cleanup = 0
    while True:
        try:
            resp = handler.get_group_list()
            raw = getattr(resp, "raw_data", None)
            groups = raw.get("data") if isinstance(raw, dict) else None
            if isinstance(groups, list):
                for g in groups:
                    gid = g.get("group_id") if isinstance(g, dict) else None
                    if gid is not None:
                        _scene_seen(f"group_{gid}", "group")
        except Exception:
            pass  # 未就绪/接口失败：跳过本轮，下轮自愈
        # 保留清理（约每 6 小时一次）
        now = int(time.time())
        if now - last_cleanup >= CLEANUP_SEC:
            last_cleanup = now
            cutoff = now - RETAIN_DAYS * 86400
            _write_retry("DELETE FROM buckets WHERE bucket_ts < ?", (cutoff,))
            _write_retry("DELETE FROM cmd_events WHERE ts < ?", (cutoff,))
        time.sleep(GROUP_POLL_SEC)


def start_group_listener(handler) -> None:
    """启动已添加场景采集线程（handler 为 message_interface，与插件 listener 同源）"""
    start_background_once("stats_group_listener", lambda: _group_list_loop(handler))


# == 接口下行钩子 ==

def hook_send_to_server(bot) -> None:
    """包装 connecter 实例的 send_to_server，统计全部接口下行调用。

    必须在 OneBot 构造之后、load_plugin_listeners / bot.run() 之前调用
    （否则会漏掉 run() 启动时的 get_login_info 等调用）。
    connecter 实例 = bot.handler.handler.inface，覆盖 message_interface 与
    tsugu card.py 直连 inface 的全部调用方；重连只替换其内部 websocket 属性，
    本包装不失效。
    """
    inface = bot.handler.handler.inface
    if getattr(inface, "_stats_hooked", False):
        return
    original = inface.send_to_server  # 已绑定方法，闭包捕获

    def wrapped(action, body):  # 实例属性赋值不会自动绑定 self，签名保持 (action, body)
        record_downstream(action)
        return original(action, body)

    inface.send_to_server = wrapped
    inface._stats_hooked = True
