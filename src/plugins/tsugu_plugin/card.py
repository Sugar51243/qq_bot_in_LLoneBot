
# == Tsugu卡片模块 ==

# 查卡面/查卡/随机查卡/随机卡面/查卡池/卡池模拟/查角色

import os, random, requests
from OneBotConnecter.types import MessageChain, ImageMessage
from OneBotConnecter.loger.log_info import log
from src.project_locator.project_locator import get_project_location
from src.plugins.tsugu_plugin.config import load_config
from src.plugins.tsugu_plugin.call_tsugu import call_tsugu, call_net
from src.tools.reply_message import feedback

#查卡面
def card_face(bot, message, cardID):
    if random.randint(1,100) > 50 and str(cardID) == "947":
        send = MessageChain([" [TSUGU]不许查!!!"])
        feedback(message, send)
        return
    url = f"https://bestdori.com/api/cards/{cardID}.json"
    data = call_net(url)
    if data == {}:
        send = MessageChain(["\n[TSUGU]无法连接bestdori服务器"])
        feedback(message, send)
        return
    before_train = getImage(data, False)
    if before_train[-3:] == "mp4":
        file_path = os.path.join(get_project_location(), load_config()["card_temp_path"], f"{cardID}.mp4")
        if not os.path.exists(file_path):
            result = requests.get(before_train, timeout=10)
            if result.status_code != 200:
                send = MessageChain(["\n[TSUGU]无法连接bestdori服务器"])
                feedback(message, send)
                return
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            file = open(file_path, "wb")
            file.write(result.content)
            file.close()
        send_gif(bot, message, file_path, f"{cardID}.mp4")
        return
    send = MessageChain(["[TSUGU]", ImageMessage(before_train)])
    if data["rarity"] >= 3:
        after_train = getImage(data, True)
        send.add(ImageMessage(after_train))
    feedback(message, send)
#查卡
def sreachCard(bot, message, cardID):
    bangdream_config = load_config()
    if cardID.isdigit():
        datapack = {
            "displayedServerList": [3,0],
            "text": cardID,
            "useEasyBG": bangdream_config["useEasyBG"],
            "compress": bangdream_config["compress"]
        }
    else:
        uri = f"{bangdream_config[bangdream_config['use_uri']]}/fuzzySearch"
        datapack = {"text": cardID}
        result = call_net(uri, mode="post", data_pack=datapack)
        if result == {}:
            message_chain = MessageChain(["\n[TSUGU]茨菇后台连接失败"])
            feedback(message, message_chain)
            return
        if result["status"] == "success":
            datapack = {
                "displayedServerList": [3,0],
                "fuzzySearchResult": result["data"],
                "useEasyBG": bangdream_config["useEasyBG"],
                "compress": bangdream_config["compress"]
            }
        else:
            message_chain = MessageChain(["\n[TSUGU]茨菇后台连接失败"])
            feedback(message, message_chain)
            return
    mode = "searchCard"
    message_chain = call_tsugu(mode, datapack)
    feedback(message, message_chain)
#随机查卡
def randomSreachCard(bot, message):
    try:
        url = "https://bestdori.com/api/cards/all.0.json"
        data = call_net(url)
        if data == {}: raise Exception()
    except:
        message_chain = MessageChain(["[TSUGU]服务器网络连接出错"])
        feedback(message, message_chain)
        return
    index = list(data.keys())
    idx = random.randint(0, len(index)-1)
    cardID = index[idx]
    if cardID == "":
        return
    sreachCard(bot, message, cardID)
#随机卡面
def randomGetCard(bot, message):
    message_chain = MessageChain(["\n"])
    try:
        url = "https://bestdori.com/api/cards/all.0.json"
        data = call_net(url)
        if data == {}: raise Exception()
    except:
        message_chain = MessageChain(["[TSUGU]服务器网络连接出错"])
        feedback(message, message_chain)
        return
    index = list(data.keys())
    idx = random.randint(0, len(index)-1)
    cardID = index[idx]
    if cardID == "":
        return
    try:
        url = f"https://bestdori.com/api/cards/{cardID}.json"
        data = call_net(url)
        if data == {}: raise Exception()
    except:
        message_chain = MessageChain(["[TSUGU]服务器网络连接出错"])
        feedback(message, message_chain)
        return
    train = False
    if data['rarity']>=3:
        if random.randint(1, 100) <= 50: train = True
        else: train = False
    message_chain.add(ImageMessage(getImage(data, train)))
    feedback(message, message_chain)
#从bestdori拉取卡面图片
def getImage(data, train, server="jp"):
    res = data['resourceSetName']
    servers = ["jp", "en", "tw", "cn", "kr"]
    for i in range(len(servers)):
        if data["prefix"][i] != None:
            server = servers[i]
            break
    animation = "https://bestdori.com/assets/en/movie/animation_episode/mov016001_rip/mov016001.mp4"
    if data.get("animation", {}).get("assetBundleName", None):
        ass_name = data["animation"]["assetBundleName"]
        animation = f"https://bestdori.com/assets/{server}/movie/animation_episode/{ass_name}_rip/{ass_name}.mp4"
        return animation
    if train:
        image = f"https://bestdori.com/assets/{server}/characters/resourceset/{res}_rip/card_after_training.png"
    else:
        image = f"https://bestdori.com/assets/{server}/characters/resourceset/{res}_rip/card_normal.png"
    return image
#查卡池
def self_search_gacha(bot, message, gacha_id):
    bangdream_config = load_config()
    mode = "searchGacha"
    datapack = {
        "displayedServerList": [3, 0],
        "gachaId": gacha_id,
        "useEasyBG": bangdream_config["useEasyBG"],
        "compress": bangdream_config["compress"]
    }
    message_chain = call_tsugu(mode, datapack)
    feedback(message, message_chain)
#卡池模拟
def self_gacha_simulate(bot, message, raw_message):
    server = raw_message[-2:].strip()
    try:
        serverSet = {"jp":0, "en":1, "tw":2, "cn":3, "kr":4}
        server = serverSet[server]
        raw_message = raw_message[:-2].strip()
    except: server = 3
    parameters = raw_message.split(" ")
    [time, id] = [None, None]
    if len(parameters) >= 2:
        [time, id] = parameters
    elif len(parameters) == 1 and parameters[0] != "":
        time = parameters[0]
    try:
        if not time.isdigit():
            id = None
            time = None
        elif not id.isdigit(): id = None
    except: pass
    mode = "gachaSimulate"
    bangdream_config = load_config()
    if id != None:
        datapack = {
            "mainServer": server,
            "times": time,
            "compress": bangdream_config["compress"],
            "gachaId": id
        }
    elif time != None:
        datapack = {
            "mainServer": server,
            "times": time,
            "compress": bangdream_config["compress"],
        }
    else:
        datapack = {
            "mainServer": server,
            "compress": bangdream_config["compress"],
        }
    message_chain = call_tsugu(mode, datapack)
    feedback(message, message_chain)
#查角色
def self_sreach_character(bot, message, characterID):
    bangdream_config = load_config()
    if characterID.isdigit():
        datapack = {
            "displayedServerList": [3,0],
            "text": characterID,
            "compress": bangdream_config["compress"]
        }
    else:
        uri = f"{bangdream_config[bangdream_config['use_uri']]}/fuzzySearch"
        datapack = {"text": characterID}
        result = call_net(uri, mode="post", data_pack=datapack)
        if result == {}:
            message_chain = "\n[TSUGU]茨菇连接失败"
            feedback(message, message_chain)
            return
        if result["status"] == "success":
            datapack = {
                "displayedServerList": [3,0],
                "fuzzySearchResult": result["data"],
                "compress": bangdream_config["compress"]
            }
        else:
            message_chain = "\n[TSUGU]茨菇查询失败"
            feedback(message, message_chain)
            return
    mode = "searchCharacter"
    message_chain = call_tsugu(mode, datapack)
    feedback(message, message_chain)

def send_gif(bot, message, gif_path, file_name):
    if "group" in message.event_type:
        result = bot.inface.send_to_server(action="upload_group_file", body={
            "group_id": message.raw_data.get("group_id"),
            "file": gif_path,
            "name": file_name
        })
        log(result.raw_data)
    elif "private" in message.event_type:
        result = bot.inface.send_to_server(action="upload_private_file", body={
            "user_id": message.raw_data.get("user_id"),
            "file": gif_path,
            "name": file_name
        })
        log(result.raw_data)
