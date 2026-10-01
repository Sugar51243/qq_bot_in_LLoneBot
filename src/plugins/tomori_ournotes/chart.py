
# == Tomori OurNotes谱面模块 ==

# 查谱(Our Notes风格谱面预览图) / 谱面数据(谱面JSON文本)

import re
from OneBotConnecter.types import MessageChain
from OneBotConnecter.loger.log_info import log
from src.plugins.tomori_ournotes.config import load_config
from src.plugins.tomori_ournotes.call_ournotes import call_ournotes, call_net, call_fuzzy_search, parse_server, servers_display, server_display, server_hint, DEFAULT_SERVERS
from src.plugins.tomori_ournotes.reply import feedback

DIFFICULTY_KEY_SET = {"ez":0, "easy":0, "nm":1, "normal":1, "hd":2, "hard":2, "ex":3, "expert":3}
DIFFICULTY_NAME_LIST = ["EASY", "NORMAL", "HARD", "EXPERT"]

#解析难度/镜像/流速/服务器参数(逐词分类, 与顺序无关)
def parse_parameters(parameter: str):
    """返回(剩余参数列表, difficulty, mirror, noteSpeed, servers)"""
    difficulty = 3
    mirror = False
    note_speed = None
    servers = []
    rest = []
    for p in [p for p in parameter.split(" ") if p != ""]:
        low = p.lower()
        #镜像
        if low in ["mirror", "镜像"]:
            mirror = True
        #难度
        elif low in DIFFICULTY_KEY_SET:
            difficulty = DIFFICULTY_KEY_SET[low]
        #流速(速度X/流速X/speedX, 1.00-12.00)
        else:
            m = re.fullmatch(r"(速度|流速|speed)(\d+(?:\.\d+)?)", p, re.IGNORECASE)
            if m:
                note_speed = float(m.group(2))
            else:
                #服务器(四区域短码或中文别名)
                server = parse_server(p)
                if server:
                    if server not in servers:
                        servers.append(server)
                else:
                    rest.append(p)
    if not servers:
        servers = list(DEFAULT_SERVERS)
    return rest, difficulty, mirror, note_speed, servers

#查谱
def sreach_chart(bot, message, parameter):
    log(f"[TOMORI]查谱: {parameter}")
    if not parameter:
        send_message = MessageChain(["\n[TOMORI]查询Our Notes风格谱面预览图(24轨/滑条/fever)"])
        send_message.add("\n可用参数:")
        send_message.add("\n-------------------------")
        send_message.add("\n[(歌名/关键词/ID) 难度]")
        send_message.add("\n难度: ez/nm/hd/ex (默认ex)")
        send_message.add("\n例: tomori查谱 迷星叫 ex")
        send_message.add("\n可选: 镜像 / 速度7.5 / 服务器(默认港澳台服)")
        send_message.add(f"\n服务器: {server_hint()}\n")
        feedback(message, send_message)
        return
    parameters, difficulty, mirror, note_speed, servers = parse_parameters(parameter)
    #数字ID
    if len(parameters) == 1 and parameters[0].isdigit():
        get_chart_image(bot, message, parameters[0], difficulty, mirror, note_speed, servers)
        return
    #歌名/关键词: fuzzySearch→songId
    if len(parameters) <= 0:
        feedback(message, MessageChain(["\n[TOMORI]未检测到歌名或ID"]))
        return
    text = " ".join(parameters)
    result = call_fuzzy_search(text, servers)
    if result == {} or result.get("status") != "success":
        feedback(message, MessageChain(["\n[TOMORI]OurNotes后端连接失败"]))
        return
    song_ids = result.get("data", {}).get("songId", [])
    if len(song_ids) == 1:
        get_chart_image(bot, message, str(song_ids[0]), difficulty, mirror, note_speed, servers)
        return
    #多结果或无songId(整体同名规则下乐团名/等级等条件只返回bandId/songLevels等分类键):
    # 交由后端searchSong按fuzzy结果出列表图, 让用户用ID查谱
    song_keys = {"songId", "bandId", "songLevels", "_number", "_relationStr", "_all"}
    if any(k in result.get("data", {}) for k in song_keys):
        config = load_config()
        datapack = {
            "displayedServerList": servers,
            "fuzzySearchResult": result["data"],
            "compress": config["compress"]
        }
        send_message = MessageChain(["\n[TOMORI]搜索结果如下, 请用ID查谱:"])
        send_message.add(call_ournotes("searchSong", datapack))
        feedback(message, send_message)
        return
    feedback(message, MessageChain(["\n[TOMORI]没有搜索到符合条件的歌曲"]))

#谱面预览图 - /songChart(单服, 取服务器列表首个)
def get_chart_image(bot, message, song_id, difficulty, mirror, note_speed, servers):
    config = load_config()
    datapack = {
        "displayedServerList": servers,
        "songId": int(song_id),
        "difficultyId": difficulty,
        "compress": config["compress"],
        "mirror": mirror
    }
    if note_speed != None:
        datapack["noteSpeed"] = note_speed
    send_message = MessageChain([f"\n[TOMORI]ID: {song_id} ({DIFFICULTY_NAME_LIST[difficulty]}) [{server_display(servers[0])}]"])
    send_message.add(call_ournotes("songChart", datapack))
    feedback(message, send_message)

#谱面数据 - /songChartData
def get_chart_data(bot, message, parameter):
    log(f"[TOMORI]谱面数据: {parameter}")
    if not parameter:
        send_message = MessageChain(["\n[TOMORI]查询Our Notes谱面数据(等级/物量/BPM/fever)"])
        send_message.add("\n可用参数:")
        send_message.add("\n-------------------------")
        send_message.add("\n[ID (难度) (镜像) (服务器)]")
        send_message.add("\n难度: ez/nm/hd/ex (默认ex)")
        send_message.add(f"\n服务器: {server_hint()}\n")
        send_message.add("\n例: 谱面数据 100001 hd jp\n")
        feedback(message, send_message)
        return
    parameters, difficulty, mirror, _, servers = parse_parameters(parameter)
    if len(parameters) <= 0 or not parameters[0].isdigit():
        feedback(message, MessageChain(["\n[TOMORI]请提供数字歌曲ID, 例: 谱面数据 100001 hd"]))
        return
    config = load_config()
    result = call_net(f"{config['ournotes_uri']}/songChartData", mode="post", data_pack={
        "displayedServerList": servers,
        "songId": int(parameters[0]),
        "difficultyId": difficulty,
        "mirror": mirror,
        "format": "simple"
    })
    if result == {}:
        feedback(message, MessageChain(["\n[TOMORI]OurNotes后端连接失败"]))
        return
    if result.get("status") != "success":
        feedback(message, MessageChain([f"\n[TOMORI]{result.get('data', '查询失败')}"]))
        return
    data = result["data"]
    meta = data.get("meta", {}) or {}
    duration = int(meta.get("durationMs", 0)) // 1000
    counts = meta.get("counts", {}) or {}
    send_message = MessageChain(["\n[TOMORI]谱面数据"])
    send_message.add(f"\n{meta.get('title', '')} (ID: {meta.get('musicId', '')}) [{server_display(servers[0])}]")
    send_message.add(f"\n{meta.get('difficulty', '')} / 等级: {meta.get('level', '')} / 轨道: {meta.get('laneCount', '')}")
    send_message.add(f"\n时长: {duration//60:02d}:{duration%60:02d}")
    bpm = meta.get("bpm", {}) or {}
    if isinstance(bpm, dict):
        bpm_text = bpm.get("value", "-")
    else:
        #meta.bpm为段列表: [{bpm, timeStartMs, timeEndMs}, ...]
        values = [seg.get("bpm") for seg in bpm if isinstance(seg, dict) and seg.get("bpm") is not None]
        if not values:
            bpm_text = "-"
        elif len(set(values)) == 1:
            bpm_text = values[0]
        else:
            bpm_text = f"{min(values)}-{max(values)}"
    send_message.add(f"\nBPM: {bpm_text}")
    count_text = " / ".join(f"{k}: {v}" for k, v in counts.items())
    send_message.add(f"\n物量: {count_text}")
    send_message.add(f"\nFever段: {meta.get('feverCount', 0)} / 滑条: {meta.get('slideCount', 0)}")
    if mirror:
        send_message.add("\n(镜像)")
    feedback(message, send_message)
