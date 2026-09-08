
# == Tsugu谱面模块 ==

# 查谱/查官谱/查自制谱/随机谱面/查曲/新增搜索词

import os, re, requests, traceback
from OneBotConnecter.types import MessageChain, ImageMessage
from OneBotConnecter.loger.log_info import log
from src.project_locator.project_locator import get_project_location
from src.db_handler.plugin_db import dumps, loads
from src.plugins.tsugu_plugin.config import load_config
from src.plugins.tsugu_plugin.db import db
from src.plugins.tsugu_plugin.call_tsugu import call_tsugu, call_net
from src.tools.reply_message import feedback

#查谱
def sreachChart(bot, message, parameter):
    log(f"查谱: {parameter}")
    try:
        log(f"尝试搜索自制谱")
        charID = parameter
        if not charID.isdigit(): raise Exception()
        url = "https://bestdori.com/api/post/details?id=" + charID
        data = call_net(url)
        if data == {}:
            send = MessageChain(["\n小生物网络连接出现问题,请等下再试"])
            feedback(message, send)
            log(f"网络连接出现问题")
            return
        log(f"Bestdori接口回复: {data}")
        chartDetail = data["post"]
        sonolus_chart(bot, message, chartDetail, charID)
        return
    except Exception as e:
        log(f"尝试搜索官谱")
        parameters = parameter.split(" ")
        difficulty = parameters[-1].lower()
        difficultyKeySet = {"ez":0, "nm":1, "hd":2, "ex":3, "sp":4, "easy":0, "normal":1, "hard":2, "expert":3, "special":4}
        try:
            difficulty = difficultyKeySet[difficulty]
            parameters = parameters[:-1]
        except: difficulty = 3
        offical_chart(bot, message, parameters, difficulty)
        return
#自制
def sonolus_chart(bot, message, chartData, charID):
    log(f"开始解包谱面资料")
    name = chartData["title"]
    log(f"谱面名称: {name}")
    id = charID
    log(f"谱面ID: {id}")
    difficult = ["EASY", "NORMAL", "HARD", "EXPERT", "SPECIAL"]
    difficult = difficult[chartData["diff"]]
    log(f"谱面难度: {difficult}")
    level = chartData["level"]
    log(f"谱面等级: {level}")
    bpm = [-1,-1]
    n=0
    for nodes in chartData["chart"]:
        #计算BPM
        if nodes["type"] == "BPM":
            if bpm[0] == -1 or nodes["bpm"]<bpm[0]:
                bpm[0] = nodes["bpm"]
            if bpm[0] == -1 or nodes["bpm"]>bpm[1]:
                bpm[1] = nodes["bpm"]
        else:
            if nodes["type"] == "Slide":
                for node in nodes["connections"]:
                    try:
                        node["hidden"]
                    except: n+=1
            else:
                n+=1
    if bpm[0] == bpm[1]:
        bpm = f"{bpm[0]}"
    else:
        bpm = f"{bpm[0]}-{bpm[1]}"
    log(f"谱面BPM: {bpm}")
    count = n
    log(f"谱面物量: {count}")
    if chartData["song"]["type"] == "bandori":
        try:
            charID = chartData["song"]["id"]
            song_url = "https://bestdori.com//api/songs/all.7.json"
            song_list = call_net(song_url)
            duration = song_list[str(charID)]["length"]
            time: str = f"{duration//60:02.0f}:{duration%60:02.2f}"
        except:
            time = "官谱曲目时长识别失败"
    elif chartData["song"]["type"] == "custom":
        path = f"{os.path.join(get_project_location(), load_config()['music_temp_path'])}/{charID}.mp3"
        try:
            import eyed3
            try:
                duration = eyed3.load(path).info.time_secs
            except:
                audio_url: str = chartData['song']['audio']
                response = requests.get(audio_url)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'wb') as f:
                    f.write(response.content)
                duration = eyed3.load(path).info.time_secs
            time: str = f"{duration//60:02.0f}:{duration%60:02.2f}"
        except:
            time = "自定义曲目时长识别失败"
    else:
        time = f"曲目类型识别失败:{chartData['song']['type']}"
    log(f"谱面时长: {time}")
    server = "Bestdori"
    log(f"服务器: {server}")
    owner = chartData["author"]["username"]
    log(f"谱师: {owner}")
    like = chartData["likes"]
    log(f"谱面点赞数: {like}")
    chart = chartData["chart"]
    log(f"开始构造信息链")
    message_chain = MessageChain(["\n", "[TSUGU]谱面信息\n", "--------------------\n"])
    message_chain.add(MessageChain([f"谱面名称:{name}\n"]))
    message_chain.add(MessageChain([f"谱面ID:{id}\n"]))
    message_chain.add(MessageChain([f"点赞数:{like}\n"]))
    message_chain.add(MessageChain(["--------------------\n"]))
    message_chain.add(MessageChain([f"谱面难度:{difficult}\n"]))
    message_chain.add(MessageChain([f"谱面等级:{level}\n"]))
    message_chain.add(MessageChain([f"谱师:{owner}\n"]))
    message_chain.add(MessageChain(["--------------------\n"]))
    message_chain.add(MessageChain([f"BPM:{bpm}\n"]))
    message_chain.add(MessageChain([f"物量:{count}\n"]))
    message_chain.add(MessageChain([f"时长:{time}\n"]))
    message_chain.add(MessageChain(["--------------------\n"]))
    message_chain.add(MessageChain([f"服务器:{server}\n"]))
    url = f"https://sonolus.bestdori.com/community/levels/bestdori-community-{id}"
    message_chain.add(MessageChain([f"前去游玩:{url}\n"]))
    message_chain.add(MessageChain(["--------------------\n"]))
    imageURL = renderingChart(bot, charData=chart, charID=id, server=server, difficult=difficult)
    if imageURL == None: message_chain.add("渲染失败")
    else: message_chain.add(MessageChain([ImageMessage(imageURL)]))
    try:
        feedback(message, message_chain)
    except Exception as e:
        tb = e.__traceback__
        formatted_tb = ''.join(traceback.format_tb(tb))
        log(f"[{type(e)}] {e}\n{formatted_tb}")
#谱面渲染至图片 - bestdori-render
def renderingChart(bot, charData: list, charID, server: str, difficult = "expert"):
    try:
        #渲染
        log(f"开始渲染")
        from bestdori.render import render
        image = render(charData)
        log(f"渲染成功")
        if server == "Bandori":
            imageURL: str = f"{os.path.join(get_project_location(), 'data', 'plugin', 'tsugu_plugin', 'char')}/{charID}-{difficult}.png"
        else:
            imageURL: str = f"{os.path.join(get_project_location(), 'data', 'plugin', 'tsugu_plugin', 'char')}/{charID}.png"
        os.makedirs(os.path.dirname(imageURL), exist_ok=True)
        image.save(imageURL)
        log(f"文件已储存至: {imageURL}")
        #返回文件地址
        return imageURL
    except Exception as e:
        log(f"渲染失败")
        tb = e.__traceback__
        formatted_tb = ''.join(traceback.format_tb(tb))
        log(f"[{type(e)}] {e}\n{formatted_tb}")
        return None
#官谱
def offical_chart(bot, message, parameters: list, difficulty: int):
    if not parameters or not parameters[0].isdigit():
        log(f"检测到参数并非数字ID")
        log(f"开始请求歌曲列表")
        song_url = "https://bestdori.com//api/songs/all.7.json"
        song_list = call_net(song_url)
        log(f"Bestdori接口回复: {song_list}")
        log(f"正在使用歌名模式搜索")
        result = sreachFromNameMode(song_list, parameters)
        log(f"搜索结果: {result}")
        log(f"正在叠加难度过滤")
        result = filterFromDifficulty(song_list, result, difficulty)
        log(f"搜索结果: {result}")
        #处理结果
        if len(result) <= 0:
            log(f"搜索失败，正在使用条件式搜索")
            result = sreachFromFilterMode(song_list, parameters)
            log(f"搜索结果: {result}")
            log(f"正在叠加难度过滤")
            result = filterFromDifficulty(song_list, result, difficulty)
            log(f"搜索结果: {result}")
        log(f"结果总计: {len(result)}首")
        if len(result) == 1:
            log(f"将向茨菇查询谱面图片")
            charID = result[0]
            get_offical_chart_image(bot, message, charID, difficulty)
        else:
            log(f"将返回谱面列表")
            message_chain = MessageChain([f"\n[TSUGU]小生物查询结果为({len(result)}):"])
            if len(result) <= 0:
                message_chain.add(MessageChain(["\n无"]))
            for songID in result:
                serverid = 0
                while song_list[songID]['musicTitle'][serverid] == None:
                    serverid += 1
                message_chain.add(MessageChain([f"\n{songID}. {song_list[songID]['musicTitle'][serverid]}"]))
            feedback(message, message_chain)
        return
    #茨菇查谱
    log(f"将向茨菇查询谱面图片")
    get_offical_chart_image(bot, message, parameters[0], difficulty)
    return
#谱面渲染至图片 - tsugu
def get_offical_chart_image(bot, message, charID, difficulty):
    mode = "songChart"
    bangdream_config = load_config()
    datapack = {
        "displayedServerList": [3,0],
        "songId": charID,
        "difficultyId": difficulty,
        "compress": bangdream_config["compress"]
    }
    send_message = MessageChain([f"\nID: {charID}"])
    send_message.add(call_tsugu(mode, datapack))
    feedback(message, send_message)
#歌名模式搜索
def sreachFromNameMode(song_list, parameters: list):
    result = []
    log(f"进入歌名搜索")
    log(f"进行首轮过滤")
    for id in song_list:
        for name in song_list[id]['musicTitle']:
            if name == None:
                continue
            if parameters[0].lower() in name.lower() and id not in result:
                result.append(id)
                break
    log(f"过滤结果: {result}")
    log(f"进行第二轮过滤: {result}")
    for parameter in parameters:
        temp = []
        for id in result:
            for name in song_list[id]['musicTitle']:
                if name == None:
                    continue
                if parameter.lower() in name.lower() and id not in temp:
                    temp.append(id)
        result = temp
    log(f"过滤结果: {result}")
    if len(result) == 1: return result
    log(f"进入关键词搜索")
    log(f"读入关键词本")
    sreachKey = {}
    for keyword, ids_text in db.query("SELECT keyword, song_ids FROM key_set;"):
        sreachKey[keyword] = loads(ids_text) or []
    log(f"进行过滤")
    for key in sreachKey:
        for keyword in parameters:
            if keyword.lower() in key.lower():
                for song_id in sreachKey[key]:
                    if song_id not in result:
                        result.append(song_id)
    log(f"过滤结果: {result}")
    return list(set(result))
#条件式搜索
def sreachFromFilterMode(song_list, parameters: list):
    filters = list(parameters)
    filterResult = []
    log(f"正在填装歌曲ID")
    for id in song_list:
        filterResult.append(id)
    log(f"进入曲目种类搜索")
    log(f"进行首轮过滤")
    types = ["原创", "动画", "翻唱", "covers", "cover"]
    songType = list(set(filters) & set(types))
    if len(songType)>0:
        log(f"曲目种类搜索: {songType}")
        filters.remove(songType[0])
        filterResult = list(set(sreachByType(song_list, filterResult, songType[0])) & set(filterResult))
    log(f"过滤结果: {filterResult}")
    if len(filterResult) <= 1: return filterResult
    log(f"进入曲目等级搜索")
    log(f"进行第二轮过滤")
    for parameter in filters:
        if parameter[:2] == "lv" and parameter[2:].isdigit():
            level = int(parameter[2:])
            log(f"曲目等级搜索: {level}")
            filters.remove(parameter)
            filterResult = list(set(sreachByLevel(song_list, filterResult, level)) & set(filterResult))
            break
    log(f"过滤结果: {filterResult}")
    if len(filterResult) <= 1: return filterResult
    log(f"进入曲目物量搜索")
    log(f"进行第三轮过滤")
    for parameter in filters:
        if parameter[:2] == "物量":
            log(f"曲目物量搜索: {parameter[2:]}")
            if "-" in parameter[2:]:
                notesRange = parameter[2:].split("-")
                if len(notesRange)>=2:
                    if notesRange[0].isdigit() and notesRange[1].isdigit():
                        notes1 = int(notesRange[0])
                        notes2 = int(notesRange[1])
                        filters.remove(parameter)
                        filterResult = list(set(sreachByNotes(song_list, filterResult, notes1, notes2)) & set(filterResult))
                        break
                elif len(notesRange)==1:
                    if notesRange[0].isdigit():
                        notes1 = 0
                        notes2 = int(notesRange[0])
                        filters.remove(parameter)
                        filterResult = list(set(sreachByNotes(song_list, filterResult, notes1, notes2)) & set(filterResult))
                        break
            elif "+" in parameter[2:]:
                notesRange = parameter[2:].split("+")
                if notesRange[0].isdigit() and len(notesRange) == 1:
                    notes1 = int(notesRange[0])
                    notes2 = 2147483647
                    filters.remove(parameter)
                    filterResult = list(set(sreachByNotes(song_list, filterResult, notes1, notes2)) & set(filterResult))
                    break
            elif parameter[2:].isdigit():
                notes = int(parameter[2:])
                filters.remove(parameter)
                filterResult = list(set(sreachByNotes(song_list, filterResult, notes)) & set(filterResult))
                break
    log(f"过滤结果: {filterResult}")
    if len(filterResult) <= 1: return filterResult
    log(f"进入曲目BPM搜索")
    log(f"进行第四轮过滤")
    for parameter in filters:
        if parameter[:3].lower() == "bpm":
            log(f"曲目BPM搜索: {parameter[3:]}")
            if "-" in parameter[3:]:
                bpmRange = parameter[3:].split("-")
                if len(bpmRange) >= 2:
                    if bpmRange[0].isdigit() and bpmRange[1].isdigit():
                        bpm1 = int(bpmRange[0])
                        bpm2 = int(bpmRange[1])
                        filters.remove(parameter)
                        filterResult = list(set(sreachByBPM(song_list, filterResult, bpm1, bpm2)) & set(filterResult))
                        break
                elif len(bpmRange) == 1:
                    if bpmRange[0].isdigit():
                        bpm1 = 0
                        bpm2 = int(bpmRange[0])
                        filters.remove(parameter)
                        filterResult = list(set(sreachByBPM(song_list, filterResult, bpm1, bpm2)) & set(filterResult))
                        break
            elif "+" in parameter[3:]:
                bpmRange = parameter[3:].split("+")
                if bpmRange[0].isdigit() and len(bpmRange) == 1:
                    bpm1 = int(bpmRange[0])
                    bpm2 = 2147483647
                    filters.remove(parameter)
                    filterResult = list(set(sreachByBPM(song_list, filterResult, bpm1, bpm2)) & set(filterResult))
                    break
            elif parameter[3:].isdigit():
                bpm = int(parameter[3:])
                filters.remove(parameter)
                filterResult = list(set(sreachByBPM(song_list, filterResult, bpm)) & set(filterResult))
                break
    log(f"过滤结果: {filterResult}")
    if len(filterResult) <= 1: return filterResult
    log(f"进入曲目乐团名称搜索")
    log(f"进行第五轮过滤")
    if len(filters) > 0:
        log(f"乐团名称搜索: {' '.join(filters)}")
        filterResult = list(set(sreachByBand(song_list, filterResult, " ".join(filters))) & set(filterResult))
    log(f"过滤结果: {filterResult}")
    return filterResult
#难度过滤
def filterFromDifficulty(song_list, id_list, difficulty):
    result = []
    if len(id_list)<=0:
        return result
    for id in id_list:
        song = song_list[id]
        if str(difficulty) in song["difficulty"]:
            result.append(id)
        else:
            continue
    return result
#条件式搜索 - 曲目种类
def sreachByType(songList, filterResult, songType: str):
    result = [] #暂存ID列表
    #模糊关键词
    if songType == "原创": songType = "normal"
    elif songType == "动画": songType = "anime"
    elif songType == "翻唱": songType = "tie_up"
    elif songType == "cover": songType = "tie_up"
    elif songType == "covers": songType = "tie_up"
    #筛选
    result = [key for key in filterResult if songList[key]["tag"] == songType]
    return result
#条件式搜索 - 曲目等级
def sreachByLevel(songList, filterResult, level):
    result = [] #暂存ID列表
    level = int(level)
    #筛选
    for key in filterResult:
        song = songList[key]
        #比对各种难度
        for difficulty in song['difficulty']:
            levelData = song['difficulty'][difficulty]
            if levelData["playLevel"] == level:
                result.append(key)
                break
    return result
#条件式搜索 - 乐团名称
#支持模糊搜索
def sreachByBand(songList, filterResult, band: str):
    result = [] #暂存ID列表
    #模糊关键词
    if band.lower() in ["ppp", "Poppin'Party"]:
        band = "Poppin'Party"
    elif band.lower() in ["ag", "afterglow"]:
        band = "Afterglow"
    elif band.lower() in ["hhw", "ハロー、ハッピーワールド！"]:
        band = "ハロー、ハッピーワールド！"
    elif band.lower() in ["pp", "p*p", "Pastel＊Palettes"]:
        band = "Pastel＊Palettes"
    elif band.lower() in ["萝", "rose", "r", "roselia"]:
        band = "Roselia"
    elif band.lower() in ["蝶", "morfonica"]:
        band = "Morfonica"
    elif band.lower() in ["母鸡卡", "ave mujica"]:
        band = "Ave Mujica"
    elif band.lower() in ["梦结", "夢ノ結唱"]:
        band = "夢ノ結唱"
    elif band.lower() in ["ras", "raise a suilen"]:
        band = "RAISE A SUILEN"
    #请求必须信息
    band_url = "https://bestdori.com/api/bands/all.1.json"
    band_name_list = call_net(band_url)
    #模糊匹配乐团信息，返回可能参数 (Band ID)
    for id in filterResult:
        for name in band_name_list[str(songList[id]["bandId"])]["bandName"]:
            if name != None:
                if band.lower() in name.lower() and id not in result:
                    result.append(id)
    return result
#条件式搜索 - 物量
def sreachByNotes(songList, filterResult, notes1, notes2 = None):
    result = [] #暂存ID列表
    notes1 = int(notes1)
    if notes2 != None:
        notes2 = int(notes2)
    #筛选
    for key in filterResult:
        song = songList[key]
        #比对各种难度
        for difficulty in song['difficulty']:
            levelData = song['notes'][difficulty]
            if notes2 != None:
                if int(levelData) >= int(notes1) and int(levelData) <= int(notes2):
                    result.append(key)
                    break
            elif int(levelData) == int(notes1):
                result.append(key)
                break
    return result
#条件式搜索 - BPM
def sreachByBPM(songList, filterResult, bpm1, bpm2 = None):
    result = [] #暂存ID列表
    bpm1 = int(bpm1)
    if bpm2 != None:
        bpm2 = int(bpm2)
    #筛选
    for key in filterResult:
        song = songList[key]
        #比对各种难度
        for difficulty in song['difficulty']:
            levelData = song['bpm'][difficulty]
            bpm = int(levelData[0]["bpm"])
            if bpm2 != None:
                if (bpm >= bpm1 and bpm <= bpm2):
                    result.append(key)
                    break
            elif bpm == bpm1:
                result.append(key)
                break
    return result
#随机查谱
def randomSreachChart(bot, message):
    song_url = "https://bestdori.com//api/songs/all.7.json"
    song_list = call_net(song_url)
    if song_list == {}:
        feedback(message, MessageChain(["\n[TSUGU]服务器网络连接出错"]))
        return
    id_set = list(song_list.keys())
    idx = random.randint(0, len(id_set)-1)
    song = song_list[id_set[idx]]
    difficulty_set = list(song["difficulty"].keys())
    idx = random.randint(0, len(difficulty_set)-1)
    difficulty = difficulty_set[idx]
    offical_chart(bot, message, [str(id_set[idx])], int(difficulty))
    return
#新增搜索词
def add_key_word_for_song(bot, message, raw_message):
    command = raw_message[5:].strip()
    try:
        id = re.findall(r'(\d+)', command)[0]
    except:
        feedback(message, MessageChain([" [TSUGU]未检测到谱面ID"]))
        return
    command = command.replace(id,"").strip()
    command = command.replace("，",",")
    sreachKey = []
    keySet = command.split(",")
    for key in keySet:
        sreachKey.append(key.strip())
    id = str(id)
    keySet = sreachKey
    #更新
    saved_keys = []
    for key in keySet:
        if not key: continue
        saved_keys.append(key)
        row = db.query_one("SELECT song_ids FROM key_set WHERE keyword = ?;", (key,))
        if row:
            ids = loads(row[0]) or []
            if id not in ids:
                ids.append(id)
                db.execute("UPDATE key_set SET song_ids = ? WHERE keyword = ?;", (dumps(ids), key))
            else: saved_keys.remove(key)
        else:
            db.execute("INSERT OR IGNORE INTO key_set (keyword, song_ids) VALUES (?, ?);", (key, dumps([id])))
    message_chain = MessageChain([f" [TSUGU]已为谱面ID [{id}] 新增关键词 {saved_keys} "])
    feedback(message, message_chain)
#茨菇查曲
def returnSongInfo(bot, message, charID: str):
    bangdream_config = load_config()
    if charID.isdigit():
        datapack = {
            "displayedServerList": [3,0],
            "text": charID,
            "useEasyBG": bangdream_config["useEasyBG"],
            "compress": bangdream_config["compress"]
        }
    else:
        uri = f"{bangdream_config[bangdream_config['use_uri']]}/fuzzySearch"
        datapack = {"text": charID}
        result = call_net(uri, mode="post", data_pack=datapack)
        if result == {}:
            message_chain = "\n[TSUGU]茨菇连接失败"
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
            message_chain = "\n[TSUGU]茨菇查询失败"
            feedback(message, message_chain)
            return
    mode = "searchSong"
    message_chain = call_tsugu(mode, datapack)
    feedback(message, message_chain)
