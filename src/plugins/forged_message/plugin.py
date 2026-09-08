
# == 伪造信息文件 ==

# 由v1(src/plugin/伪造信息/main.py)迁移至v2插件格式
# 仅机器人管理员可用(对应v1中仅bot自身账号可触发)

from OneBotConnecter.types import MessageChain, ImageMessage, AtMessage, ForwardChain, NodeMessage
from OneBotConnecter.loger.log_info import log
from src.tools.reply_message import feedback

# == 入口 ==

def on_all_case(bot, message) -> bool: #call case including message, poke, request ...
    if "message" in message.event_type:
        return on_msg(bot, message=message)
    return False

def on_msg(bot, message) -> bool: # message
    #仅机器人管理员可使用(对应v1中仅bot自身账号可触发)
    if str(message.user_id) not in [str(owner_id) for owner_id in bot.bot.owner]: return False
    raw_message = message.text
    if not raw_message: return False
    #裸插件ID"伪造信息"由核心显示帮助文档，避免冲突
    if raw_message[0:2] in ["伪造"] and raw_message.strip() != "伪造信息":
        raw_message = raw_message.replace("伪造信息", "伪造")
        raw_message = raw_message[2:].strip()
        target_id = None
        target_name = None

        temp = raw_message.split(" ")
        temp = temp[0]
        if temp.isdigit():
            target_id = temp
            raw_message = raw_message.replace(f"{target_id}", "").strip()
            info = bot.get_stranger_info(user_id=int(target_id))
            try:
                target_name = info.data.nickname
            except:
                target_name = None

        message_list = [msg for msg in message.message]
        if not target_id:
            for msg in message_list:
                if msg.type == "at":
                    target_id = str(msg.data.qq)
                    try: target_name = msg.data.name if msg.data.name else str(target_id)
                    except: target_name = str(target_id)
                    message_list.remove(msg)
                    break

        if not target_id:
            feedback(message, MessageChain(["未识别到目标用户"]))
            return True

        if (str(target_id) in [str(owner_id) for owner_id in bot.bot.owner] or str(target_id) == str(bot.bot.user_id)) and str(message.user_id) not in [str(owner_id) for owner_id in bot.bot.owner]:
            feedback(message, MessageChain(["还想伪造bot主的信息？想屁吃呢？"]))
            return True

        if len(message_list)<1:
            feedback(message, MessageChain(["未识别到内容"]))
            return True

        send_message = MessageChain([])
        for msg in message_list:
            if msg.type == "at":
                at_target = str(msg.data.qq)
                send_message.add(AtMessage(at_target))
                send_message.add(MessageChain([f" "]))
            elif msg.type == "text":
                text = msg.data.text
                if text.strip():
                    if text[0:2] == "伪造":
                        text = text.replace("伪造信息", "伪造")
                        text = text.replace("伪造", "")
                        text = text.strip()
                    if target_id in text:
                        text = text.replace(str(target_id), "")
                        text = text.strip()
                    if text.strip(): send_message.add(MessageChain([f"{text.strip()}"]))
            elif msg.type == "image":
                url = msg.data.url
                send_message.add(ImageMessage(url))
        node = NodeMessage(uin=int(target_id), name=target_name if target_name else str(target_id), content=send_message.to_send_message())
        send_message = ForwardChain(node)
        message.reply_message(send_message)
        return True
    return False
