
# == Score积分核心模块 ==

# 积分读写/排名/笨蛋机/加成卡/每日奖励/赠送积分
# 本模块的函数同时作为跨插件API使用(tsugu猜谱/猜卡、jrlp换老婆等)

import time, random
from OneBotConnecter.types import MessageChain, AtMessage, ForwardChain
from src.plugins.score.db import db
from src.tools.reply_message import feedback

#排名
def guess_ranking(message, num = 10):
    message_chain = MessageChain(["\n小生物总分排名:"])
    #读取数据库
    users = db.query("SELECT user_id, scores, name FROM users;")
    #计算排名
    user_list = [row for row in users]
    user_list.sort(key=lambda row: row[1], reverse=True)
    #输出排名
    rank = 1
    for row in user_list:
        score = row[1]
        nickname = row[2]
        score = number_to_chinese((int(score)))
        message_chain.add(MessageChain([f"\n{rank}. {nickname}-总分: {score}"]))
        rank += 1
        if rank > num:
            break
    feedback(message, message_chain)
#笨蛋机
def randAddScroes(message, input_score: int = 10):
    #获取用户数据
    data = get_user_score(message)
    #时间CD
    now_time = time.time()
    if (now_time - data["time"]) < 600.0:
        dif = data["time"]+600 - now_time
        message_chain = MessageChain([f"\n每10分钟只能随机一次哦\n目前还差:{int(int(dif)/60)}分钟{int(int(dif)%60)}秒"])
        feedback(message, message_chain)
        return
    #检查积分是否足够
    if data["scores"] < input_score:
        message_chain = MessageChain([f"你的总积分不足"])
        feedback(message, message_chain)
        return
    #随机倍率
    score = biased_random(input_score) #0.0000 ~ 2.0000
    add_score = input_score * score
    #输出信息
    nickname = message.raw_data.get("sender", {}).get("nickname", "")
    message_chain = MessageChain([f"{nickname}投入积分:\n[{number_to_chinese(input_score)}] * [{score*100:.2f}%]\n获得随机积分: {number_to_chinese(int(add_score))} 分"])
    Nodes = ForwardChain(message_chain)
    #更新数据
    old_rank = reduce_score(message, score=input_score, time=time.time())
    #更新积分
    add_scroes(None, message, score=add_score, add_type="sp", old_rank=old_rank, Nodes=Nodes)
#查分
def checkScores(message):
    data = get_user_score(message)
    message_chain = MessageChain([f"你的总积分为: \n{int(data['scores'])}\n({number_to_chinese(int(data['scores']))})"])
    feedback(message, message_chain)
#赠送积分
def give_score(bot, message, target_user_id = None):
    reply_id = None
    if target_user_id == None:
        for ms in message.message:
            if ms.type == "at":
                target_user_id = str(ms.data.qq)
            elif ms.type == "reply":
                reply_id = str(ms.data.id)
    if target_user_id == None and reply_id != None:
        reply_msg = bot.get_msg(reply_id)
        try:
            target_user_id = str(reply_msg.data.sender.user_id)
        except: pass
    if target_user_id == None:
        message_chain = MessageChain(["请至少回复一条消息或艾特一位用户来赠送积分哦！"])
        feedback(message, message_chain)
        return False
    #获取用户数据
    data = get_user_score(message)
    score = random.randint(1, 1000)
    #检查积分是否足够
    if data["scores"] < 10:
        message_chain = MessageChain([f"你的总积分不足"])
        feedback(message, message_chain)
        return False
    if data["scores"] < score:
        score = data["scores"]
    #更新数据
    reduce_score(message, score=score)
    #更新积分
    add_scroes(bot, message, score=score, add_type="sp", target_id=target_user_id, use_card=False, showRank=False)
    message_chain = MessageChain([f"成功赠送了{score}积分给用户 ", AtMessage(target_user_id), " !"])
    feedback(message, message_chain)
    return True
#每日加成
def datily_get_card(message):
    user_id = str(message.user_id)
    toDay = time.strftime("%Y-%m-%d", time.localtime())
    row = db.query_one("SELECT user_id FROM daily_cards WHERE date = ? AND user_id = ?;", (toDay, user_id))
    if row:
        return (False, 0)
    card = random.randint(1, 2000) / 1000
    get_card(message, card_score=card)
    db.execute("INSERT OR IGNORE INTO daily_cards (date, user_id) VALUES (?, ?);", (toDay, user_id))
    return (True, card)
#每日积分
def datily_get_score(bot, message):
    user_id = str(message.user_id)
    toDay = time.strftime("%Y-%m-%d", time.localtime())
    row = db.query_one("SELECT user_id FROM daily_scores WHERE date = ? AND user_id = ?;", (toDay, user_id))
    #检查是否已经获得过积分
    if row:
        return False
    #检查积分
    score = get_user_score(message)["scores"]
    if score >= 50:
        return False
    #更新积分
    add_scroes(bot, message, score=10, add_type="sp", use_card=False, showRank=False)
    db.execute("INSERT OR IGNORE INTO daily_scores (date, user_id) VALUES (?, ?);", (toDay, user_id))
    return True


#查分 => {"scores", "chart", "card", "sp", "name", "cards", "use_card", "time"}
def get_user_score(message, user_id = None):
    user_id = str(message.user_id) if user_id == None else str(user_id)
    row = db.query_one("SELECT scores, chart, card, sp, name, use_card, time FROM users WHERE user_id = ?;", (user_id,))
    if not row:
        name = message.raw_data.get("sender", {}).get("nickname", "")
        data = {"scores": 0, "chart": 0, "card": 0, "sp": 0, "name": name, "cards": [], "use_card": True, "time": 0.0}
        db.execute("INSERT OR IGNORE INTO users (user_id, scores, chart, card, sp, name, use_card, time) VALUES (?, 0, 0, 0, 0, ?, 1, 0.0);", (user_id, str(name)))
        return data
    cards = [card[0] for card in db.query("SELECT card_score FROM cards WHERE user_id = ? ORDER BY id;", (user_id,))]
    data = {"scores": row[0], "chart": row[1], "card": row[2], "sp": row[3], "name": row[4], "cards": cards, "use_card": bool(row[5]), "time": row[6]}
    return data
#加分
def add_scroes(bot, message, score = 0, add_type: str = "sp", get_card_p = 0, max_card_bonus = 500, target_id = None, use_card = True, showRank = True, old_rank = None, Nodes=None):
    old_rank = -1 if old_rank == None else old_rank
    user_id = str(message.user_id) if target_id == None else str(target_id)
    #获取用户数据
    data = get_user_score(message, user_id = user_id)
    #计算排名
    users = db.query("SELECT user_id, scores FROM users;")
    try:
        if old_rank == -1:
            user_list = [row for row in users]
            user_list.sort(key=lambda row: row[1], reverse=True)
            old_rank = [row[0] for row in user_list].index(user_id)
    except: pass
    #更新数据
    if data["use_card"] and score > 0 and use_card:
        card_bonus = 1
        if len(data["cards"]) > 0:
            card_bonus = 1 + data["cards"][0]
            oldest = db.query_one("SELECT id FROM cards WHERE user_id = ? ORDER BY id LIMIT 1;", (user_id,))
            if oldest:
                db.execute("DELETE FROM cards WHERE id = ?;", (oldest[0],))
        score = score * card_bonus
        if card_bonus > 1:
            message_chain = MessageChain([f"使用卡牌加成 x{card_bonus}，本次获得积分提升至 {number_to_chinese(int(score))} 分！"])
            if Nodes: Nodes.add(message_chain)
            else: feedback(message, message_chain)
    data["scores"] += score
    data[add_type] = data.get(add_type, 0) + score
    _save_user_data(user_id, data)
    #输出信息 & 概率获得小卡片
    if score > 0:
        message_chain = MessageChain([f"获得积分 {number_to_chinese(int(score))} ！"])
        #概率获得小卡片
        if random.randint(0, 99) < get_card_p:
            card_score = random.randint(1, max_card_bonus) / 100
            message_chain = MessageChain([f"获得了一个小卡片[倍率: {card_score}]！下次获得分数将有额外加成哦！"])
            if Nodes: Nodes.add(message_chain)
            else: feedback(message, message_chain)
            # 小概率获得947大奖卡片 (10%概率，倍率9.47)
            if (card_score >= 4.7 or card_score == 0.47) and random.randint(0, 99) <= 9:
                card_score = 9.47
                message_chain = MessageChain([f"中大奖噜！卡片倍率已进化为{card_score}～"])
                if Nodes: Nodes.add(message_chain)
                else: feedback(message, message_chain)
            get_card(message, card_score=card_score, user_id=user_id)
    #计算排名
    if not showRank:
        if Nodes:
            message.reply_message(Nodes)
        return
    users = db.query("SELECT user_id, scores FROM users;")
    user_list = [row for row in users]
    user_list.sort(key=lambda row: row[1], reverse=True)
    rank = [row[0] for row in user_list].index(user_id)
    #输出信息
    if rank < (old_rank) or old_rank == -1:
        message_chain = MessageChain([f"恭喜你！你的总分提升到第 {rank+1} 名！"])
        if Nodes: Nodes.add(message_chain)
        else: feedback(message, message_chain)
    if Nodes:
        message.reply_message(Nodes)

#减分
def reduce_score(message, score, time = None):
    user_id = str(message.user_id)
    #获取用户数据
    data = get_user_score(message)
    if data["scores"] < score:
        return None

    users = db.query("SELECT user_id, scores FROM users;")
    user_list = [row for row in users]
    user_list.sort(key=lambda row: row[1], reverse=True)
    old_rank = [row[0] for row in user_list].index(user_id)

    data["scores"] -= score
    if time != None: data["time"] = time
    _save_user_data(user_id, data)
    return old_rank
#获取加成卡
def get_card(message, card_score, user_id = None):
    user_id = str(message.user_id) if user_id == None else str(user_id)
    db.execute("INSERT INTO cards (user_id, card_score) VALUES (?, ?);", (user_id, float(card_score)))
    cards = [card[0] for card in db.query("SELECT card_score FROM cards WHERE user_id = ? ORDER BY id;", (user_id,))]
    return cards
#使用加成卡
def use_card(message, use_card: bool = None):
    user_id = str(message.user_id)
    #获取用户数据
    data = get_user_score(message)
    if use_card == None:
        use_card = not data["use_card"]
    data["use_card"] = use_card
    _save_user_data(user_id, data)
    return use_card

def _save_user_data(user_id, data):
    db.execute("UPDATE users SET scores = ?, chart = ?, card = ?, sp = ?, name = ?, use_card = ?, time = ? WHERE user_id = ?;",
        (data["scores"], data["chart"], data["card"], data["sp"], str(data["name"]), 1 if data["use_card"] else 0, data["time"], user_id))

#分数倍率随机函数
def biased_random(user_input: int) -> float:
    if user_input < 10:
        raise ValueError("输入必须 >= 10")

    # Step 1: 固定 2 的概率为 2%
    if random.random() < 0.02:
        return 2.0000

    # Step 2: 输入 < 100000 时，至少 80% 在 [1,2)
    if user_input < 100000:
        prob_high = 0.80
        if random.random() < prob_high:
            return round(1 + random.random(), 4)
        else:
            alpha = min(user_input / 100000000, 10)
            r = random.random() ** alpha
            return round(r, 4 if r >= 0.001 else 0)

    # Step 3: 输入 ≥ 100000 且 ≤ 100000000 时，逐渐调整分布
    if user_input <= 100000000:
        prob_high = max(0.2, 0.80 - (user_input - 100000) / 200000)
        if random.random() < prob_high:
            return round(1 + random.random(), 4)
        else:
            alpha = min(user_input / 100000000, 10)
            r = random.random() ** alpha
            return round(r, 4 if r >= 0.001 else 0)

    # Step 4: 输入 > 100000000 时，固定概率分配
    p = random.random()
    if p < 0.05:  # 5% 概率在 [1.5,2)
        return round(1.5 + random.random() * 0.5, 4)
    elif p < 0.15:  # 6%~10% 概率在 [1,1.5)
        return round(1 + random.random() * 0.5, 4)
    else:  # 剩余概率在 [0,1)，偏向 0
        alpha = 10  # 强烈偏向 0
        r = random.random() ** alpha
        if r < 0.001 and random.random() < 0.10:  # 0 的最大概率 10%
            return 0.0000
        return round(r, 4)
#数字转中文单位
def number_to_chinese(num: int) -> str:
    """
    将数字转换为中文单位表示（万、亿、兆...）
    支持单位叠加（千万、万亿、千万亿等），固定两位小数输出
    """
    if num < 10000:
        return str(num)

    # 定义单位（每 10^4 进一位）
    units = ["", "万", "亿", "兆", "京", "垓", "秭", "穰", "沟", "涧", "正", "载"]

    # 找到合适的单位
    unit_index = 0
    value = float(num)
    while value >= 10000 and unit_index < len(units) - 1:
        value /= 10000
        unit_index += 1

    # 固定两位小数
    result = f"{value:.2f}{units[unit_index]}"

    # 处理叠加单位：当数值是 10、100、1000 时，转成「1千万」「1万亿」等
    if result.startswith(("10.00", "100.00", "1000.00")):
        int_value = int(float(result.split(units[unit_index])[0]))
        if int_value == 10:
            prefix = "1.00十"
        elif int_value == 100:
            prefix = "1.00百"
        elif int_value == 1000:
            prefix = "1.00千"
        else:
            prefix = str(int_value)
        result = f"{prefix}{units[unit_index]}"

    return result
