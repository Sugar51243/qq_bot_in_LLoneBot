
# == 回复消息工具 ==

# 由v1(src/tools/reply_message.py)迁移至v2
# 过长信息自动转为合并转发(v1行为: 超过word_limit时使用转发信息)

from OneBotConnecter.types import ForwardChain, MessageChain, NodeMessage, TextMessage
from src.config_reader.config_reader import read_bot_config


def feedback(message, send_message):
    if isinstance(send_message, ForwardChain):
        return message.reply_message(send_message)
    if not isinstance(send_message, MessageChain):
        if not isinstance(send_message, list):
            send_message = [send_message]
        send_message = MessageChain(send_message)
    messages = send_message.to_send_message()
    counter = 0
    for msg in messages:
        if msg.get("type", None) != "text":
            continue
        counter += len(msg.get("data", {}).get("text", ""))
    bot_config = read_bot_config()
    maxlimit = bot_config.get("word_limit", 250)
    if counter >= maxlimit:
        node = NodeMessage(content=messages)
        send_message = ForwardChain(node)
    return message.reply_message(send_message)
