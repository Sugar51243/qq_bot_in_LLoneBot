
# == 群事件播报插件入口 ==

# 由v1(src/plugin/功能注册器/main.py)中的入群欢迎/昵称播报/退群播报迁移至v2插件格式
# 本插件声明always_on: 事件处理不受场景注册限制(v1中注册器默认全场景运行)
# 各群可单独通过"播报开关"指令控制昵称/退群播报

import re, traceback
from OneBotConnecter.types import MessageChain, AtMessage
from OneBotConnecter.loger.log_info import log, error
from src.core.register import delete_scene_records
from src.plugins.group_events.db import nickname_enabled, leave_enabled, set_nickname_enabled, set_leave_enabled
from src.tools.reply_message import feedback

# == 入口 ==

def on_all_case(bot, message) -> bool: #call case including message, poke, request ...
    if "message" in message.event_type:
        return on_msg(bot, message=message)
    return on_event(bot, message)

def on_msg(bot, message) -> bool: # message
    raw_message = message.text
    if not raw_message: return False
    #播报开关
    if raw_message[0:4] in ["播报开关"]:
        handle_switch(bot, message, raw_message[4:].strip())
        return True
    return False

def on_event(bot, message) -> bool: # notice
    try:
        if message.event_type.startswith("group_increase"):
            handle_increase(bot, message)
            return True
        elif message.event_type.startswith("group_decrease"):
            handle_decrease(bot, message)
            return True
        elif message.event_type.startswith("group_card"):
            handle_card(bot, message)
            return True
    except Exception as e:
        tb = e.__traceback__
        formatted_tb = ''.join(traceback.format_tb(tb))
        log(f"[{type(e)}] {e}\n{formatted_tb}")
    return False

# == 事件处理 ==

def handle_increase(bot, message):
    group_id = message.raw_data.get("group_id")
    user_id = str(message.raw_data.get("user_id", ""))
    if user_id == str(bot.bot.user_id):
        #小生物入群
        send = MessageChain(["欢迎使用小生物，本群暂未启用任何功能。请使用'help'查询更多信息。"])
        bot.send_group_msg(group_id, send)
        log(f"[GroupEvents] 小生物入群[{group_id}]已发送欢迎信息")
        return
    if user_id in ["2854196310"]: return #v1中跳过的特殊用户
    send = MessageChain([AtMessage(user_id)])
    send.add(" 欢迎")
    bot.send_group_msg(group_id, send)

def handle_decrease(bot, message):
    user_id = str(message.raw_data.get("user_id", ""))
    if user_id == str(bot.bot.user_id):
        #小生物被移出群，清理该场景注册记录
        delete_scene_records(message.scene_id)
        log(f"[GroupEvents] 小生物被移出群[{message.scene_id}]，已清理注册记录")
        return
    group_id = str(message.raw_data.get("group_id", ""))
    if not leave_enabled(group_id): return
    operator_id = str(message.raw_data.get("operator_id", ""))
    msg = f"{user_id}退出了" if user_id == operator_id else f"{user_id}被{operator_id}踢离了"
    bot.send_group_msg(message.raw_data.get("group_id"), MessageChain([msg]))

def handle_card(bot, message):
    group_id = str(message.raw_data.get("group_id", ""))
    if not nickname_enabled(group_id): return
    card_old = message.raw_data.get("card_old", "")
    card_new = message.raw_data.get("card_new", "")
    if is_control_character_present(card_new): #bug name
        log(f"用户名称{str(card_new)}存在非法字符")
        return
    msg = f'''用户{message.raw_data.get("user_id")}{f"({card_old})" if card_old else ""}更改群昵称为{card_new}'''
    bot.send_group_msg(message.raw_data.get("group_id"), MessageChain([msg]))

# == 指令处理 ==

def handle_switch(bot, message, raw_message):
    raw_message = raw_message.split(" ")
    if not raw_message[0]:
        send = MessageChain([f"请指定模式和群号\n播报开关 (all/昵称/退群) 群号"])
        feedback(message, send)
        return
    elif len(raw_message) == 2: mod, group_id = raw_message
    elif len(raw_message) == 1:
        #单参数: 模式(默认本群) 或 群号(默认all)
        if raw_message[0] in ["all", "昵称", "退群"]:
            mod, group_id = raw_message[0], str(message.raw_data.get("group_id", ""))
        else:
            mod, group_id = "all", raw_message[0]
    else: mod, group_id = raw_message[0], raw_message[1]
    if not group_id: group_id = str(message.raw_data.get("group_id", ""))
    #
    if mod not in ["all", "昵称", "退群"]:
        send = MessageChain([f"无效的模式: {mod}"])
        feedback(message, send)
        return
    #
    if not group_id.isdigit():
        send = MessageChain([f"无效的群号: {group_id}"])
        feedback(message, send)
        return
    #
    try:
        member_data = bot.get_group_member_info(int(group_id), int(message.user_id))
        role = member_data.data.role
        if role not in ["owner", "admin"]:
            raise Exception("权限不足")
    except Exception as e:
        send = MessageChain([f"你并非该群管理/群主"])
        feedback(message, send)
        return
    #
    if mod == "all":
        #退群播报
        allow_leave = not leave_enabled(group_id)
        set_leave_enabled(group_id, allow_leave)
        #昵称播报
        allow_name = not nickname_enabled(group_id)
        set_nickname_enabled(group_id, allow_name)
        #
        send = MessageChain([f"昵称播报及退群播报开关已切换为: {allow_name} | {allow_leave}"])
        feedback(message, send)
        return
    elif mod == "昵称":
        allow_name = not nickname_enabled(group_id)
        set_nickname_enabled(group_id, allow_name)
        send = MessageChain([f"昵称播报开关已切换为: {allow_name}"])
        feedback(message, send)
        return
    elif mod == "退群":
        allow_leave = not leave_enabled(group_id)
        set_leave_enabled(group_id, allow_leave)
        send = MessageChain([f"退群播报开关已切换为: {allow_leave}"])
        feedback(message, send)
        return

# 检测非法字符
def is_control_character_present(word: str):
    if '�' in word:
        return True
    elif re.search(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', word):
        return True
    else:
        return False
