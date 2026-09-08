
# == 远行商人插件入口 ==

# 由v1(src/plugin/远行商人/main.py)迁移至v2插件格式
# 本文件负责指令路由，各模块:
#   db(推送轮次记录) / merchant(API与数据格式化) / listener(后台自动推送)
# 后台推送通过plugin_listener入口在bot初始化时由main.py启动

from OneBotConnecter.types import MessageChain
from src.plugins.traveling_merchant.merchant import get_data
from src.plugins.traveling_merchant.listener import plugin_listener
from src.tools.reply_message import feedback

# == 入口 ==

def on_all_case(bot, message) -> bool: #call case including message, poke, request ...
    if "message" in message.event_type:
        return on_msg(bot, message=message)
    return False

def on_msg(bot, message) -> bool: # message
    if not message.text: return False
    #查询指令(裸插件ID"远行商人"由核心显示帮助文档，避免冲突)
    if message.text in ["远行", "远商"]:
        shop_data = get_data()
        feedback(message, MessageChain([shop_data]))
        return True
    return False
