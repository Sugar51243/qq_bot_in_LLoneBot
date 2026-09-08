
# == Tsugu猜谱面/猜卡面模块 ==

import io, os, base64, random, threading, traceback
from datetime import datetime, timedelta
from PIL import Image
from OneBotConnecter.types import MessageChain, ImageMessage
from OneBotConnecter.loger.log_info import log
from src.project_locator.project_locator import get_project_location
from src.db_handler.plugin_db import get_plugin_state, dumps, loads
from src.plugins.tsugu_plugin.config import load_config
from src.plugins.tsugu_plugin.db import db
from src.plugins.tsugu_plugin.call_tsugu import call_net
from src.plugins.tsugu_plugin.chart import sreachFromNameMode
from src.plugins.tsugu_plugin.card import getImage
from src.tools.image_cuter import split_image
from src.tools.reply_message import feedback
from src.plugins.score.scores import add_scroes

# == 跨消息状态 ==
state = get_plugin_state("tsugu")

def guess_char_list() -> dict:
    if "guess_char_list" not in state: state["guess_char_list"] = {}
    return state["guess_char_list"]

def guess_card_list() -> dict:
    if "guess_card_list" not in state: state["guess_card_list"] = {}
    return state["guess_card_list"]

def guess_thread() -> dict:
    if "guess_thread" not in state: state["guess_thread"] = {}
    return state["guess_thread"]

#猜谱
def guess_chart(bot, message, raw_message, num = 0):
    if message.scene_id in guess_char_list().keys() or message.scene_id in guess_card_list().keys():
        message_chain = MessageChain(["\n[TSUGU]已有未完成的猜谱游戏，请先结束该游戏"])
        feedback(message, message_chain)
        return
    log(f"[TSUGU]猜谱 - 请求歌曲列表")
    song_url = "https://bestdori.com//api/songs/all.7.json"
    song_list = call_net(song_url)
    log(f"歌曲列表[{len(song_list)}]: {song_list}")
    log(f"过滤至只剩难度>=26")
    temp = {}
    for song in song_list:
        for d in song_list[song]["difficulty"]:
            if song_list[song]["difficulty"][d]["playLevel"]>=26:
                temp[song] = song_list[song]
                break
    log(f"歌曲列表[{len(temp)}]: {temp}")
    idx = random.randint(0, len(temp)-1)
    charID = list(temp)[idx]
    log(f"随机目标: {charID}")
    song = song_list[charID]
    d_list = list(song["difficulty"].keys())[3:]
    for d in d_list:
        if song["difficulty"][d]["playLevel"]<26:
            d_list.remove(d)
    d = d_list[random.randint(0, len(d_list)-1)]
    log(f"随机难度: {d}")
    try:
        charID = int(charID)
        bangdream_config = load_config()
        datapack = {
            "displayedServerList": [3,0],
            "songId": charID,
            "difficultyId": d,
            "compress": bangdream_config["compress"]
        }
        chart = call_net(f"{bangdream_config[bangdream_config['use_uri']]}/songChart", mode="post", data_pack=datapack)
        if chart[0]["type"] != "base64":
            raise SyntaxError()
        data = base64.b64decode(chart[0]["string"])
        im = Image.open(io.BytesIO(data))
        #图片切割
        image_list = split_image(image_data=im, num=num, cut_left=True, vertical_segment=((735/2) * 3))
        if num == 0: score = 10
        else: score = 21 - (num*1)
        #
        message_chain = MessageChain(["\n[TSUGU]猜猜这是哪首歌的谱面？\n"])
        for i in range(len(image_list)):
            #保存图片
            imageURL: str = f"{os.path.join(get_project_location(), 'data', 'plugin', 'tsugu_plugin', 'char')}/guess_{i}.jpg"
            os.makedirs(os.path.dirname(imageURL), exist_ok=True)
            image_list[i].save(imageURL)
            #发送图片
            message_chain.add(ImageMessage(imageURL))
        feedback(message, message_chain)
        package = {
            "charID": str(charID),
            "difficulty": str(d),
            "tips": 0,
            "score": score,
            "song_data": song,
            "chart_img": chart[0]["string"]
        }
        guess_char_list().update({message.scene_id: package})
        log(package)
    except Exception as e:
        message_chain = MessageChain(["\n[TSUGU]茨菇后台连接失败"])
        feedback(message, message_chain)
        tb = e.__traceback__
        formatted_tb = ''.join(traceback.format_tb(tb))
        log(f"[{type(e)}] {e}\n{formatted_tb}")
#猜谱回答
def answer_guess_chart(bot, message, answer):
    places_id = message.scene_id
    if places_id not in list(guess_char_list().keys()):
        return
    if answer.strip() in ["bzd", "不知道"]:
        song = guess_char_list().pop(places_id)
        charID = song["charID"]
        song_name = None
        for name in song["song_data"]["musicTitle"]:
            if name != None:
                song_name = name
                break
        d_set = {"3": "expert", "4": "special"}
        message_chain = MessageChain([f"\n[TSUGU]已结束猜谱，正确答案为:\n{charID}. {song_name} [{d_set[song['difficulty']]}] [lv{song['song_data']['difficulty'][song['difficulty']]['playLevel']}]"])
        message_chain.add(ImageMessage(f"base64://{song['chart_img']}"))
        feedback(message, message_chain)
    elif answer.strip() in ["提示"]:
        tips_id = guess_char_list()[places_id]["tips"]
        if tips_id <= 4 and guess_char_list()[places_id]["score"] > 0:
            guess_char_list()[places_id]["score"] = max(0, guess_char_list()[places_id]["score"] - 2)
        #物量 - 2
        if tips_id == 0:
            notes = guess_char_list()[places_id]["song_data"]["notes"][guess_char_list()[places_id]["difficulty"]]
            low = (notes // 250) * 250
            high = low + 250
            message_chain = MessageChain([f"\n[TSUGU]提示{tips_id+1}：该谱面物量为 {low} - {high}"])
            feedback(message, message_chain)
            guess_char_list()[places_id]["tips"] += 1
        #难度 - 2
        elif tips_id == 1:
            level = guess_char_list()[places_id]["song_data"]["difficulty"][guess_char_list()[places_id]["difficulty"]]
            message_chain = MessageChain([f"\n[TSUGU]提示{tips_id+1}：该谱面难度为 {level['playLevel']}"])
            feedback(message, message_chain)
            guess_char_list()[places_id]["tips"] += 1
        #乐团 - 2
        elif tips_id == 2:
            band_id = guess_char_list()[places_id]["song_data"]["bandId"]
            band_name = None
            band_url = "https://bestdori.com/api/bands/all.1.json"
            band_list = call_net(band_url)
            for name in band_list[str(band_id)]["bandName"]:
                if name == None: continue
                band_name = name
                break
            message_chain = MessageChain([f"\n[TSUGU]提示{tips_id+1}：该谱面所属乐团为 {band_name}"])
            feedback(message, message_chain)
            guess_char_list()[places_id]["tips"] += 1
        #BPM - 2
        elif tips_id == 3:
            bpm_data = guess_char_list()[places_id]["song_data"]["bpm"][guess_char_list()[places_id]["difficulty"]]
            if len(bpm_data) == 1:
                bpm = bpm_data[0]["bpm"]
                low = (bpm // 25) * 25
                high = low + 25
                message_chain = MessageChain([f"\n[TSUGU]提示{tips_id+1}：该谱面BPM为 {low} - {high}"])
            else:
                bpm1 = bpm_data[0]["bpm"]
                low = (bpm1 // 25) * 25
                bpm2 = bpm_data[-1]["bpm"]
                high = (bpm2 // 25) * 25 + 25
                message_chain = MessageChain([f"\n[TSUGU]提示{tips_id+1}：该谱面BPM为 {low} - {high}"])
            feedback(message, message_chain)
            guess_char_list()[places_id]["tips"] += 1
        #曲目种类 - 2
        elif tips_id == 4:
            song_type = guess_char_list()[places_id]["song_data"]["tag"]
            typeSet = {"normal":"原创", "anime":"动画", "tie_up":"翻唱"}
            message_chain = MessageChain([f"\n[TSUGU]提示{tips_id+1}：该谱面曲目种类为 {typeSet[song_type]}"])
            feedback(message, message_chain)
            guess_char_list()[places_id]["tips"] += 1
        #提示用完
        else:
            message_chain = MessageChain([f"\n[TSUGU]提示次数已用完"])
            feedback(message, message_chain)
    elif answer.strip().isdigit():
        charID = guess_char_list()[places_id]["charID"]
        if answer.strip() != charID:
            message_chain = MessageChain(["[TSUGU]猜错了"])
            feedback(message, message_chain)
            return
        song = guess_char_list().pop(places_id)
        song_name = None
        for name in song["song_data"]["musicTitle"]:
            if name == None:
                continue
            song_name = name
            break
        d_set = {"3": "expert", "4": "special"}
        message_chain = MessageChain([f"\n[TSUGU]回答正确！答案为:\n{charID}. {song_name} [{d_set[song['difficulty']]}] [lv{song['song_data']['difficulty'][song['difficulty']]['playLevel']}]\n"])
        message_chain.add(MessageChain([f"获得积分: {song['score']} 分"]))
        message_chain.add(ImageMessage(f"base64://{song['chart_img']}"))
        feedback(message, message_chain)
        add_scroes(bot, message, score=song["score"], add_type="chart", get_card_p=20+song['score'])
    else:
        charID = guess_char_list()[places_id]["charID"]
        parameters = answer.split(" ")
        temp = []
        for p in parameters:
            if len(p.strip()) <= 1:
                continue
            temp.append(p.strip())
        parameters = temp
        if len(parameters) >= 1:
            song_url = "https://bestdori.com//api/songs/all.7.json"
            song_list = call_net(song_url)
            result = sreachFromNameMode(song_list, parameters)
            if charID in result:
                song = guess_char_list().pop(places_id)
                song_name = None
                for name in song["song_data"]["musicTitle"]:
                    if name == None:
                        continue
                    song_name = name
                    break
                d_set = {"3": "expert", "4": "special"}
                message_chain = MessageChain([f"\n[TSUGU]回答正确！答案为:\n{charID}. {song_name} [{d_set[song['difficulty']]}] [lv{song['song_data']['difficulty'][song['difficulty']]['playLevel']}]\n"])
                message_chain.add(MessageChain([f"获得积分: {song['score']} 分"]))
                message_chain.add(ImageMessage(f"base64://{song['chart_img']}"))
                feedback(message, message_chain)
                add_scroes(bot, message, score=song["score"], add_type="chart", get_card_p=20+song['score'])
                return
        if message.at_me:
            message_chain = MessageChain(["[TSUGU]猜错了"])
            feedback(message, message_chain)

#猜卡面超时
def end_guess_card(bot, message, places_id, package):
    data = guess_card_list().get(places_id, None)
    if data == None: return
    if data["cardID"] != package[places_id]["cardID"]: return
    data = guess_card_list().pop(places_id)
    log(f"\n{datetime.now()}\n===================\n卡面计时器: 时间到！\n===================\n")
    cardID = data["cardID"]
    cardName = data["cardName"][0]
    characterName = data["characterName"][0]
    message_chain = MessageChain([f"\n[TSUGU]时间到！已结束猜卡面，正确答案为:\n{characterName}\n{cardID}. {cardName}\n"])
    message_chain.add(ImageMessage(data["cardURI"]))
    feedback(message, message_chain)
#猜卡面
def guess_card(bot, message, raw_message):
    #检查对象场景正在游戏中
    if message.scene_id in list(guess_char_list().keys()) or message.scene_id in list(guess_card_list().keys()):
        message_chain = MessageChain(["\n[TSUGU]已有未完成的猜谱游戏，请先结束该游戏"])
        feedback(message, message_chain)
        return
    #确认参数
    star = 3
    raw_message = raw_message.replace("猜卡面", "猜卡")
    raw_message = raw_message[2:].strip()
    if len(raw_message) > 0:
        if raw_message[-1] in ["*", "星"]:
            raw_message = raw_message[:-1].strip()
        if raw_message.isdigit():
            star = int(raw_message) if (int(raw_message) >= 3 and int(raw_message) <= 5) else 3
    #请求卡面列表
    log(f"[TSUGU]猜卡 - 请求卡面列表")
    card_list = {}
    cache_rows = db.query("SELECT card_id, data FROM card_cache;")
    if len(cache_rows) <= 0:
        data = call_net("https://bestdori.com/api/cards/all.0.json")
        if data != {}:
            for card_id, card_data in data.items():
                db.execute("INSERT OR IGNORE INTO card_cache (card_id, data) VALUES (?, ?);", (str(card_id), dumps(card_data)))
            cache_rows = db.query("SELECT card_id, data FROM card_cache;")
    for card_id, card_data_text in cache_rows:
        card_data = loads(card_data_text)
        if card_data: card_list[card_id] = card_data
    log(f"卡面列表[{len(card_list)}]: {card_list}")
    log(f"过滤至只剩>={star}星")
    temp = []
    for id in card_list:
        if card_list[id]["rarity"] < star:
            continue
        temp.append(id)
    log(f"卡面列表[{len(temp)}]: {temp}")
    if len(temp) <= 0:
        feedback(message, MessageChain(["\n[TSUGU]服务器网络连接出错"]))
        return
    #随机目标
    idx = random.randint(0, len(temp)-1)
    card_id = temp[idx]
    log(f"随机目标: {card_id}")
    card = card_list[card_id]
    character = call_net(f"https://bestdori.com/api/characters/{card['characterId']}.json")
    #图片切割
    uri = getImage(card, True)
    image_list = split_image(image_uri=uri, num=2, piece = 5)
    score = 5
    #保存图片
    imageURL: str = f"{os.path.join(get_project_location(), 'data', 'plugin', 'tsugu_plugin', 'card')}/guess.jpg"
    imageURL_1: str = f"{os.path.join(get_project_location(), 'data', 'plugin', 'tsugu_plugin', 'card')}/guess_1.jpg"
    os.makedirs(os.path.dirname(imageURL), exist_ok=True)
    image_list[0].convert("RGB").save(imageURL, format="JPEG")
    image_list[1].convert("RGB").save(imageURL_1, format="JPEG")
    #发送图片
    message_chain = MessageChain(["\n[TSUGU]猜猜这是谁的卡面？\n"])
    message_chain.add(ImageMessage(imageURL))
    message_chain.add(ImageMessage(imageURL_1))
    feedback(message, message_chain)
    #储存游戏信息
    package = {
        message.scene_id:{
            "cardID": str(card_id),
            "cardName": list(filter(lambda x: x is not None, card["prefix"])),
            "characterID": str(card["characterId"]),
            "characterName": list(filter(lambda x: x is not None, character["characterName"])),
            "score": score,
            "cardURI": uri
        }
    }
    guess_card_list().update(package)
    log(package)
    #计时
    time_out = 10 * 60
    timer = threading.Timer(time_out, end_guess_card, args=(bot, message, message.scene_id, package))
    guess_thread().update({message.scene_id: timer})
    timer.start()
    log(f"卡面计时器: [{time_out}]")
    log(f"过期时间为: {datetime.now() + timedelta(seconds=time_out)}")
#猜卡面回答
def answer_guess_card(bot, message, answer):
    #检查对象场景正在游戏中
    places_id = message.scene_id
    if places_id not in guess_card_list().keys():
        return
    #回答检查
    #不知道
    if answer.strip() in ["bzd", "不知道"]:
        card = guess_card_list().pop(places_id)
        cardID = card["cardID"]
        cardName = card["cardName"][0]
        characterName = card["characterName"][0]
        message_chain = MessageChain([f"\n[TSUGU]已结束猜卡面，正确答案为:\n{characterName}\n{cardID}. {cardName}\n"])
        message_chain.add(ImageMessage(card["cardURI"]))
        thread = guess_thread().pop(places_id, None)
        if thread: thread.cancel()
        feedback(message, message_chain)
    #卡面ID
    elif answer.strip().isdigit():
        card = guess_card_list()[places_id]
        #错误
        if answer.strip() != card["cardID"]:
            message_chain = MessageChain(["[TSUGU]猜错了"])
            feedback(message, message_chain)
            return
        #正确
        card = guess_card_list().pop(places_id)
        cardID = card["cardID"]
        cardName = card["cardName"][0]
        characterName = card["characterName"][0]
        message_chain = MessageChain([f"\n[TSUGU]回答正确！已结束猜卡面，正确答案为:\n{characterName}\n{cardID}. {cardName}\n"])
        message_chain.add(MessageChain([f"获得积分: {card['score']} 分"]))
        message_chain.add(ImageMessage(card["cardURI"]))
        thread = guess_thread().pop(places_id, None)
        if thread: thread.cancel()
        feedback(message, message_chain)
        add_scroes(bot, message, score=card["score"], add_type="chart", get_card_p=10)
    #模糊搜索
    else:
        card = guess_card_list()[places_id]
        #卡面名称或角色名称包含回答内容即视为正确
        if answer.strip() in card["cardName"] or answer.strip() in card["characterName"]:
            card = guess_card_list().pop(places_id)
            cardID = card["cardID"]
            cardName = card["cardName"][0]
            characterName = card["characterName"][0]
            message_chain = MessageChain([f"\n[TSUGU]回答正确！已结束猜卡面，正确答案为:\n{characterName}\n{cardID}. {cardName}\n"])
            message_chain.add(MessageChain([f"获得积分: {card['score']} 分"]))
            message_chain.add(ImageMessage(card["cardURI"]))
            thread = guess_thread().pop(places_id, None)
            if thread: thread.cancel()
            feedback(message, message_chain)
            add_scroes(bot, message, score=card["score"], add_type="chart")
            return
        #模糊搜索
        bangdream_config = load_config()
        uri = f"{bangdream_config[bangdream_config['use_uri']]}/fuzzySearch"
        datapack = {"text": answer}
        result = call_net(uri, mode="post", data_pack=datapack)
        #搜索结果检查
        #茨菇连接失败
        if result == {}:
            message_chain = MessageChain(["\n[TSUGU]网络连接不好，请再尝试"])
            feedback(message, message_chain)
            return
        log(result["data"])
        #搜索结果中包含正确卡面即视为正确
        try:
            if len(list(set(result["data"]["characterId"]))) > 5:
                log("搜索结果中包含多个角色，无法确认正确卡面")
                feedback(message, MessageChain(["\n[TSUGU]不要单次枚举多个选项哦~"]))
                return
            for c_id in result["data"]["characterId"]:
                #检查角色ID是否匹配
                if str(c_id) != card["characterID"]:
                    continue
                card = guess_card_list().pop(places_id)
                cardID = card["cardID"]
                cardName = card["cardName"][0]
                characterName = card["characterName"][0]
                message_chain = MessageChain([f"\n[TSUGU]回答正确！已结束猜卡面，正确答案为:\n{characterName}\n{cardID}. {cardName}\n"])
                message_chain.add(MessageChain([f"获得积分: {card['score']} 分"]))
                message_chain.add(ImageMessage(card["cardURI"]))
                thread = guess_thread().pop(places_id, None)
                if thread: thread.cancel()
                feedback(message, message_chain)
                add_scroes(bot, message, score=card["score"], add_type="chart", get_card_p=10)
                return
        except: pass
        #搜索结果中不包含正确卡面
        if message.at_me:
            message_chain = MessageChain(["[TSUGU]猜错了"])
            feedback(message, message_chain)
