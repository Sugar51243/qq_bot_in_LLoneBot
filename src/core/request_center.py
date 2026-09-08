
# == 请求处理核心 ==

# 由v1(功能注册器)的入群/好友请求处理迁移至v2核心内置常驻功能
# 白名单数据储存于核心数据库permissions.db的allow_add分表

import traceback
from OneBotConnecter.types import MessageChain
from OneBotConnecter.loger.log_info import log
from src.core.register import permission_db
from src.db_handler.database_handler import call_database, get_from_database

table_name = "allow_add"

# == 白名单 ==

def create_allow_add_table():
    sta = f"CREATE TABLE IF NOT EXISTS {table_name} (user_id TEXT PRIMARY KEY);"
    call_database(path=permission_db, sta=sta)

def allow_add_list() -> list:
    create_allow_add_table()
    return [row[0] for row in get_from_database(path=permission_db, sta=f"SELECT user_id FROM {table_name};")]

def add_allow(user_id: str) -> bool:
    create_allow_add_table()
    rows = get_from_database(path=permission_db, sta=f'SELECT user_id FROM {table_name} WHERE user_id = "{user_id}";')
    if rows: return False
    call_database(path=permission_db, sta=f'INSERT OR IGNORE INTO {table_name} (user_id) VALUES ("{user_id}");')
    return True

def _owner(bot) -> list:
    return [str(owner_id) for owner_id in bot.bot.owner]

# == 请求事件处理 ==

def handle_request(bot, message) -> bool:
    try:
        if message.raw_data.get("request_type") == "group":
            handle_group_request(bot, message)
            return True
        elif message.raw_data.get("request_type") == "friend":
            handle_friend_request(bot, message)
            return True
    except Exception as e:
        tb = e.__traceback__
        formatted_tb = ''.join(traceback.format_tb(tb))
        log(f"[Core请求处理] [{type(e)}] {e}\n{formatted_tb}")
    return False

def handle_group_request(bot, message):
    owners = _owner(bot)
    sender = message.raw_data.get("user_id")
    group_id = message.raw_data.get("group_id")
    comment = message.raw_data.get("comment", "")
    source_group_id = message.raw_data.get("source_group_id", "")
    flag = message.raw_data.get("flag", "")
    sub_type = message.raw_data.get("sub_type", "")
    #自动通过好友内的群邀请
    try:
        friendsList = bot.get_friend_list()
        for friend in friendsList.data:
            if str(friend.get("user_id")) == str(sender):
                bot.set_group_add_request(flag=flag, sub_type=sub_type, approve=True)
                log(f"[Core请求处理] 自动通过了来自[{sender}]的加群[{group_id}]请求")
                if owners:
                    bot.send_private_msg(int(owners[0]),
                        MessageChain([f"自动通过了来自[{sender}]的加群[{group_id}]请求，附言：{comment}"]))
                return
    except Exception as e:
        log(f"[Core请求处理] 好友列表获取失败: [{type(e)}] {e}")
    #通知管理员
    if owners:
        bot.send_private_msg(int(owners[0]),
            MessageChain([f"收到来自[{sender}][群:{source_group_id}]的加群[{group_id}]请求(group_request_flag:{flag},sub_type:{sub_type})，附言：\n{comment}"]))
    #通知群聊
    if str(sender) in allow_add_list(): return
    if not source_group_id: return
    bot.send_group_msg(source_group_id,
        MessageChain([f"收到来自[{sender}]的无端拉群请求，请管理注意(小生物拉群请先添加好友)"]))

def handle_friend_request(bot, message):
    owners = _owner(bot)
    if not owners: return
    sender = message.raw_data.get("user_id")
    comment = message.raw_data.get("comment", "")
    flag = message.raw_data.get("flag", "")
    #通知管理员
    bot.send_private_msg(int(owners[0]),
        MessageChain([f"收到来自[{sender}]的好友请求(private_request_flag:{flag})，附言：\n{comment}"]))

# == 管理员指令 ==

def handle_approve(bot, message):
    target = ""
    for msg in message.message:
        if msg.type == "reply":
            replied = bot.get_msg(msg.data.id)
            for seg in replied.data.message:
                if seg.get("type") == "text":
                    target += str(seg.get("data", {}).get("text", ""))
            break
    if not target or target.find("request_flag:") == -1: return
    #提取括号内内容
    target = target[target.find("(")+1:]
    target = target[:target.find(")")]
    flag_part = target[target.find("request_flag:")+len("request_flag:"):]
    flag = flag_part.split(",")[0].strip()
    sub_type = ""
    if "sub_type:" in flag_part:
        sub_type = flag_part[flag_part.find("sub_type:")+len("sub_type:"):].strip()
    log(f"flag: {flag}")
    log(f"target: {target}")
    if not flag: return
    owners = _owner(bot)
    if "group" in target:
        bot.set_group_add_request(flag=flag, sub_type=sub_type, approve=True)
        if owners:
            bot.send_private_msg(int(owners[0]), MessageChain([f"通过了加群请求[{flag}]"]))
    elif "private" in target:
        bot.set_friend_add_request(flag=flag, approve=True)
        if owners:
            bot.send_private_msg(int(owners[0]), MessageChain([f"通过了的好友请求[{flag}]"]))

def handle_add_allow(bot, message):
    raw_message = message.text[len("添加白名单"):].strip()
    user_ids = raw_message.split(" ")
    if not user_ids or not raw_message: return
    added = []
    for user_id in user_ids:
        if not user_id.isdigit(): continue
        if add_allow(user_id):
            added.append(str(user_id))
    if added:
        owners = _owner(bot)
        if owners:
            bot.send_private_msg(int(owners[0]), MessageChain([f"用户{added}白名单已添加"]))
