

# == 数据统计 ==

# 机器人侧计数采集，写入 data/db/stats.db（面板只读展示）。
# 口径：
#   信息接收 = 收到的 QQ 消息事件(post_type=message)；信息发送 = 调用发送消息 API 次数
#   接口上行 = 从 OneBot 收到的全部事件(消息/通知/请求/元事件，心跳在连接器层已过滤)
#   接口下行 = 调用 OneBot API 的总次数(含查资料/踢人等)；指令触发 = 被核心/插件成功处理的消息事件
# 两个"总次数"由面板前端相加计算，不单独存储。

import time

from OneBotConnecter.loger.log_info import error
from src.db_handler.plugin_db import PluginDB

# 发送消息类 API：命中时在"接口下行"之外再计一次"信息发送"
MSG_SEND_ACTIONS = {"send_private_msg", "send_group_msg",
                    "send_private_forward_msg", "send_group_forward_msg"}

_db = PluginDB("stats", {
    "counters": "CREATE TABLE IF NOT EXISTS counters(key TEXT PRIMARY KEY, value INTEGER NOT NULL DEFAULT 0)",
}, db_name="stats")  # -> data/db/stats.db，面板数据库管理自动可见


def incr(key: str, n: int = 1) -> bool:
    """计数 +n（UPSERT 原子自增）；失败重试 3 次防 SQLITE_BUSY 丢失计数"""
    sta = ("INSERT INTO counters(key, value) VALUES(?, ?) "
           "ON CONFLICT(key) DO UPDATE SET value = value + excluded.value")
    for _ in range(3):
        if _db.execute(sta, (key, n)):
            return True
        time.sleep(0.05)
    error(f"[stats] 计数器 {key} 写入失败")
    return False


def record_upstream(message) -> None:
    """每条从 OneBot 收到的非心跳事件 +1；消息事件再计一次信息接收"""
    incr("api_up")
    if message.raw_data.get("post_type") == "message":
        incr("msg_receive")


def record_downstream(action: str) -> None:
    """每次调用 OneBot API +1；发送消息类 API 再计一次信息发送"""
    incr("api_down")
    if action in MSG_SEND_ACTIONS:
        incr("msg_send")


def record_command() -> None:
    incr("cmd_trigger")


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
