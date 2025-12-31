import os
from io import BytesIO
import numpy as np
try:
    from OneBotConnecter.MessageType import MessageChain, ImageMessage, RecordMessage
except:
    os.system("pip install OneBotConnecter")
    exec("from OneBotConnecter.MessageType import MessageChain, ImageMessage, RecordMessage")
try:
    from tsugu_api import cutoff_detail, cutoff_all, cutoff_list_of_recent_event
    from tsugu_api import search_song, song_chart, song_meta
    from tsugu_api import search_card, search_player, search_character
    from tsugu_api import event_stage, search_event
    from tsugu_api import search_gacha, gacha_simulate
    from tsugu_api import room_list, query_room_number, submit_room_number, station_query_all_room
except:
    os.system("pip install tsugu-api-python")
    exec("from tsugu_api import cutoff_detail, cutoff_all, cutoff_list_of_recent_event")
    exec("from tsugu_api import search_song, song_chart, song_meta")
    exec("from tsugu_api import search_card, search_player, search_character")
    exec("from tsugu_api import event_stage, search_event")
    exec("from tsugu_api import search_gacha, gacha_simulate")
    exec("from tsugu_api import room_list, query_room_number, submit_room_number, station_query_all_room")
try: from bestdori.render import render
except:
    os.system("pip install bestdori-render")
    exec("from bestdori.render import render")
lib_list = ["requests", "json", "traceback", "eyed3", "base64", "random", "re", "io"]
for lib in lib_list:
    try:
        exec(f"import {lib}")
    except:
        os.system(f"pip install {lib}")
        exec(f"import {lib}")
try: from PIL import Image, ImageDraw
except:
    os.system("pip install pillow")
    exec("from PIL import Image, ImageDraw")
try: from config_io import Config
except:
    os.system("pip install config-io")
    exec("from config_io import Config")

guess_list = {}

async def bangdreamMode(bot, msg, raw_message, be_at):
    if str(msg["group_id"]) in guess_list:
        await answer_guess_chart(bot, msg, raw_message, be_at)
    # 查谱
    if raw_message[0:2] == "查谱":
        await sreachChart(bot, msg, raw_message, be_at)
        return
    # 自制查谱
    if raw_message[0:4] == "查自制谱":
        if raw_message[0:5] == "查自制谱面":
            command = raw_message[5:].strip()
        else:
            command = raw_message[4:].strip()
        try:
            charID = command
            if not charID.isdigit(): raise Exception()
            url = "https://bestdori.com/api/post/details?id=" + charID
            data = requestData(url)
            chartDetail = data["post"]
            await sreachSelfMakeChart(bot, msg, chartDetail, charID)
            return
        except Exception as e:
            message = MessageChain([" 自制谱面ID参数错误 "])
            await bot.reply_to_message(msg, message)
            return
        await sreachChart(bot, msg, command, be_at)
        return
    # 官谱查谱
    if raw_message[0:3] == "查官谱":
        if raw_message[0:4] == "查官谱面":
            command = raw_message[4:].strip()
        else:
            command = raw_message[3:].strip()
        parameters = command.split(" ")
        difficulty = parameters[-1]
        difficultyKeySet = {"ez":0, "nm":1, "hd":2, "ex":3, "sp":4}
        try: 
            difficulty = difficultyKeySet[difficulty]
            parameters = parameters[:-1]
        except: difficulty = 3
        await sreachOfficalMakeChart(bot, msg, parameters, difficulty)
        return
    # 随机查谱
    if raw_message == "随机查谱":
        await randomSreachChart(bot, msg)
        return
    # 查曲
    if raw_message[0:2] == "查曲":
        await returnSongInfo(bot, msg, raw_message[2:].strip())
        return
    # 新增搜索词
    if raw_message[:5] == "新增搜索词":
        await add_key_word_for_song(bot, msg, raw_message, be_at)
        return
    # 查卡池 - search_gacha - serverlist, id
    if raw_message[0:3] == "查卡池":
        raw_message = raw_message[3:].strip()
        if len(raw_message) <= 0 or not raw_message.isdigit():
            message = MessageChain(["\n参数缺失,可用参数:\n", "-------------------------\n", "[卡池ID]\n", "例:查卡池 1\n", "-------------------------\n"])
            await bot.reply_to_message(msg, message)
            return
        if raw_message.isdigit():
            await self_search_gacha(bot, msg, raw_message, be_at)
            return
    # 查卡947
    if '查卡' in raw_message and "947" in raw_message:
        if (str(msg["sender"]["user_id"]) not in bot.owner) or (random.randint(1,100) > (50)):
            message = MessageChain([" 不许查!!!"])
            await bot.reply_to_message(msg, message)
            return
    # 查卡面
    if raw_message[0:3] == "查卡面":
        cardID = raw_message[3:].strip()
        if cardID.isdigit() == True:
            url = f"https://bestdori.com/api/cards/{cardID}.json"
            data = requestData(url)
            message = MessageChain([ImageMessage(getImage(data,False))])
            try:
                message.add(ImageMessage(getImage(data,True)))
            except: pass
            await bot.reply_to_message(msg, message)
        return
    # 查卡
    if raw_message[0:2] == "查卡":
        cardID = raw_message[2:].strip()
        await sreachCard(bot, msg, cardID)
        return
    # 随机查卡
    if raw_message == "随机查卡":
        await randomSreachCard(bot, msg)
        return
    # 随机卡面
    if raw_message == "随机卡面":
        await randomGetCard(bot, msg)
        return
    # lsycx
    if raw_message[0:5].lower() == "lsycx":
        await lsycx(bot, msg, raw_message, be_at)
        return
    # ycxall
    if raw_message[0:6].lower() == "ycxall":
        await ycxall(bot, msg, raw_message, be_at)
        return
    # ycx
    if raw_message[0:3].lower() == "ycx" or raw_message.lower() == "k":
        await self_ycx(bot, msg, raw_message, be_at)
        return
    # 查角色
    if raw_message[0:2] == "查角色":
        characterID = raw_message[2:].strip()
        await self_sreach_character(bot, msg, characterID, be_at)
        return
    # 分数表
    if raw_message[0:3] == "分数表":
        server = raw_message[3:].strip()
        await self_song_meta(bot, msg, server, be_at)
        return
    # 卡池模拟
    if raw_message[0:4] == "卡池模拟":
        command = raw_message[4:].strip()
        await self_gacha_simulate(bot, msg, command, be_at)
    # 猜谱面
    if raw_message[0:3] == "猜谱面":
        num = 0
        if len(raw_message[3:].strip())>0:
            if raw_message[3:].strip().isdigit():
                if int(raw_message[3:].strip()) >0 and int(raw_message[3:].strip()) <= 5:
                    num = int(raw_message[3:].strip())
        await guess_chart(bot, msg, raw_message, be_at, num)
        return
    # ycm - query_room_number
    if raw_message.lower() == "ycm":
        await self_room_list(bot, msg, raw_message, be_at)
        return
    
    '''
    # 上传车牌 - submit_room_number - nmber, id, raw_message, source, token
    '''
    #查玩家
    if raw_message[0:3] == "查玩家":
        await check_player_info(bot, msg, raw_message, be_at)
        return
    # 绑定玩家
    if raw_message[0:4] == "绑定玩家":
        await bing_user(bot, msg, raw_message, be_at)
        return
    # 绑定记录
    if raw_message[0:4] == "绑定记录":
        await checkUserBinded(bot, msg)
        return
    # 删除绑定
    if raw_message[0:4] == "删除绑定":
        await delUserBinded(bot, msg, raw_message, be_at)
        return
    # 玩家状态
    if raw_message[0:4] == "玩家状态":
        raw_message = raw_message[4:].strip()
        id = 0
        if len(raw_message)>0:
            if raw_message.isdigit():
                if int(raw_message) > 0:
                    id = int(raw_message)-1
        await get_play_info(bot, msg, msg["sender"]["user_id"], id)
    # 逮捕
    if raw_message[0:2] == "逮捕":
        raw_message = raw_message[2:].strip()
        if "[CQ:at,qq=" in raw_message or "[CQ:reply,id=" in raw_message:
            idx = raw_message.find("qq=")+3
            raw_message = raw_message[idx:]
            targetID = re.findall(r'(\d+)', raw_message)
            await get_play_info(bot, msg, targetID[0], 0)
            return
        await bot.reply_to_message(bot, msg, MessageChain(["未发现参数"]))
        return
    # 查试炼
    if raw_message[0:3] == "查试炼":
        await self_event_stage(bot, msg, raw_message, be_at)
        return
    # 查活动
    if raw_message[0:3] == "查活动":
        await self_search_event(bot, msg, raw_message, be_at)
        return


#ycm
async def self_room_list(bot, msg, raw_message, be_at):
    try:
        data = station_query_all_room()
        data = data["data"]
        data = room_list(data)
        message = MessageChain(["\n"])
        message.add(ImageMessage(f"base64://{data[0]["string"]}"))
        await bot.reply_to_message(msg, message)
        return
    except Exception as e:
        message = MessageChain(["\n茨菇后台连接失败"])
        await bot.reply_to_message(msg, message)
        traceback.print_exc()
        return

#查茨菇
async def call_tsugu(bot, msg, callback):
    try:
        data = callback()
        try:
            if data[0]["type"] == "base64":
                message = MessageChain(["\n"])
                message.add(ImageMessage(f"base64://{data[0]["string"]}"))
                callback = await bot.reply_to_message(msg, message)
                return
            raise SyntaxError()
        except SyntaxError:
            message = MessageChain(["\n"])
            message.add(MessageChain([card[0]["string"]]))
            await bot.reply_to_message(msg, message)
            return
        except Exception:
            message = MessageChain(["\n"])
            message.add(MessageChain("茨菇返回数据处理出现问题"))
            await bot.reply_to_message(msg, message)
            traceback.print_exc()
            return
    except Exception as e:
        message = MessageChain(["\n"])
        message.add(MessageChain(["茨菇后台连接失败"]))
        await bot.reply_to_message(msg, message)
        traceback.print_exc()
        return

#查卡池
async def self_search_gacha(bot, msg, gacha_id, be_at):
    function = lambda: search_gacha([3, 0], gacha_id=gacha_id)
    await call_tsugu(bot, msg, callback = function)
#查角色
async def self_sreach_character(bot, msg, characterID, be_at):
    if characterID.isdigit() == True:
        function = lambda: search_character([3, 0], characterID)
    else:
        function = lambda: search_character([3, 0], text=characterID)
    await call_tsugu(bot, msg, callback = function)
#查询分数表
async def self_song_meta(bot, msg, server, be_at):
    try:
        serverSet = {"jp":0, "en":1, "tw":2, "cn":3, "kr":4}
        server = serverSet[server]
    except: server = 3
    function = lambda: song_meta([3, 0], server)
    await call_tsugu(bot, msg, callback = function)
#卡池模拟
async def self_gacha_simulate(bot, msg, raw_message, be_at):
    server = raw_message[-2:].strip()
    try:
        serverSet = {"jp":0, "en":1, "tw":2, "cn":3, "kr":4}
        server = serverSet[server]
        raw_message = raw_message[:-2].strip()
    except: server = 3
    parameters = raw_message.split(" ")
    if len(parameters) < 2:
        message = MessageChain(["\n参数缺失"])
        await bot.reply_to_message(msg, message)
        return
    [id, time] = parameters
    if id.isdigit() == False or time.isdigit() == False:
        message = MessageChain(["\n参数错误"])
        await bot.reply_to_message(msg, message)
        return
    function = lambda: gacha_simulate(server, time, id)
    await call_tsugu(bot, msg, callback = function)

#查谱
async def sreachChart(bot, msg, raw_message, be_at):
    if raw_message[0:3] == "查谱面":
        command = raw_message[3:].strip()
    else:
        command = raw_message[2:].strip()
    #无参警告
    if len(command) <= 0:
        message = MessageChain([
            "\n参数缺失,可用参数:\n",
            "-------------------------\n",
            "[歌名/关键词/ID 难度]\n",
            "例:六兆年 sp\n",
            "-------------------------\n",
            "[(等级/乐团名称/歌曲种类) 难度]\n",
            "例:萝 lv27 翻唱 hd\n",
            "-------------------------\n",
            "注意事项:\n",
            "1. 搜索将以歌名搜索优先\n",
            "2. 等级搜索请在前加上lv\n例: lv41\n",
            "3. 难度并非过滤器参数\n",
            "4. 此功能为搜谱，并非搜曲\n"
            ])
        await bot.reply_to_message(msg, message)
        return
    #自制
    try:
        charID = command
        if not charID.isdigit(): raise Exception()
        url = "https://bestdori.com/api/post/details?id=" + charID
        data = requestData(url)
        chartDetail = data["post"]
        await sreachSelfMakeChart(bot, msg, chartDetail, charID)
        return
    #官谱
    except Exception as e:
        parameters = command.split(" ")
        difficulty = parameters[-1]
        difficultyKeySet = {"ez":0, "nm":1, "hd":2, "ex":3, "sp":4}
        try: 
            difficulty = difficultyKeySet[difficulty]
            parameters = parameters[:-1]
        except: difficulty = 3
        await sreachOfficalMakeChart(bot, msg, parameters, difficulty)
        return
#自制
async def sreachSelfMakeChart(bot, msg, chartData, charID):
    #取出数据
    name = chartData["title"]
    id = charID
    #难度 & 等级
    difficult = chartData["diff"]
    if difficult == 0:
        difficult = "EASY"
    elif difficult == 1:
        difficult = "NORMAL"
    elif difficult == 2:
        difficult = "HARD"
    elif difficult == 3:
        difficult = "EXPERT"
    elif difficult == 4:
        difficult = "SPECIAL"
    level = chartData["level"]
    #物量 & BPM
    bpm = [-1,-1]
    n=0
    counted = False
    for nodes in chartData["chart"]:
        #计算BPM
        if nodes["type"] == "BPM":
            if bpm[0] == -1 or nodes["bpm"]<bpm[0]: 
                bpm[0] = nodes["bpm"]
            if bpm[0] == -1 or nodes["bpm"]>bpm[1]: 
                bpm[1] = nodes["bpm"]
        else:
            if nodes["type"] == "Slide":
                n+=len(nodes["connections"])
            else: n+=1
    if bpm[0] == bpm[1]:
        bpm = f"{bpm[0]}"
    else:
        bpm = f"{bpm[0]}-{bpm[1]}"
    count = n
    #时长
    if chartData["song"]["type"] == "bandori":
        try:
            charID = chartData["song"]["id"]
            song_url = "https://bestdori.com//api/songs/all.7.json"
            song_list = requestData(song_url)
            duration = song_list[str(charID)]["length"]
            time: str = f"{duration//60:02.0f}:{duration%60:02.2f}"
        except:
            time = "官谱曲目时长识别失败"
    elif chartData["song"]["type"] == "custom":
        path = f"data/classify/bangdream/song/{charID}.mp3"
        try:
            try:
                duration = eyed3.load(path).info.time_secs
            except:
                audio_url: str = chartData['song']['audio']
                response = requests.get(audio_url)
                with open(path, 'wb') as f:
                    f.write(response.content)
                duration = eyed3.load(path).info.time_secs
            time: str = f"{duration//60:02.0f}:{duration%60:02.2f}"
        except:
            time = "自定义曲目时长识别失败"
    else:
        time = f"曲目类型识别失败:{chartData["song"]["type"]}"
    server = "Bestdori"
    owner = chartData["author"]["username"]
    like = chartData["likes"]
    chart = chartData["chart"]
    #构造信息链
    message = MessageChain(["\n", "谱面信息\n", "--------------------\n"])
    #基础信息
    #谱面名称
    message.add(MessageChain([f"谱面名称:{name}\n"]))
    #谱面ID
    message.add(MessageChain([f"谱面ID:{id}\n"]))
    #点赞数
    message.add(MessageChain([f"点赞数:{like}\n"]))
    #一级信息 ( 谱面难度 | 谱面等级 | 所属乐团或谱师 )
    message.add(MessageChain(["--------------------\n"]))
    #谱面难度
    message.add(MessageChain([f"谱面难度:{difficult}\n"]))
    #谱面等级
    message.add(MessageChain([f"谱面等级:{level}\n"]))
    #所属乐团或谱师
    message.add(MessageChain([f"谱师:{owner}\n"]))
    #二级信息 ( BPM | 物量 | 时长 )
    message.add(MessageChain(["--------------------\n"]))
    #BPM
    message.add(MessageChain([f"BPM:{bpm}\n"]))
    #物量
    message.add(MessageChain([f"物量:{count}\n"]))
    #时长
    message.add(MessageChain([f"时长:{time}\n"]))
    #三级信息 ( 服务器 | 游玩网址 )
    message.add(MessageChain(["--------------------\n"]))
    #服务器
    message.add(MessageChain([f"服务器:{server}\n"]))
    #游玩网址
    url = f"https://sonolus.bestdori.com/community/levels/bestdori-community-{id}"
    message.add(MessageChain([f"前去游玩:{url}\n"]))
    #四级信息 ( 谱面图片 )
    message.add(MessageChain(["--------------------\n"]))
    imageURL = renderingChart(charData= chart, charID= id, server= server, difficult= difficult)
    message.add(MessageChain([ImageMessage(f"file://C:/Users/Administrator/Desktop/bot/OneBot-General/{imageURL}")]))
    await bot.reply_to_message(msg, message)
#官谱
async def sreachOfficalMakeChart(bot, msg, parameters: list[str], difficulty: int):
    song_url = "https://bestdori.com//api/songs/all.7.json"
    song_list = requestData(song_url)
    if not parameters[0].isdigit():
        #歌名模式搜索
        result = sreachFromNameMode(song_list, parameters)
        result = filterFromDifficulty(song_list, result, difficulty)
        #处理结果
        if len(result) <= 0:
            #条件式搜索
            result = sreachFromFilterMode(song_list, parameters)
            result = filterFromDifficulty(song_list, result, difficulty)
        #处理结果
        #如果只有一个结果，即返回谱面信息
        #如果多于一个结果，即返回结果列表
        if len(result) == 1:
            charID = result[0]
            #茨菇查谱
            await returnOfficalMakeChart(bot, msg, charID, song_list, difficulty)
        else:
            message = MessageChain(["\n小生物查询结果为:"])
            if len(result) <= 0:
                message.add(MessageChain(["\n无"]))
            for songID in result:
                serverid = 0
                while song_list[songID]['musicTitle'][serverid] == None:
                    serverid += 1
                message.add(MessageChain([f"\n{songID}. {song_list[songID]['musicTitle'][serverid]}"]))
            await bot.reply_to_message(msg, message)
        return
    #茨菇查谱
    await returnOfficalMakeChart(bot, msg, parameters[0], song_list, difficulty)
    return
#随机查谱
async def randomSreachChart(bot, msg):
    song_url = "https://bestdori.com//api/songs/all.7.json"
    song_list = requestData(song_url)
    id_set = list(song_list.keys())
    idx = random.randint(0, len(id_set)-1)
    song = song_list[id_set[idx]]
    difficulty_set = list(song["difficulty"].keys())
    idx = random.randint(0, len(difficulty_set)-1)
    difficulty = difficulty_set[idx]
    await sreachOfficalMakeChart(bot, msg, [str(id_set[idx])], int(difficulty))
    return
#新增搜索词
async def add_key_word_for_song(bot, msg, raw_message, be_at):
    command = raw_message[5:].strip()
    id = re.findall(r'(\d+)', command)[0]
    command = command.replace(id,"").strip()
    command = command.replace("，",",")
    sreachKey = []
    keySet = command.split(",")
    for key in keySet:
        sreachKey.append(key.strip())
    id = str(id)
    keySet = sreachKey
    #读入关键词本
    keysetPath = "data/classify/bangdream/keyset.json"
    sreachKey = Config.load_from_file(keysetPath)
    #更新
    for key in keySet:
        if key in sreachKey:
            if sreachKey[key] == None:
                sreachKey[key] = [id]
            if id not in sreachKey[key]:
                sreachKey[key].append(id)
            else: keySet.remove(key)
        else:
            sreachKey[key] = [id]
    #写入关键词本
    sreachKey.dump_to_file(keysetPath)
    message = MessageChain([f" 已为谱面ID [{id}] 新增关键词 {keySet} "])
    await bot.reply_to_message(msg, message)

def requestData(url: str):
    #try catch expeted: ( Network Exception(s) |  JSONDecode Exception(s) )
    try:
        #Get response(s) from url
        response = requests.get(url)
        #Json the data
        data:dict = response.json()
    except Exception as e:
        #Error message
        print("[request-from-api: Error]: Data request error from: " + url)
        print("[request-from-api: Error]: Error details belowe:")
        print("[request-from-api: Error]: " + str(e))
        #return the error
        raise e
    #return
    return data
#谱面渲染至图片 - bestdori-render
def renderingChart(charData: list, charID: str | int, server: str, difficult = "expert"):
    #渲染
    image = render(charData)
    #文件名称: -> charID | charID-difficult, png format
    if server == "Bandori":
        imageURL: str = f"data/classify/bangdream/char/{charID}-{difficult}.png"
    else:
        imageURL: str = f"data/classify/bangdream/char/{charID}.png"
    #储存文件
    image.save(imageURL)
    #返回文件地址
    return imageURL
#歌名模式搜索
def sreachFromNameMode(song_list, parameters: list[str]):
    #歌名模式
    result = []
    #----->歌名
    for id in song_list:
        for name in song_list[id]['musicTitle']:
            if name != None:
                if parameters[0].lower() in name.lower() and id not in result:
                    result.append(id)
                    break
    for parameter in parameters:
        temp = []
        for id in result:
            for name in song_list[id]['musicTitle']:
                if name != None:
                    if parameter.lower() in name.lower() and id not in temp:
                        temp.append(id)
        result = temp
    if len(result) == 1: return result
    #----->关键词
    keysetPath = "data/classify/bangdream/keyset.json"
    #读入关键词本
    sreachKey = Config.load_from_file(keysetPath)
    for key in sreachKey:
        for keyword in parameters:
            if keyword.lower() in key.lower() and sreachKey[key] not in result:
                result.extend(sreachKey[key])
    return list(set(result))
#条件式搜索
def sreachFromFilterMode(song_list, parameters: list[str]):
    filters = list(parameters)
    filterResult = []
    #装填
    for id in song_list:
        filterResult.append(id)
    #曲目种类
    types = ["原创", "动画", "翻唱", "covers", "cover"]
    songType = list(set(filters) & set(types))
    if len(songType)>0: 
        filters.remove(songType[0])
        filterResult = list(set(sreachByType(song_list, filterResult, songType[0])) & set(filterResult))
    if len(filterResult) <= 1: return filterResult
    #等级
    for parameter in filters:
        if parameter[:2] == "lv" and parameter[2:].isdigit():
            level = int(parameter[2:])
            filters.remove(parameter)
            filterResult = list(set(sreachByLevel(song_list, filterResult, level)) & set(filterResult))
            break
    if len(filterResult) <= 1: return filterResult
    #物量
    for parameter in filters:
        if parameter[:2] == "物量":
            if "-" in parameter[2:]:
                notesRange = parameter[2:].split("-")
                if notesRange[0].isdigit() and notesRange[1].isdigit():
                    notes1 = int(notesRange[0])
                    notes2 = int(notesRange[1])
                    filters.remove(parameter)
                    filterResult = list(set(sreachByNotes(song_list, filterResult, notes1, notes2)) & set(filterResult))
                    break
            elif parameter[2:].isdigit():
                notes = int(parameter[2:])
                filters.remove(parameter)
                filterResult = list(set(sreachByNotes(song_list, filterResult, notes)) & set(filterResult))
                break
    if len(filterResult) <= 1: return filterResult
    #BPM
    for parameter in filters:
        if parameter[:3].lower() == "bpm":
            if "-" in parameter[3:]:
                bpmRange = parameter[3:].split("-")
                if bpmRange[0].isdigit() and bpmRange[1].isdigit():
                    bpm1 = int(bpmRange[0])
                    bpm2 = int(bpmRange[1])
                    filters.remove(parameter)
                    filterResult = list(set(sreachByBPM(song_list, filterResult, bpm1, bpm2)) & set(filterResult))
                    break
            elif parameter[3:].isdigit():
                bpm = int(parameter[3:])
                filters.remove(parameter)
                filterResult = list(set(sreachByBPM(song_list, filterResult, bpm)) & set(filterResult))
                break
    if len(filterResult) <= 1: return filterResult
    #乐团名称
    if len(filters) > 0:
        filterResult = list(set(sreachByBand(song_list, filterResult, " ".join(filters))) & set(filterResult))
    return filterResult
#filter by difficulty
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


#从bestdori请求所有该曲目种类的曲目ID
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
#从bestdori请求所有该等级的曲目ID
def sreachByLevel(songList, filterResult, level: int | str):
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
#从bestdori请求该乐团所属的所有曲目ID
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
    band_name_list = requestData(band_url)
    #模糊匹配乐团信息，返回可能参数 (Band ID)
    for id in filterResult:
        for name in band_name_list[str(songList[id]["bandId"])]["bandName"]:
            if name != None:
                if band.lower() in name.lower() and id not in result:
                    result.append(id)
    return result
#从bestdori请求该物量所属的所有曲目ID
def sreachByNotes(songList, filterResult, notes1: int | str, notes2: int | str = None):
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
#从bestdori请求该BPM所属的所有曲目ID
def sreachByBPM(songList, filterResult, bpm1: int | str, bpm2: int | str = None):
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
#茨菇查谱
async def returnOfficalMakeChart(bot, msg, charID: str, song_list, d: int):
    charID = int(charID)
    function = lambda: song_chart([3, 0], charID, d)
    await call_tsugu(bot, msg, callback = function)
#茨菇查曲
async def returnSongInfo(bot, msg, charID: str):
    if charID.isdigit == True:
        function = lambda: search_song([3, 0], charID)
    else:
        function = lambda: search_song([3, 0], text=charID)
    await call_tsugu(bot, msg, callback = function)


#查卡
async def sreachCard(bot, msg, cardID):
    if cardID.isdigit() == True:
        function = lambda: search_card([3, 0], cardID)
    else:
        function = lambda: search_card([3, 0], cardID)
    await call_tsugu(bot, msg, callback = function)
#随机查卡
async def randomSreachCard(bot, msg):
    try:
        url = "https://bestdori.com/api/cards/all.0.json"
        data = requestData(url)
    except:
        message = MessageChain(["服务器网络连接出错"])
        await bot.reply_to_message(msg, message)
        return
    index = list(data.keys())
    idx = random.randint(0, len(index)-1)
    cardID = index[idx]
    if cardID == "":
        return
    await sreachCard(bot, msg, cardID)
#随机卡面
async def randomGetCard(bot, msg):
    message = MessageChain(["\n"])
    try:
        url = "https://bestdori.com/api/cards/all.0.json"
        data = requestData(url)
    except:
        message = MessageChain(["服务器网络连接出错"])
        await bot.reply_to_message(msg, message)
        return
    index = list(data.keys())
    idx = random.randint(0, len(index)-1)
    cardID = index[idx]
    if cardID == "":
        return
    try:
        url = f"https://bestdori.com/api/cards/{cardID}.json"
        data = requestData(url)
    except:
        message = MessageChain(["服务器网络连接出错"])
        await bot.reply_to_message(msg, message)
        return
    train = False
    if data['rarity']>=3:
        if random.randint(1, 100) <= 50: train = True
        else: train = False
    message.add(ImageMessage(getImage(data,train)))
    await bot.reply_to_message(msg, message)
#从bestdori拉取卡面图片
def getImage(data, train):
    res = data['resourceSetName']
    if train:
        image = f"https://bestdori.com/assets/jp/characters/resourceset/{res}_rip/card_after_training.png"
    else:
        image = f"https://bestdori.com/assets/jp/characters/resourceset/{res}_rip/card_normal.png"
    return image


#lsycx
async def lsycx(bot, msg, raw_message, be_at):
    raw_message = raw_message[5:].strip()
    server = 3
    tier = 1000
    event_id = None
    if len(raw_message.strip())>0:
        try:
            inputServer = re.findall(r'(\D+)', raw_message.strip())
            inputServer = inputServer[-1].strip().lower()
            serverSet = {"jp":0, "en":1, "tw":2, "cn":3, "kr":4}
            server = serverSet[inputServer]
        except: pass
        raw_message = re.findall(r'(\d+)', raw_message.strip())
        if len(raw_message)>0:
            try:
                tier = int(raw_message[0])
            except: pass
            try:
                event_id = int(raw_message[1])
            except: pass
    function = lambda: cutoff_list_of_recent_event(server, tier, event_id)
    await call_tsugu(bot, msg, callback = function)
#ycxall
async def ycxall(bot, msg, raw_message, be_at):
    raw_message = raw_message[6:].strip()
    server = 3
    event_id = None
    if len(raw_message.strip())>0:
        try:
            inputServer = re.findall(r'(\D+)', raw_message.strip())
            inputServer = inputServer[-1].strip().lower()
            serverSet = {"jp":0, "en":1, "tw":2, "cn":3, "kr":4}
            server = serverSet[inputServer]
        except: pass
        raw_message = re.findall(r'(\d+)', raw_message.strip())
        if len(raw_message)>0:
            try:
                event_id = int(raw_message[0])
            except: pass
    function = lambda: cutoff_all(server, event_id)
    await call_tsugu(bot, msg, callback = function)
#ycx
async def self_ycx(bot, msg, raw_message, be_at):
    if raw_message[0:3].lower() == "ycx":
        raw_message = raw_message[3:].strip()
    server = 3
    tier = 1000
    event_id = None
    if len(raw_message.strip())>0:
        try:
            inputServer = re.findall(r'(\D+)', raw_message.strip())
            inputServer = inputServer[-1].strip().lower()
            serverSet = {"jp":0, "en":1, "tw":2, "cn":3, "kr":4}
            server = serverSet[inputServer]
        except: pass
        raw_message = re.findall(r'(\d+)', raw_message.strip())
        if len(raw_message)>0:
            try:
                tier = int(raw_message[0])
            except: pass
            try:
                event_id = int(raw_message[1])
            except: pass
    function = lambda: cutoff_detail(server, tier, event_id)
    await call_tsugu(bot, msg, callback = function)

#查玩家
async def check_player_info(bot, msg, raw_message, be_at):
    raw_message = raw_message[3:].strip()
    server = "cn"
    player_id = raw_message
    if raw_message[-2:].lower() in ["jp", "en", "tw", "cn", "kr"]:
        server = raw_message[-2:].lower()
        player_id = raw_message[:-2].strip()
    try:
        if player_id.isdigit():
            await self_search_player(bot, msg, player_id, server)
            return
        raise Exception()
    except:
        message = MessageChain(["参数错误"])
        await bot.reply_to_message(msg, message)
#茨菇查玩家
async def self_search_player(bot, msg, player_id, server):
    playerID = int(player_id)
    try:
        serverSet = {"jp":0, "en":1, "tw":2, "cn":3, "kr":4}
        server = serverSet[server]
    except: server = 3
    function = lambda: search_player(playerID, server)
    await call_tsugu(bot, msg, callback = function)
#玩家状态
async def get_play_info(bot, msg, user_id, id):
    #读取玩家绑定记录
    users = Config.load_from_file("data/classify/bangdream/userBinding.json")
    try:
        user = users[str(user_id)][id]
    except:
        message = MessageChain(["无绑定记录"])
        await bot.reply_to_message(msg, message)
        return
    #查玩家资料
    await self_search_player(bot, msg, user["acc"], user["server"])
    return


#绑定玩家
async def bing_user(bot, msg, raw_message, be_at):
    raw_message = raw_message[4:].strip()
    player_id = raw_message.strip()
    server = "cn"
    if raw_message[-2:].lower() in ["jp", "en", "tw", "cn", "kr"]:
        server = raw_message[-2:].lower()
        player_id = raw_message[:-2].strip()
    try:
        if player_id.isdigit():
            uri = f"https://bestdori.com/api/player/{server}/{player_id}"
            data = requestData(uri)
            if data["data"]["profile"] != None:
                #读取文件
                users = Config.load_from_file("data/classify/bangdream/userBinding.json")
                try:
                    data = users[str(msg["sender"]["user_id"])]
                except:
                    data = []
                #检查数据未绑定
                for savedData in data:
                    if player_id == savedData["acc"] and server == savedData["server"]:
                        message = MessageChain(["账号已存在，请勿重复储存"])
                        await bot.reply_to_message(msg, message)
                        return
                #更新
                data.append({"acc":player_id, "server": server})
                users[str(msg["sender"]["user_id"])]=data
                #写入文件
                users.dump_to_file("data/classify/bangdream/userBinding.json")
                #反馈
                message = MessageChain(["账号储存成功"])
                await bot.reply_to_message(msg, message)
                await checkUserBinded(bot, msg)
                return
            else:
                await bot.reply_to_message(msg, MessageChain(["账号不存在"]))
                print(data["data"])
                if len(str(data["data"]))<500:
                    await bot.send_private_msg(bot.owner[0], MessageChain([str(data["data"])]))
                else:
                    await bot.send_private_msg(bot.owner[0], MessageChain(["Bind Error"]))
                return
        raise Exception()
    except:
        message = MessageChain(["参数错误"])
        await bot.reply_to_message(msg, message)
#绑定记录
async def checkUserBinded(bot, msg):
    message = MessageChain(["\n"])
    try:
        message.add(MessageChain(["绑定记录:"]))
        users = Config.load_from_file("data/classify/bangdream/userBinding.json")
        user = users[str(msg["sender"]["user_id"])]
        for i in range(len(user)):
            message.add(MessageChain([f"\n{str(i+1)}. {user[i]['acc']} {user[i]['server']}"]))
    except Exception as e:
        message.add(MessageChain(["无绑定记录"]))
    await bot.reply_to_message(msg, message)
#删除绑定
async def delUserBinded(bot, msg, raw_message, be_at):
    raw_message = raw_message[4:].strip()
    try:
        users = Config.load_from_file("data/classify/bangdream/userBinding.json")
        user = users[str(msg["sender"]["user_id"])]
        if raw_message != None:
            if raw_message.isdigit and raw_message!="0":
                if int(raw_message)<=len(user):
                    user.remove(user[int(raw_message)-1])
                    users.dump_to_file("data/classify/bangdream/userBinding.json")
                    message = MessageChain(["账号删除成功"])
                    await bot.reply_to_message(msg, message)
                    await checkUserBinded(bot, msg)
                    return
        raise Exception()
    except:
        message = MessageChain(["参数错误"])
        await bot.reply_to_message(msg, message)
        traceback.print_exc()


#查试炼
async def self_event_stage(bot, msg, raw_message, be_at):
    raw_message = raw_message[3:].strip()
    server = raw_message[-2:]
    try:
        serverSet = {"jp":0, "en":1, "tw":2, "cn":3, "kr":4}
        server = serverSet[server]
        raw_message = raw_message[:-2].strip()
    except: server = 3
    event_id = None
    if len(raw_message)>0:
        if raw_message.isdigit:
            event_id = int(raw_message)
    function = lambda: event_stage(server, event_id, True)
    await call_tsugu(bot, msg, callback = function)
    
#查活动
async def self_search_event(bot, msg, raw_message, be_at):
    raw_message = raw_message[3:].strip()
    function = lambda: search_event([3, 0], text=raw_message)
    await call_tsugu(bot, msg, callback = function)


#猜谱
async def guess_chart(bot, msg, raw_message, be_at, num = 0):
    if str(msg["group_id"]) in guess_list.keys():
        message = MessageChain(["\n已有未完成的猜谱游戏，请先结束该游戏"])
        await bot.reply_to_message(msg, message)
        return
    song_url = "https://bestdori.com//api/songs/all.7.json"
    song_list = requestData(song_url)
    temp = {}
    for song in song_list:
        for d in song_list[song]["difficulty"]:
            if song_list[song]["difficulty"][d]["playLevel"]>=26:
                temp[song] = song_list[song]
                break
    idx = random.randint(0, len(temp)-1)
    charID = list(temp)[idx]
    song = song_list[charID]
    d_list = list(song["difficulty"].keys())[3:]
    d = d_list[random.randint(0, len(d_list)-1)]
    try:
        await bot.reply_to_message(msg, MessageChain("\n正在加载谱面..."))
        charID = int(charID)
        chart = song_chart([3, 0], charID, d)
        if chart[0]["type"] != "base64":
            raise SyntaxError()
        data = base64.b64decode(chart[0]["string"])
        im = Image.open(io.BytesIO(data))
        #图片切割
        image_list = split_image(image_data=im, num=num)
        if num == 0:
            score = 5
        else:
            score = 16 - (num*1)
        #
        message = MessageChain(["\n猜猜这是哪首歌的谱面？\n"])
        for i in range(len(image_list)):
            #保存图片
            imageURL: str = f"data/classify/bangdream/char/guess_{i}.jpg"
            image_list[i].save(imageURL)
            #发送图片
            message.add(ImageMessage(f"file://{bot.localtion}/{imageURL}"))
        await bot.reply_to_message(msg, message)
        guess_list.update({str(msg["group_id"]): {"charID": str(charID), "difficulty": str(d), "tips": 0, "score": score, "song_data": song, "chart_img": chart[0]["string"]}})
        return
    except Exception as e:
        message = MessageChain(["\n茨菇后台连接失败"])
        await bot.reply_to_message(msg, message)
        traceback.print_exc()
        return
#猜谱回答
async def answer_guess_chart(bot, msg, answer, be_at):
    if str(msg["group_id"]) not in guess_list.keys():
        return
    if answer.strip() in ["bzd", "不知道"]:
        song = guess_list.pop(str(msg["group_id"]))
        charID = song["charID"]
        song_name = None
        for name in song["song_data"]["musicTitle"]:
            if name != None:
                song_name = name
                break
        d_set = {"3": "expert", "4": "special"}
        message = MessageChain([f"\n已结束猜谱，正确答案为:\n{charID}. {song_name} [{d_set[song['difficulty']]}] [lv{song['song_data']['difficulty'][song['difficulty']]['playLevel']}]"])
        message.add(ImageMessage(f"base64://{song["chart_img"]}"))
        await bot.reply_to_message(msg, message)
    elif answer.strip() in ["提示"]:
        tips_id = guess_list[str(msg["group_id"])]["tips"]
        if tips_id <= 4 and guess_list[str(msg["group_id"])]["score"] > 0:
            guess_list[str(msg["group_id"])]["score"] -= 2
            if guess_list[str(msg["group_id"])]["score"] < 0:
                guess_list[str(msg["group_id"])]["score"] = 0
        #物量 - 2
        if tips_id == 0:
            notes = guess_list[str(msg["group_id"])]["song_data"]["notes"][guess_list[str(msg["group_id"])]["difficulty"]]
            low = (notes // 500) * 500
            high = low + 500
            message = MessageChain([f"\n提示{tips_id+1}：该谱面物量为 {low} - {high}"])
            await bot.reply_to_message(msg, message)
            guess_list[str(msg["group_id"])]["tips"] += 1
        #难度 - 2
        elif tips_id == 1:
            level = guess_list[str(msg["group_id"])]["song_data"]["difficulty"][guess_list[str(msg["group_id"])]["difficulty"]]
            message = MessageChain([f"\n提示{tips_id+1}：该谱面难度为 {level['playLevel']}"])
            await bot.reply_to_message(msg, message)
            guess_list[str(msg["group_id"])]["tips"] += 1
        #乐团 - 2
        elif tips_id == 2:
            band_id = guess_list[str(msg["group_id"])]["song_data"]["bandId"]
            band_name = None
            band_url = "https://bestdori.com/api/bands/all.1.json"
            band_list = requestData(band_url)
            for name in band_list[str(band_id)]["bandName"]:
                if name != None:
                    band_name = name
                    break
            message = MessageChain([f"\n提示{tips_id+1}：该谱面所属乐团为 {band_name}"])
            await bot.reply_to_message(msg, message)
            guess_list[str(msg["group_id"])]["tips"] += 1
        #BPM - 2
        elif tips_id == 3:
            bpm_data = guess_list[str(msg["group_id"])]["song_data"]["bpm"][guess_list[str(msg["group_id"])]["difficulty"]]
            if len(bpm_data) == 1:
                bpm = bpm_data[0]["bpm"]
                low = (bpm // 50) * 50
                high = low + 50
                message = MessageChain([f"\n提示{tips_id+1}：该谱面BPM为 {low} - {high}"])
            else:
                bpm1 = bpm_data[0]["bpm"]
                low = (bpm1 // 50) * 50
                bpm2 = bpm_data[-1]["bpm"]
                high = (bpm2 // 50) * 50 + 50
                message = MessageChain([f"\n提示{tips_id+1}：该谱面BPM为 {low} - {high}"])
            await bot.reply_to_message(msg, message)
            guess_list[str(msg["group_id"])]["tips"] += 1
        #曲目种类 - 2
        elif tips_id == 4:
            song_type = guess_list[str(msg["group_id"])]["song_data"]["tag"]
            typeSet = {"normal":"原创", "anime":"动画", "tie_up":"翻唱"}
            message = MessageChain([f"\n提示{tips_id+1}：该谱面曲目种类为 {typeSet[song_type]}"])
            await bot.reply_to_message(msg, message)
            guess_list[str(msg["group_id"])]["tips"] += 1
        #提示用完
        else:
            message = MessageChain([f"\n提示次数已用完"])
            await bot.reply_to_message(msg, message)
    elif answer.strip().isdigit():
        charID = guess_list[str(msg["group_id"])]["charID"]
        if answer.strip() == charID:
            song = guess_list.pop(str(msg["group_id"]))
            song_name = None
            for name in song["song_data"]["musicTitle"]:
                if name != None:
                    song_name = name
                    break
            d_set = {"3": "expert", "4": "special"}
            message = MessageChain([f"\n回答正确！答案为:\n{charID}. {song_name} [{d_set[song['difficulty']]}] [lv{song['song_data']['difficulty'][song['difficulty']]['playLevel']}]\n"])
            message.add(MessageChain([f"获得积分: {song['score']} 分"]))
            message.add(ImageMessage(f"base64://{song["chart_img"]}"))
            await bot.reply_to_message(msg, message)
            await add_scroes(bot, msg, score=song["score"], add_type="chart")
    elif be_at:
        charID = guess_list[str(msg["group_id"])]["charID"]
        parameters = answer.split(" ")
        temp = []
        for p in parameters:
            if len(p.strip()) > 1:
                temp.append(p.strip())
        parameters = temp
        if len(parameters) >= 1:
            song_url = "https://bestdori.com//api/songs/all.7.json"
            song_list = requestData(song_url)
            result = sreachFromNameMode(song_list, parameters)
            if charID in result:
                song = guess_list.pop(str(msg["group_id"]))
                song_name = None
                for name in song["song_data"]["musicTitle"]:
                    if name != None:
                        song_name = name
                        break
                d_set = {"3": "expert", "4": "special"}
                message = MessageChain([f"\n回答正确！答案为:\n{charID}. {song_name} [{d_set[song['difficulty']]}] [lv{song['song_data']['difficulty'][song['difficulty']]['playLevel']}]\n"])
                message.add(MessageChain([f"获得积分: {song['score']} 分"]))
                message.add(ImageMessage(f"base64://{song["chart_img"]}"))
                await bot.reply_to_message(msg, message)
                await add_scroes(bot, msg, score=song["score"], add_type="chart")

#图片切割函数
def split_image(image_path = None, image_data = None, num = 0):
    if image_path is not None:
        # 打开原始图片
        img = Image.open(image_path)
    else: img = image_data
    width, height = img.size
    image_list = []

    # 1. 删除最左侧一栏（封面）：裁剪掉左侧一列区域，这里假设左侧栏宽度为图片宽度的1/总列数，也可手动指定宽度
    # 若知道左侧栏具体像素宽度，直接替换crop的第一个参数即可，例如left_crop_width = 80
    if num == 0:
        left_crop_width = 250  # 按比例估算左侧栏宽度，可根据实际图片调整
    else:
        left_crop_width = 250 + (735/2)  # 按比例估算左侧栏宽度，可根据实际图片调整
    img_cropped = img.crop((left_crop_width, 0, width, height))  # 裁剪左侧栏后的新图

    if num > 0:
        # img_cropped.show()
        crop_w, crop_h = img_cropped.size

        # 2. 纵向分为4段：计算每段的宽度
        vertical_segment = (735/2) * 3

        row_height = int(crop_h / 4)

        for v in range(int(crop_w/vertical_segment)):
            # 计算纵向裁剪的左右坐标
            v_left = v * vertical_segment
            v_right = (v + 1) * vertical_segment

            # 遍历横向每2行
            h = 0
            while h * row_height < crop_h and (crop_h - (h * row_height) >= row_height):
                # 计算横向裁剪的上下坐标
                h_top = h * row_height
                h_bottom = (h + 1) * row_height if (h + 1) * row_height < crop_h else crop_h

                # 裁剪小图
                sub_img = img_cropped.crop((v_left, h_top, v_right, h_bottom))
                image_list.append(sub_img)
                h += 1
        temp = []
        for i in range(num):
            try:
                idx = random.randint(0, len(image_list)-1)
                img = image_list.pop(idx)
                temp.append(img)
            except IndexError:
                break
        image_list = temp
    else:
        image_list.append(img_cropped)
    return image_list

#
async def add_scroes(bot, msg, score = 0, add_type: str = "sp"):
    old_rank = -1
    user_id = msg["sender"]["user_id"]
    if user_id is not str:
        user_id = str(user_id)
    #读取文件
    users = Config.load_from_file("data/classify/general/guess_scores.json")
    try:
        data = users[user_id]
    except:
        data = {"scores": 0.0, "chart": 0, "card": 0, "sp": 0.0, "name": msg["sender"]["nickname"], "cards": [], "use_card": True, "time": 0}
    #计算排名
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
            message = MessageChain([f"\n使用卡牌加成 x{1+card_bonus}，本次获得积分提升至 {int(score)} 分！"])
            await bot.reply_to_message(msg, message)
    data["scores"] += score
    if add_type == "sp":
        data["sp"] += score
    else:
        data[add_type] += 1
    users[user_id] = data
    #写入文件
    users.dump_to_file("data/classify/general/guess_scores.json")
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
        await bot.reply_to_message(msg, message)
