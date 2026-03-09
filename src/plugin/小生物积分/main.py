
# == 积分系统插件文件 ==

#此文件为OneBot11-小生物的Tsugu积分涵数文件
#应用环境为LL-Bot v2.4.4

#如果不清楚具体作用，除配置外，请不要修改任何参数代码


#引用库
#  ==> pip自动下载缺失的库
# type: ignore
import time, random
from src.importer import import_package
from src.loger import log
from src.tools.reply_message import feedback
from src.tools.image_cuter import split_image
exec(import_package("requests"))
exec(import_package("Config", package_from= "config_io", package_pip_Name= "config-io"))
exec(import_package(
    "MessageChain, ImageMessage, RecordMessage, AtMessage, EmojiMessage, ReplyMessage", 
    package_from= "OneBotConnecter.MessageType", 
    package_pip_Name= "OneBotConnecter")
)
from src.plugin.功能注册器.main import get_places_id, help



score_list_path = "data/plugin/score/guess_scores.json"

guess_users = {} #猜群友


async def onMessage(bot, message, raw_message, be_at, msgType):
    # == 积分系统 ==
    #排名
    if raw_message[0:2] == "排名":
        num = 10
        if raw_message[2:].strip().isdigit():
            num = int(raw_message[2:].strip())
        await guess_ranking(bot, message, num = num)
    #查分
    elif raw_message[0:2] == "查分":
        await checkScores(bot, message)
    #笨蛋机
    elif raw_message[0:1] in ["土", "赌"]:
        num = 10
        if raw_message[1:].strip().isdigit():
            if int(raw_message[1:].strip()) >= 10:
                num = int(raw_message[1:].strip())
            else:
                msg = MessageChain(["最低投注积分为10分 "])
                callback = await bot.reply_to_message(message, msg)
                log(f"{callback}", needPrint=(bot.testMode))
                return
        elif len(raw_message[1:]) > 0: return
        await randAddScroes(bot, message, input_score = num)
    #卡牌加成开关
    elif raw_message in ["加成开关"]:
        use_card_switch = use_card(message)
        msg = MessageChain(["\n已关闭使用卡牌加成，下次猜分数将不再有额外加成！"])
        if use_card_switch:
            msg = MessageChain(["\n已开启使用卡牌加成，下次猜分数将有额外加成哦！"])
        await feedback(bot, message, msg)
    #help
    elif raw_message == "小生物积分":
        places_id = get_places_id(message)
        await help(bot, message, "小生物积分", places_id)
    #猜群友
    elif msgType =="Group_message":
        if raw_message in ["猜头像", "猜群友"]:
            await guess_user(bot, message)
        elif str(message["group_id"]) in list(guess_users.keys()) and raw_message != "":
            await answer_guess_user(bot, message, be_at)

# == 积分系统 ==
#排名
async def guess_ranking(bot, msg, num = 10):
    message = MessageChain(["\n小生物总分排名:"])
    #读取文件
    users = Config.load_from_file(score_list_path)
    #计算排名
    user_list = list(users.keys())
    user_list.sort(key=lambda uid: users[uid]["scores"], reverse=True)
    #输出排名
    rank = 1
    for uid in user_list:
        score = users[uid]["scores"]
        nickname = users[uid]["name"]
        message.add(MessageChain([f"\n{rank}. {nickname} - 总分: {int(score)} 分"]))
        rank += 1
        if rank > num:
            break
    await feedback(bot, msg, message)
#笨蛋机
async def randAddScroes(bot, msg, input_score: int = 10):
    #读取文件
    user_id = msg["sender"]["user_id"]
    if user_id is not str:
        user_id = str(user_id)
    #获取用户数据
    data = get_user_score(msg)
    #时间CD
    now_time = time.time()
    if (now_time - data["time"]) < 600.0:
        dif = data["time"]+600 - now_time
        message = MessageChain([f"\n每10分钟只能随机一次哦\n目前还差:{int(int(dif)/60)}分钟{int(int(dif)%60)}秒"])
        await feedback(bot, msg, message)
        return
    #检查积分是否足够
    if data["scores"] < input_score:
        message = MessageChain([f"你的总积分不足"])
        await feedback(bot, msg, message)
        return
    #随机倍率
    score = random.randint(1, 100)
    if score <= 5:
        score = 200
    elif score <= 20:
        score = 0
    elif score <= 60:
        score = random.randint(0, 100)
    else:
        score = random.randint(100, 200)
    add_score = int(input_score * (score/100))
    #输出信息
    message = MessageChain([f"\n投入积分:[{input_score}] * 随机倍率[{score/100}]\n获得随机积分: {add_score} 分"])
    await feedback(bot, msg, message)
    #更新数据
    reduce_score(msg, score=input_score, time=time.time())
    #更新积分
    await add_scroes(bot, msg, score=add_score, add_type="sp")
#查分
async def checkScores(bot, msg):
    data = get_user_score(msg)
    message = MessageChain([f"你的总积分为: {data["scores"]}"])
    await feedback(bot, msg, message)

#查分_json => {"scores", "chart", "card", "sp", "name", "cards", "use_card", "time"}
def get_user_score(msg):
    user_id = msg["sender"]["user_id"]
    if user_id is not str:
        user_id = str(user_id)
    users = Config.load_from_file(score_list_path)
    try:
        data = users[user_id]
    except:
        data = {"scores": 0, "chart": 0, "card": 0, "sp": 0, "name": msg["sender"]["nickname"], "cards": [], "use_card": True, "time": 0.0}
    users[user_id] = data
    users.dump_to_file(score_list_path)
    return data
#加分
async def add_scroes(bot, msg, score = 0, add_type: str = "sp", get_card_p = 0, max_card_bonus = 500):
    old_rank = -1
    user_id = msg["sender"]["user_id"]
    if user_id is not str:
        user_id = str(user_id)
    #读取文件
    data = get_user_score(msg)
    #计算排名
    users = Config.load_from_file(score_list_path)
    try:
        user_list = list(users.keys())
        user_list.sort(key=lambda uid: users[uid]["scores"], reverse=True)
        old_rank = user_list.index(user_id)
    except: pass
    #更新数据
    if data["use_card"] and score > 0:
        card_bonus = 1
        if len(data["cards"]) > 0:
            card_bonus = 1 + data["cards"].pop(0)
        score = score * card_bonus
        if card_bonus > 1:
            message = MessageChain([f"\n使用卡牌加成 x{card_bonus}，本次获得积分提升至 {int(score)} 分！"])
            await feedback(bot, msg, message)
    data["scores"] += score
    if add_type == "sp":
        data["sp"] += score
    else:
        data[add_type] += 1
    users.update({str(user_id): data})
    #写入文件
    users.dump_to_file(score_list_path)
    #
    if score > 0:
        message = MessageChain([f"获得积分 {int(score)} ！"])
    #计算排名
    user_list = list(users.keys())
    user_list.sort(key=lambda uid: users[uid]["scores"], reverse=True)
    rank = user_list.index(user_id)
    #输出信息
    if rank > (old_rank) or old_rank == -1:
        message = MessageChain([f"恭喜你！你的总分提升到第 {rank+1} 名！"])
        await feedback(bot, msg, message)
    #5%概率获得小卡片
    if random.randint(0, 99) < get_card_p:
        card_score = random.randint(1, max_card_bonus) / 100
        get_card(msg, card_score=card_score)
        message = MessageChain([f"\n获得了一个小卡片[倍率: {card_score}]！下次猜分数将有额外加成哦！"])
        await feedback(bot, msg, message)
#减分
def reduce_score(msg, score, time = None):
    user_id = msg["sender"]["user_id"]
    #读取文件
    data = get_user_score(msg)
    users = Config.load_from_file(score_list_path)
    if data["scores"] < score:
        return None
    data["scores"] -= score
    if time != None: data["time"] = time
    users.update({str(user_id): data})
    users.dump_to_file(score_list_path)
#
def get_card(msg, card_score):
    user_id = msg["sender"]["user_id"]
    if user_id is not str:
        user_id = str(user_id)
    #读取文件
    data = get_user_score(msg)
    users = Config.load_from_file(score_list_path)
    data["cards"].append(card_score)
    users.update({str(user_id): data})
    users.dump_to_file(score_list_path)
    return data["cards"]
#
def use_card(msg, use_card: bool = None):
    user_id = msg["sender"]["user_id"]
    if user_id is not str:
        user_id = str(user_id)
    #读取文件
    data = get_user_score(msg)
    users = Config.load_from_file(score_list_path)
    if use_card == None:
        use_card = not data["use_card"]
    data["use_card"] = use_card
    users.update({str(user_id): data})
    users.dump_to_file(score_list_path)
    return use_card

# == 猜群友 ==
#猜群友
async def guess_user(bot, msg):
    if str(msg["group_id"]) in list(guess_users.keys()):
        message = MessageChain(["\n已有未完成的猜头像游戏，请先结束该游戏"])
        await feedback(bot, msg, message)
        return
    #更新群员名单
    member_list_data = await bot.get_group_member_list(group_id=msg["group_id"])
    log(f"{member_list_data}", needPrint=(bot.testMode))
    member_list: list = member_list_data['data']
    member_list = [member_list[i]['user_id'] for i in range(len(member_list)) if member_list[i]['user_id'] != msg["sender"]["user_id"]]
    #
    target_id = member_list[random.randint(0,len(member_list)-1)]
    #
    info = await bot.get_group_member_info(group_id=msg["group_id"], user_id=target_id, no_cache=True)
    log(f"{info}", needPrint=(bot.testMode))
    name = info['data']['nickname']
    card = info['data']['card']
    if not card.strip(): card = None
    guess_users.update({str(msg["group_id"]): {"id": str(target_id), "nickName": name, "card": card}})
    #
    avatar = f"https://q1.qlogo.cn/g?b=qq&nk={target_id}&s=640"
    image_list = await split_image(image_uri = avatar, num=1)
    target = image_list[random.randint(0, len(image_list)-1)]
    #
    #保存图片
    imageURL: str = f"data/plugin/score/temp/guess.png"
    target.save(imageURL)
    message = MessageChain(["\n猜猜这是哪位群友？\n"])
    message.add(ImageMessage(f"file://{bot.localtion}/{imageURL}"))
    await feedback(bot, msg, message)

async def answer_guess_user(bot, msg, be_at):
    if str(msg["group_id"]) not in guess_users.keys():
        return
    for answer in msg["message"]:
        if answer["type"] == "at":
            answer = str(answer["data"]["qq"]).strip()
        elif answer["type"] == "text":
            answer = str(answer["data"]["text"]).strip()
        else: pass
        try:
            if answer.strip() in ["bzd", "不知道"]:
                user = guess_users.pop(str(msg["group_id"]))
                user_id = user["id"]
                nickName = user["nickName"]
                if user["card"] != None: nickName = user["card"]
                message = MessageChain([f"\n正确答案为:\n{nickName}"])
                message.add(ImageMessage(f"https://q1.qlogo.cn/g?b=qq&nk={user_id}&s=640"))
                await feedback(bot, msg, message)
            elif answer.strip().isdigit():
                answer = str(answer.strip())
                target = str(guess_users[str(msg["group_id"])]["id"])
                if  answer == target:
                    user = guess_users.pop(str(msg["group_id"]))
                    nickName = user["nickName"]
                    if user["card"] != None: nickName = user["card"]
                    message = MessageChain([f"\n正确! 答案为:\n{nickName}"])
                    message.add(ImageMessage(f"https://q1.qlogo.cn/g?b=qq&nk={user["id"]}&s=640"))
                    await feedback(bot, msg, message)
                    await add_scroes(bot,msg, 1, get_card_p=5)
            else:
                nickName = guess_users[str(msg["group_id"])]["nickName"]
                card = guess_users[str(msg["group_id"])]["card"]
                if answer.strip() == nickName or answer.strip() == card:
                    user = guess_users.pop(str(msg["group_id"]))
                    if card != None: nickName = user["card"]
                    message = MessageChain([f"\n正确! 答案为:\n{nickName}"])
                    message.add(ImageMessage(f"https://q1.qlogo.cn/g?b=qq&nk={user["id"]}&s=640"))
                    await feedback(bot, msg, message)
                    await add_scroes(bot,msg, 1, get_card_p=5)
                    return
                if be_at:
                    await feedback(bot, msg, MessageChain(["猜错了"]))
        except: pass
