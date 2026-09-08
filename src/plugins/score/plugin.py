
# == 积分系统插件入口 ==

# 由v1(src/plugin/小生物积分/main.py)迁移至v2插件格式
# 本文件仅负责指令路由，各功能按模块划分:
#   db(数据库) / scores(积分核心) / guess_user(猜群友)

from OneBotConnecter.types import MessageChain
from src.plugins.score.scores import guess_ranking, checkScores, randAddScroes, give_score, datily_get_card, datily_get_score
from src.plugins.score.scores import get_user_score, use_card
from src.plugins.score.guess_user import guess_user, answer_guess_user, guess_users
from src.tools.reply_message import feedback

# == 入口 ==

def on_all_case(bot, message) -> bool: #call case including message, poke, request ...
    if "message" in message.event_type:
        return on_msg(bot, message=message)
    return False

def on_msg(bot, message) -> bool: # message
    raw_message = message.text
    if not raw_message: return False
    # == 积分系统 ==
    #排名
    if raw_message[0:2] in ["排名", "排行"]:
        num = 10
        if raw_message[2:].strip().isdigit():
            num = int(raw_message[2:].strip())
        guess_ranking(message, num = num)
        return True
    #查分
    elif raw_message in ["查分", "我的积分"]:
        checkScores(message)
        return True
    #笨蛋机
    elif raw_message[0:1] in ["土", "赌"]:
        num = 10
        if raw_message[1:].strip().isdigit():
            if int(raw_message[1:].strip()) >= 10:
                num = int(raw_message[1:].strip())
            else:
                msg = MessageChain(["最低投注积分为10分 "])
                message.reply_message(msg)
                return True
        elif len(raw_message[1:]) > 0: return True
        randAddScroes(message, input_score = num)
        return True
    #卡牌加成开关
    elif raw_message in ["加成开关"]:
        use_card_switch = use_card(message)
        msg = MessageChain(["\n已关闭使用卡牌加成，下次获得分数将不再有额外加成！"])
        if use_card_switch:
            msg = MessageChain(["\n已开启使用卡牌加成，下次获得分数将有额外加成哦！"])
        feedback(message, msg)
        return True
    #加成列表
    elif raw_message in ["加成列表"]:
        data = get_user_score(message)
        if len(data["cards"]) == 0:
            msg = MessageChain(["你当前没有任何加成卡牌哦！"])
        else:
            msg = MessageChain(["\n你当前的加成卡牌列表:"])
            for i, card in enumerate(data["cards"]):
                msg.add(MessageChain([f"\n{i+1}. 加成倍率: {card}"]))
        feedback(message, msg)
        return True
    elif "送分" in raw_message or "赠送积分" in raw_message:
        give_score(bot, message)
        return True
    elif raw_message in ["每日加成"]:
        get_card_success, score = datily_get_card(message)
        if get_card_success:
            msg = MessageChain([f"\n成功获得了每日加成卡牌！加成: {score}"])
        else:
            msg = MessageChain(["\n你今天已经获得过每日加成卡牌了哦！"])
        feedback(message, msg)
        return True
    elif raw_message in ["每日积分"]:
        if datily_get_score(bot, message):
            msg = MessageChain(["\n成功获得了每日积分(10分)！"])
        else:
            msg = MessageChain(["\n你今天已经获得过每日积分了哦！或者你的总积分已经超过50分了哦！"])
        feedback(message, msg)
        return True
    #猜群友
    elif message.event_type == "group_message":
        if raw_message in ["猜头像", "猜群友"]:
            guess_user(bot, message)
            return True
        elif str(message.raw_data.get("group_id")) in list(guess_users().keys()) and raw_message != "":
            answer_guess_user(bot, message)
            return True
    return False
