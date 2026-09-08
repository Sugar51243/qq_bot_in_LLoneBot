
# == PJSK插件入口 ==

# 由v1(src/plugin/pjsk/main.py)迁移至v2插件格式
# 本文件负责指令路由，曲库读取位于songs.py

import os, requests
from OneBotConnecter.types import MessageChain, ImageMessage
from OneBotConnecter.loger.log_info import log
from src.project_locator.project_locator import get_project_location
from src.plugins.pjsk.songs import get_song_list, song_id
from src.tools.reply_message import feedback

# == 入口 ==

def on_all_case(bot, message) -> bool: #call case including message, poke, request ...
    if "message" in message.event_type:
        return on_msg(bot, message=message)
    return False

def on_msg(bot, message) -> bool: # message
    raw_message = message.text
    if not raw_message: return False
    #与tsugu的查谱/查曲差异化: 需携带pjsk/烤前缀
    if raw_message[:4].lower() == "pjsk":
        raw_message = raw_message[4:]
    elif raw_message[:1] == "烤":
        raw_message = raw_message[1:]
    else:
        return False
    if raw_message[0:2] == "查谱":
        parameter = raw_message.replace("查谱面", "查谱")
        parameter = parameter[2:].strip()
        if len(parameter) <= 0:
            log(f"[PJSK]查谱: 空参数")
            send_message = MessageChain(["\n[PJSK]查询pjsk官方谱面图片"])
            send_message.add("\n可用参数:")
            send_message.add("\n-------------------------")
            send_message.add("\n[(ID/歌名) 难度]")
            send_message.add("\n例:1 sp")
            feedback(message, send_message)
            return True
        sreachChart(message, parameter)
        return True
    if raw_message[0:2] == "查曲":
        parameter = raw_message[2:].strip()
        if len(parameter) <= 0:
            log(f"[PJSK]查曲: 空参数")
            send_message = MessageChain(["\n[PJSK]查询pjsk官方歌曲信息"])
            send_message.add("\n可用参数:")
            send_message.add("\n-------------------------")
            send_message.add("\nID/歌名")
            send_message.add("\n例:1 sp")
            feedback(message, send_message)
            return True
        sreachSong(message, parameter)
        return True
    return False

def sreachChart(message, parameter):
    log(f"pjsk查谱: {parameter}")
    parameters = parameter.split(" ")
    if not parameters: return
    difficulty = parameters[-1].lower()
    difficultys = ["easy", "normal", "hard", "expert", "master"]
    difficultyKeySet = {"ez":"easy", "nm":"normal", "hd":"hard", "ex":"expert", "sp":"master"}
    d = "expert"
    if difficulty in difficultys:
        d = difficulty
        parameters = parameters[:-1]
    elif difficultyKeySet.get(difficulty, None) != None:
        d = difficultyKeySet.get(difficulty, None)
        parameters = parameters[:-1]
    id = song_id(parameters)
    log(f"id: {id}")
    if not id:
        feedback(message, MessageChain([f"id识别失败"]))
        return
    id = str(id[0]).zfill(4)
    log(f"pjsk查谱: ID[{id}] 难度[{d}]")
    file_name = os.path.join(get_project_location(), "data", "plugin", "pjsk", "temp", f"{id}_{d}.png")
    if not os.path.isfile(file_name):
        url = f"https://storage.sekai.best/sekai-music-charts/jp/{id}/{d}.png"
        result = requests.get(url, timeout=10)
        if result.status_code != 200:
            feedback(message, MessageChain(["\n[PJSK]连接失败"]))
            return
        os.makedirs(os.path.dirname(file_name), exist_ok=True)
        with open(file_name, "wb") as file:
            file.write(result.content)
    send = MessageChain([f"\n[PJSK]ID: {id} [{d}]"])
    send.add(ImageMessage(file_name))
    feedback(message, send)

def sreachSong(message, parameter):
    log(f"pjsk查曲: {parameter}")
    parameters = parameter.split(" ")
    ids = song_id(parameter=parameters)
    if not ids:
        feedback(message, MessageChain([f"id识别失败"]))
        return
    song_map = {str(song.get("id")): song for song in get_song_list()}
    send = MessageChain([f"\n[PJSK]小生物查询结果为({len(ids)}):"])
    if len(ids) <= 0:
        send.add("\n无")
    for id in ids:
        song = song_map.get(str(id), {})
        title = song.get("title", "未知")
        send.add(f"\n{id}. {title}")
    feedback(message, send)
