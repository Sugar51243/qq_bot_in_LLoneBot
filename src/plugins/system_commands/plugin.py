
# == 系统指令插件入口 ==

# 赞我指令(通用功能，需在场景内启用本插件)
# 由v1(src/plugin/功能注册器/main.py)中的赞我迁移至v2插件格式
# 原管理员指令(重启/退群/同意/添加白名单)已移至v2核心内置指令

import traceback
from OneBotConnecter.types import MessageChain
from OneBotConnecter.loger.log_info import log
from src.tools.reply_message import feedback

like_times = 10

# == 入口 ==

def on_all_case(bot, message) -> bool: #call case including message, poke, request ...
    if "message" in message.event_type:
        return on_msg(bot, message=message)
    return False

def on_msg(bot, message) -> bool: # message
    raw_message = message.text
    if not raw_message: return False
    #赞我
    if raw_message in ["赞我"]:
        try:
            bot.send_like(user_id=int(message.user_id), times=like_times)
            feedback(message, MessageChain(["已经尝试赞你了，如果没有就是赞不了"]))
        except Exception as e:
            tb = e.__traceback__
            formatted_tb = ''.join(traceback.format_tb(tb))
            log(f"[{type(e)}] {e}\n{formatted_tb}")
        return True
    return False
