
# == Score猜群友模块 ==

import os, random
from OneBotConnecter.types import MessageChain, ImageMessage
from OneBotConnecter.loger.log_info import log
from src.project_locator.project_locator import get_project_location
from src.db_handler.plugin_db import get_plugin_state
from src.plugins.score.scores import add_scroes
from src.tools.image_cuter import split_image
from src.tools.reply_message import feedback

# == 跨消息状态 ==
state = get_plugin_state("小生物积分")
if "guess_users" not in state: state["guess_users"] = {} #猜群友

def guess_users() -> dict:
    return state["guess_users"]

#猜群友
def guess_user(bot, message):
    if str(message.raw_data.get("group_id")) in list(guess_users().keys()):
        message_chain = MessageChain(["\n已有未完成的猜头像游戏，请先结束该游戏"])
        feedback(message, message_chain)
        return
    #更新群员名单
    member_list_data = bot.get_group_member_list(group_id=message.raw_data.get("group_id"))
    log(f"{member_list_data.raw_data}")
    member_list: list = member_list_data.data
    exclude_ids = [str(message.user_id), str(bot.bot.user_id)]
    member_list = [member_list[i]['user_id'] for i in range(len(member_list)) if str(member_list[i]['user_id']) not in exclude_ids]
    #
    if len(member_list) <= 0:
        return
    target_id = member_list[random.randint(0,len(member_list)-1)]
    #
    info = bot.get_group_member_info(group_id=message.raw_data.get("group_id"), user_id=target_id, no_cache=True)
    log(f"{info.raw_data}")
    name = info.data.nickname
    card = info.data.card
    if not card.strip(): card = None
    if str(message.raw_data.get("group_id")) in list(guess_users().keys()):
        message_chain = MessageChain(["\n已有未完成的猜头像游戏，请先结束该游戏"])
        feedback(message, message_chain)
        return
    guess_users().update({str(message.raw_data.get("group_id")): {"id": str(target_id), "nickName": name, "card": card}})
    #
    avatar = f"https://q1.qlogo.cn/g?b=qq&nk={target_id}&s=640"
    piece = random.randint(3, 6)
    image_list = split_image(image_uri = avatar, num=2, piece=piece)
    #
    #保存图片
    imageURL_1: str = f"{os.path.join(get_project_location(), 'data', 'plugin', 'score', 'temp')}/guess_1.jpg"
    imageURL_2: str = f"{os.path.join(get_project_location(), 'data', 'plugin', 'score', 'temp')}/guess_2.jpg"
    os.makedirs(os.path.dirname(imageURL_1), exist_ok=True)
    image_list[0].convert("RGB").save(imageURL_1, format="JPEG")
    image_list[1].convert("RGB").save(imageURL_2, format="JPEG")
    message_chain = MessageChain(["\n猜猜这是哪位群友？\n"])
    message_chain.add(ImageMessage(imageURL_1))
    message_chain.add(ImageMessage(imageURL_2))
    feedback(message, message_chain)

def answer_guess_user(bot, message):
    if str(message.raw_data.get("group_id")) not in guess_users().keys():
        return
    for answer in message.message:
        if answer.type == "at":
            if str(answer.data.qq) == str(bot.bot.user_id):
                continue
            answer = str(answer.data.qq).strip()
        elif answer.type == "text":
            answer = str(answer.data.text).strip()
        else: pass
        try:
            if answer.strip() in ["bzd", "不知道"]:
                user = guess_users().pop(str(message.raw_data.get("group_id")))
                user_id = user["id"]
                nickName = user["nickName"]
                if user["card"] != None: nickName = user["card"]
                message_chain = MessageChain([f"\n正确答案为:\n{nickName}"])
                message_chain.add(ImageMessage(f"https://q1.qlogo.cn/g?b=qq&nk={user_id}&s=640"))
                feedback(message, message_chain)
            elif answer.strip().isdigit():
                answer = str(answer.strip())
                target = str(guess_users()[str(message.raw_data.get("group_id"))]["id"])
                if answer == target:
                    user = guess_users().pop(str(message.raw_data.get("group_id")))
                    nickName = user["nickName"]
                    if user["card"] != None: nickName = user["card"]
                    message_chain = MessageChain([f"\n正确! 答案为:\n{nickName}"])
                    message_chain.add(ImageMessage(f"https://q1.qlogo.cn/g?b=qq&nk={user['id']}&s=640"))
                    feedback(message, message_chain)
                    add_scroes(bot, message, 1, get_card_p=5)
            else:
                nickName = guess_users()[str(message.raw_data.get("group_id"))]["nickName"]
                card = guess_users()[str(message.raw_data.get("group_id"))]["card"]
                if answer.strip() == nickName or answer.strip() == card:
                    user = guess_users().pop(str(message.raw_data.get("group_id")))
                    if card != None: nickName = user["card"]
                    message_chain = MessageChain([f"\n正确! 答案为:\n{nickName}"])
                    message_chain.add(ImageMessage(f"https://q1.qlogo.cn/g?b=qq&nk={user['id']}&s=640"))
                    feedback(message, message_chain)
                    add_scroes(bot, message, 1, get_card_p=5)
                    return
                if message.at_me:
                    feedback(message, MessageChain(["猜错了"]))
        except: pass
