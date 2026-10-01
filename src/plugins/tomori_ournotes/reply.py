

# == Tomori OurNotes回复工具 ==

# 本插件的回复统一走这里(各模块以同名feedback导入, 调用点无需改动):
#   多图返回(图片数 >= MULTI_IMAGE_THRESHOLD)时, 把内容嵌套至聊天记录(合并转发)再发送,
#   其余情况沿用核心feedback(过长文本自动转合并转发)

from OneBotConnecter.types import ForwardChain, MessageChain, NodeMessage
from src.tools.reply_message import feedback as core_feedback

#图片数达到该值即嵌套为聊天记录(合并转发)
MULTI_IMAGE_THRESHOLD = 2

#统计消息链中的图片数
def count_images(send_message) -> int:
    if not isinstance(send_message, MessageChain):
        return 0
    return sum(1 for m in send_message.message if getattr(m, "message_type", None) == "image")

def feedback(message, send_message):
    if isinstance(send_message, MessageChain) and count_images(send_message) >= MULTI_IMAGE_THRESHOLD:
        node = NodeMessage(content=send_message.to_send_message())
        return message.reply_message(ForwardChain(node))
    return core_feedback(message, send_message)
