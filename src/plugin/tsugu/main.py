
# == Tsugu插件文件 ==

#此文件为OneBot11-小生物的Tsugu插件涵数文件
#应用环境为LL-Bot v2.4.4

#如果不清楚具体作用，除配置外，请不要修改任何参数代码


#引用库
#  ==> pip自动下载缺失的库
# type: ignore
import os, asyncio, random, io
from datetime import datetime
from src.importer import import_package
from src.plugin.功能注册器.main import get_places_id, help, get_plgin_registrated_list
from src.plugin.小生物积分.main import add_scroes
from src.plugin.tsugu.config import load_config
from src.plugin.tsugu.call_tsugu import call_tsugu, call_net
from src.tools.reply_message import feedback
from src.tools.image_cuter import split_image
from src.loger import log
exec(import_package("eyed3"))
exec(import_package("requests"))
exec(import_package("traceback"))
exec(import_package("re"))
exec(import_package("base64"))
exec(import_package("render", package_from= "bestdori.render", package_pip_Name= "bestdori-render"))
exec(import_package("Image, ImageDraw", package_from= "PIL", package_pip_Name= "pillow"))
exec(import_package("Config", package_from= "config_io", package_pip_Name= "config-io"))
exec(import_package(
    "MessageChain, ImageMessage", 
    package_from= "OneBotConnecter.MessageType", package_pip_Name= "OneBotConnecter"))


bangdream_config = load_config("data/plugin/bangdream/config.yaml")
music_temp_path = bangdream_config["music_temp_path"]
key_set_path = bangdream_config["key_set_path"]
user_acc_path = bangdream_config["user_acc_path"]

guess_char_list = {}
guess_card_list = {}


async def onMessage(bot, message, raw_message, be_at, msgType):
    # == 谱面 ==
    # 查谱
    if raw_message[0:2] == "查谱":
        parameter = raw_message.replace("查谱面", "查谱")
        parameter = parameter[2:].strip()
        if len(parameter) <= 0:
            log(f"查谱: 空参数", needPrint=(bot.testMode))
            send_message = MessageChain(["\n查询bangdream官方或bestdori sonolus社区谱面图片"])
            send_message.add("\n可用参数:")
            send_message.add("\n-------------------------")
            send_message.add("\n[(歌名/关键词/ID) 难度]")
            send_message.add("\n例:六兆年 sp")
            send_message.add("\n-------------------------")
            send_message.add("\n[(等级/乐团名称/歌曲种类/BPM/物量) 难度]")
            send_message.add("\n例:萝 lv27 翻唱 BPM100+ 物量500+ hd\n")
            await feedback(bot, message, send_message)
            return
        await sreachChart(bot, message, parameter)
    # 自制查谱
    elif raw_message[0:4] == "查自制谱":
        parameter = raw_message.replace("查自制谱面", "查自制谱")
        parameter = parameter[4:].strip()
        if len(parameter) <= 0:
            log(f"查自制谱: 空参数", needPrint=(bot.testMode))
            send_message = MessageChain(["\n查询bestdori sonolus社区谱面图片"])
            send_message.add("\n可用参数:")
            send_message.add("\n-------------------------")
            send_message.add("\n[ID]")
            send_message.add("\n例:114514")
            await feedback(bot, message, send_message)
            return
        try:
            charID = parameter
            if not charID.isdigit(): raise Exception()
            url = "https://bestdori.com/api/post/details?id=" + charID
            data = await call_net(url)
            if data == {}: 
                send = MessageChain(["\n小生物网络连接出现问题,请等下再试"])
                await feedback(bot, message, send)
                log(f"网络连接出现问题", needPrint=(bot.testMode))
                return
            log(f"Bestdori接口回复: {data}", needPrint=(bot.testMode))
            chartDetail = data["post"]
            await sonolus_chart(bot, message, chartDetail, charID)
            return
        except Exception as e:
            log(f"Get Exception:\n{e}")
            send = MessageChain(["自制谱面ID参数错误"])
            await feedback(bot, message, send)
    # 查官谱
    elif raw_message[0:3] == "查官谱":
        parameter = raw_message.replace("查官谱面", "查官谱")
        command = parameter[3:].strip()
        if len(parameter) <= 0:
            log(f"查官谱: 空参数", needPrint=(bot.testMode))
            send_message = MessageChain(["\n查询bangdream官方谱面图片"])
            send_message.add("\n可用参数:")
            send_message.add("\n-------------------------")
            send_message.add("\n[(歌名/关键词/ID) 难度]")
            send_message.add("\n例:六兆年 sp")
            send_message.add("\n-------------------------")
            send_message.add("\n[(等级/乐团名称/歌曲种类/BPM/物量) 难度]")
            send_message.add("\n例:萝 lv27 翻唱 BPM100+ 物量500+ hd\n")
            await feedback(bot, message, send_message)
            return
        parameters = command.split(" ")
        difficulty = parameters[-1]
        difficultyKeySet = {"ez":0, "nm":1, "hd":2, "ex":3, "sp":4}
        try: 
            difficulty = difficultyKeySet[difficulty]
            parameters = parameters[:-1]
        except: difficulty = 3
        await offical_chart(bot, msg, parameters, difficulty)
    # 随机查谱
    elif raw_message in ["随机查谱", "随机谱面"]:
        await randomSreachChart(bot, message)
    # 新增搜索词
    elif raw_message[:5] == "新增搜索词":
        await add_key_word_for_song(bot, message, raw_message, be_at)
    # 查曲
    elif raw_message[0:2] == "查曲":
        songID = raw_message[2:].strip()
        if len(songID) <= 0:
            log(f"查曲: 空参数", needPrint=(bot.testMode))
            send_message = MessageChain(["\n查询bangdream官方歌曲信息"])
            send_message.add("\n可用参数:")
            send_message.add("\n-------------------------")
            send_message.add("\n同茨菇tsugu")
            await feedback(bot, message, send_message)
            return
        await returnSongInfo(bot, message, songID)
    # == 玩家 ==
    #查玩家
    elif raw_message[0:3] == "查玩家":
        await check_player_info(bot, message, raw_message, be_at)
    # 绑定玩家
    elif raw_message[0:4] == "绑定玩家":
        await bing_user(bot, message, raw_message, be_at)
    # 绑定记录
    elif raw_message[0:4] == "绑定记录":
        await checkUserBinded(bot, message)
    # 删除绑定
    elif raw_message[0:4] == "删除绑定":
        await delUserBinded(bot, message, raw_message, be_at)
    # 玩家状态
    elif raw_message[0:4] == "玩家状态":
        raw_message = raw_message[4:].strip()
        id = 0
        if len(raw_message)>0:
            if raw_message.isdigit():
                if int(raw_message) > 0:
                    id = int(raw_message)-1
        await get_play_info(bot, message, message["sender"]["user_id"], id)
    # 逮捕
    elif raw_message[0:2] == "逮捕" and msgType == "Group_message":
        raw_message = raw_message[2:].strip()
        if "[CQ:at,qq=" not in raw_message and "[CQ:reply,id=" not in raw_message:
            log(f"逮捕: 空参数", needPrint=(bot.testMode))
            send_message = MessageChain(["\n查询群友的玩家信息"])
            send_message.add("\n可用参数:")
            send_message.add("\n-------------------------")
            send_message.add("\n[艾特/回复]")
            send_message.add("\n例:@群主")
            await feedback(bot, message, send_message)
            return
        idx = raw_message.find("qq=")+3
        raw_message = raw_message[idx:]
        targetID = re.findall(r'(\d+)', raw_message)
        await get_play_info(bot, message, targetID[0], 0)
    # == 卡片 ==
    # 查卡947
    elif '查卡' in raw_message and "947" in raw_message:
        if random.randint(1,100) > 50:
            send = MessageChain([" 不许查!!!"])
            await feedback(bot, message, send)
            return
        if raw_message[0:3] == "查卡面":
            url = f"https://bestdori.com/api/cards/947.json"
            data = await call_net(url)
            send = MessageChain([ImageMessage(getImage(data,False))])
            send.add(ImageMessage(getImage(data,True)))
            await feedback(bot, message, send)
        elif raw_message[0:2] == "查卡":
            await sreachCard(bot, message, "947")
    # 查卡面
    elif raw_message[0:3] == "查卡面":
        cardID = raw_message[3:].strip()
        if len(cardID) <= 0:
            log(f"查卡面: 空参数", needPrint=(bot.testMode))
            send_message = MessageChain(["\n查询bangdream官方卡面图片"])
            send_message.add("\n可用参数:")
            send_message.add("\n-------------------------")
            send_message.add("\n同茨菇tsugu")
            await feedback(bot, message, send_message)
            return
        if cardID.isdigit() == True:
            url = f"https://bestdori.com/api/cards/{cardID}.json"
            data = await call_net(url)
            send = MessageChain([ImageMessage(getImage(data,False))])
            try:
                send.add(ImageMessage(getImage(data,True)))
            except: pass
            await feedback(bot, message, send)
        return
    # 随机查卡
    elif raw_message == "随机查卡":
        await randomSreachCard(bot, message)
        return
    # 随机卡面
    elif raw_message == "随机卡面":
        await randomGetCard(bot, message)
        return
    # 查卡池 - search_gacha - serverlist, id
    elif raw_message[0:3] == "查卡池":
        raw_message = raw_message[3:].strip()
        if len(raw_message) <= 0 or not raw_message.isdigit():
            log(f"查卡池: 空参数", needPrint=(bot.testMode))
            send_message = MessageChain(["\n查询bangdream官方卡池信息"])
            send_message.add("\n可用参数:")
            send_message.add("\n-------------------------")
            send_message.add("\n同茨菇tsugu")
            await feedback(bot, message, send_message)
            return
        await self_search_gacha(bot, message, raw_message, be_at)
    # 查卡
    elif raw_message[0:2] == "查卡":
        cardID = raw_message[2:].strip()
        if len(cardID) <= 0:
            log(f"查卡: 空参数", needPrint=(bot.testMode))
            send_message = MessageChain(["\n查询bangdream官方卡片信息"])
            send_message.add("\n可用参数:")
            send_message.add("\n-------------------------")
            send_message.add("\n同茨菇tsugu")
            await feedback(bot, message, send_message)
            return
        await sreachCard(bot, message, cardID)
    # 查角色
    elif raw_message[0:3] == "查角色":
        characterID = raw_message[3:].strip()
        if len(characterID) <= 0:
            log(f"查角色: 空参数", needPrint=(bot.testMode))
            send_message = MessageChain(["\n查询bangdream官方角色信息"])
            send_message.add("\n可用参数:")
            send_message.add("\n-------------------------")
            send_message.add("\n同茨菇tsugu")
            await feedback(bot, message, send_message)
            return
        await self_sreach_character(bot, message, characterID, be_at)
    # 卡池模拟
    elif raw_message[0:4] in ["卡池模拟", "抽卡模拟"]:
        command = raw_message[4:].strip()
        await self_gacha_simulate(bot, message, command, be_at)
    # == 活动 ==
    # 查试炼
    elif raw_message[0:3] == "查试炼":
        await self_event_stage(bot, message, raw_message, be_at)
    # 查活动
    elif raw_message[0:3] == "查活动":
        await self_search_event(bot, message, raw_message, be_at)
    # lsycx
    elif raw_message[0:5].lower() == "lsycx":
        await lsycx(bot, message, raw_message, be_at)
    # ycxall
    elif raw_message[0:6].lower() == "ycxall":
        await ycxall(bot, message, raw_message, be_at)
    # ycx
    elif raw_message[0:3].lower() == "ycx" or raw_message.lower() == "k":
        await self_ycx(bot, message, raw_message, be_at)
    # 分数表
    elif raw_message[0:3] == "分数表":
        server = raw_message[3:].strip()
        await self_song_meta(bot, message, server, be_at)
    # ycm - query_room_number
    elif raw_message.lower() == "ycm":
        await self_room_list(bot, message, raw_message, be_at)
    # 上传车牌
    elif raw_message[0:4] == "上传车牌":
        await self_submit_room_number(bot, message, raw_message, be_at)
    # help
    elif raw_message.lower() in ["bangdream", "tsugu", "茨菇"]:
        places_id = get_places_id(message)
        await help(bot, message, "tsugu", places_id)
    # 猜谱面
    elif "小生物积分" in get_plgin_registrated_list(message=message) and raw_message[0:2] in ["猜谱"]:
        raw_message = raw_message.replace("猜谱面", "猜谱")
        raw_message = raw_message[2:].strip()
        num = 0
        if len(raw_message)>0:
            if raw_message.isdigit():
                if int(raw_message) >0 and int(raw_message) <= 5:
                    num = int(raw_message)
        await guess_chart(bot, message, raw_message, be_at, num)
    elif raw_message!="" and get_places_id(message) in guess_char_list:
        await answer_guess_chart(bot, message, raw_message, be_at)
    # 猜卡面
    elif "小生物积分" in get_plgin_registrated_list(message=message) and raw_message[0:2] in ["猜卡"]:
        await guess_card(bot, message, raw_message, be_at)
    elif raw_message!="" and get_places_id(message) in guess_card_list:
        await answer_guess_card(bot, message, raw_message, be_at)

# == 谱面 ==
#查谱
async def sreachChart(bot, message, parameter):
    log(f"查谱: {parameter}", needPrint=(bot.testMode))
    try:
        log(f"尝试搜索自制谱", needPrint=(bot.testMode))
        charID = parameter
        if not charID.isdigit(): raise Exception()
        url = "https://bestdori.com/api/post/details?id=" + charID
        data = await call_net(url)
        if data == {}: 
            send = MessageChain(["\n小生物网络连接出现问题,请等下再试"])
            await feedback(bot, message, send)
            log(f"网络连接出现问题", needPrint=(bot.testMode))
            return
        log(f"Bestdori接口回复: {data}", needPrint=(bot.testMode))
        chartDetail = data["post"]
        await sonolus_chart(bot, message, chartDetail, charID)
        return
    except Exception as e:
        log(f"尝试搜索官谱", needPrint=(bot.testMode))
        parameters = parameter.split(" ")
        difficulty = parameters[-1]
        difficultyKeySet = {"ez":0, "nm":1, "hd":2, "ex":3, "sp":4}
        try: 
            difficulty = difficultyKeySet[difficulty]
            parameters = parameters[:-1]
        except: difficulty = 3
        await offical_chart(bot, message, parameters, difficulty)
        return
#自制
async def sonolus_chart(bot, msg, chartData, charID):
    log(f"开始解包谱面资料", needPrint=(bot.testMode))
    name = chartData["title"]
    log(f"谱面名称: {name}", needPrint=(bot.testMode))
    id = charID
    log(f"谱面ID: {id}", needPrint=(bot.testMode))
    difficult = ["EASY", "NORMAL", "HARD", "EXPERT", "SPECIAL"]
    difficult = difficult[chartData["diff"]]
    log(f"谱面难度: {difficult}", needPrint=(bot.testMode))
    level = chartData["level"]
    log(f"谱面等级: {difficult}", needPrint=(bot.testMode))
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
    log(f"谱面BPM: {bpm}", needPrint=(bot.testMode))
    count = n
    log(f"谱面物量: {count}", needPrint=(bot.testMode))
    if chartData["song"]["type"] == "bandori":
        try:
            charID = chartData["song"]["id"]
            song_url = "https://bestdori.com//api/songs/all.7.json"
            song_list = await call_net(song_url)
            duration = song_list[str(charID)]["length"]
            time: str = f"{duration//60:02.0f}:{duration%60:02.2f}"
        except:
            time = "官谱曲目时长识别失败"
    elif chartData["song"]["type"] == "custom":
        path = f"{music_temp_path}/{charID}.mp3"
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
    log(f"谱面时长: {time}", needPrint=(bot.testMode))
    server = "Bestdori"
    log(f"服务器: {server}", needPrint=(bot.testMode))
    owner = chartData["author"]["username"]
    log(f"谱师: {owner}", needPrint=(bot.testMode))
    like = chartData["likes"]
    log(f"谱面点赞数: {like}", needPrint=(bot.testMode))
    chart = chartData["chart"]
    log(f"开始构造信息链", needPrint=(bot.testMode))
    message = MessageChain(["\n", "谱面信息\n", "--------------------\n"])
    message.add(MessageChain([f"谱面名称:{name}\n"]))
    message.add(MessageChain([f"谱面ID:{id}\n"]))
    message.add(MessageChain([f"点赞数:{like}\n"]))
    message.add(MessageChain(["--------------------\n"]))
    message.add(MessageChain([f"谱面难度:{difficult}\n"]))
    message.add(MessageChain([f"谱面等级:{level}\n"]))
    message.add(MessageChain([f"谱师:{owner}\n"]))
    message.add(MessageChain(["--------------------\n"]))
    message.add(MessageChain([f"BPM:{bpm}\n"]))
    message.add(MessageChain([f"物量:{count}\n"]))
    message.add(MessageChain([f"时长:{time}\n"]))
    message.add(MessageChain(["--------------------\n"]))
    message.add(MessageChain([f"服务器:{server}\n"]))
    url = f"https://sonolus.bestdori.com/community/levels/bestdori-community-{id}"
    message.add(MessageChain([f"前去游玩:{url}\n"]))
    message.add(MessageChain(["--------------------\n"]))
    imageURL = await renderingChart(bot, charData= chart, charID= id, server= server, difficult= difficult)
    if imageURL == None: message.add("渲染失败")
    else: message.add(MessageChain([ImageMessage(f"file://{bot.localtion}/{imageURL}")]))
    await feedback(bot, msg, message)
#谱面渲染至图片 - bestdori-render
async def renderingChart(bot, charData: list, charID: str | int, server: str, difficult = "expert"):
    try:
        #渲染
        log(f"开始渲染", needPrint=(bot.testMode))
        image = render(charData)
        log(f"渲染成功", needPrint=(bot.testMode))
        if server == "Bandori":
            imageURL: str = f"data/classify/bangdream/char/{charID}-{difficult}.png"
        else:
            imageURL: str = f"data/classify/bangdream/char/{charID}.png"
        image.save(imageURL)
        log(f"文件已储存至: {imageURL}", needPrint=(bot.testMode))
        #返回文件地址
        return imageURL
    except Exception as e:
        log(f"渲染失败", needPrint=(bot.testMode))
        tb = e.__traceback__
        formatted_tb = ''.join(traceback.format_tb(tb))
        log(formatted_tb)
        return None
#官谱
async def offical_chart(bot, msg, parameters: list[str], difficulty: int):
    if not parameters[0].isdigit():
        log(f"检测到参数并非数字ID", needPrint=(bot.testMode))
        log(f"开始请求歌曲列表", needPrint=(bot.testMode))
        song_url = "https://bestdori.com//api/songs/all.7.json"
        song_list = await call_net(song_url)
        log(f"Bestdori接口回复: {song_list}", needPrint=(bot.testMode))
        log(f"正在使用歌名模式搜索", needPrint=(bot.testMode))
        result = await sreachFromNameMode(bot, song_list, parameters)
        log(f"搜索结果: {result}", needPrint=(bot.testMode))
        log(f"正在叠加难度过滤", needPrint=(bot.testMode))
        result = await filterFromDifficulty(bot, song_list, result, difficulty)
        log(f"搜索结果: {result}", needPrint=(bot.testMode))
        #处理结果
        if len(result) <= 0:
            log(f"搜索失败，正在使用条件式搜索", needPrint=(bot.testMode))
            result = await sreachFromFilterMode(bot, song_list, parameters)
            log(f"搜索结果: {result}", needPrint=(bot.testMode))
            log(f"正在叠加难度过滤", needPrint=(bot.testMode))
            result = await filterFromDifficulty(bot, song_list, result, difficulty)
            log(f"搜索结果: {result}", needPrint=(bot.testMode))
        log(f"结果总计: {len(result)}首", needPrint=(bot.testMode))
        if len(result) == 1:
            log(f"将向茨菇查询谱面图片", needPrint=(bot.testMode))
            charID = result[0]
            await get_offical_chart_image(bot, msg, charID, difficulty)
        else:
            log(f"将返回谱面列表", needPrint=(bot.testMode))
            message = MessageChain(["\n小生物查询结果为:"])
            if len(result) <= 0:
                message.add(MessageChain(["\n无"]))
            for songID in result:
                serverid = 0
                while song_list[songID]['musicTitle'][serverid] == None:
                    serverid += 1
                message.add(MessageChain([f"\n{songID}. {song_list[songID]['musicTitle'][serverid]}"]))
            await feedback(bot, msg, message)
        return
    #茨菇查谱
    log(f"将向茨菇查询谱面图片", needPrint=(bot.testMode))
    await get_offical_chart_image(bot, msg, parameters[0], difficulty)
    return
#谱面渲染至图片 - tsugu
async def get_offical_chart_image(bot, msg, charID, difficulty):
    mode = "songChart"
    bangdream_config = load_config("data/plugin/bangdream/config.yaml")
    datapack = {
        "displayedServerList": [3,0],
        "songId": charID,
        "difficultyId": difficulty,
        "compress": bangdream_config["compress"]
    }
    send_message = MessageChain([f"\nID: {charID}"])
    send_message.add(await call_tsugu(mode, datapack))
    await feedback(bot, msg, send_message)
#歌名模式搜索
async def sreachFromNameMode(bot, song_list, parameters: list[str]):
    result = []
    log(f"进入歌名搜索", needPrint=(bot.testMode))
    log(f"进行首轮过滤", needPrint=(bot.testMode))
    for id in song_list:
        for name in song_list[id]['musicTitle']:
            if name == None:
                continue
            if parameters[0].lower() in name.lower() and id not in result:
                result.append(id)
                break
    log(f"过滤结果: {result}", needPrint=(bot.testMode))
    log(f"进行第二轮过滤: {result}", needPrint=(bot.testMode))
    for parameter in parameters:
        temp = []
        for id in result:
            for name in song_list[id]['musicTitle']:
                if name == None:
                    continue
                if parameter.lower() in name.lower() and id not in temp:
                    temp.append(id)
        result = temp
    log(f"过滤结果: {result}", needPrint=(bot.testMode))
    if len(result) == 1: return result
    log(f"进入关键词搜索", needPrint=(bot.testMode))
    log(f"读入关键词本", needPrint=(bot.testMode))
    sreachKey = Config.load_from_file(key_set_path)
    log(f"进行过滤", needPrint=(bot.testMode))
    for key in sreachKey:
        for keyword in parameters:
            if keyword.lower() in key.lower() and sreachKey[key] not in result:
                result.extend(sreachKey[key])
    log(f"过滤结果: {result}", needPrint=(bot.testMode))
    return list(set(result))
#条件式搜索
async def sreachFromFilterMode(bot, song_list, parameters: list[str]):
    filters = list(parameters)
    filterResult = []
    log(f"正在填装歌曲ID", needPrint=(bot.testMode))
    for id in song_list:
        filterResult.append(id)
    log(f"进入曲目种类搜索", needPrint=(bot.testMode))
    log(f"进行首轮过滤", needPrint=(bot.testMode))
    types = ["原创", "动画", "翻唱", "covers", "cover"]
    songType = list(set(filters) & set(types))
    if len(songType)>0: 
        log(f"曲目种类搜索: {songType}", needPrint=(bot.testMode))
        filters.remove(songType[0])
        filterResult = list(set(await sreachByType(bot, song_list, filterResult, songType[0])) & set(filterResult))
    log(f"过滤结果: {filterResult}", needPrint=(bot.testMode))
    if len(filterResult) <= 1: return filterResult
    log(f"进入曲目等级搜索", needPrint=(bot.testMode))
    log(f"进行第二轮过滤", needPrint=(bot.testMode))
    for parameter in filters:
        if parameter[:2] == "lv" and parameter[2:].isdigit():
            level = int(parameter[2:])
            log(f"曲目等级搜索: {level}", needPrint=(bot.testMode))
            filters.remove(parameter)
            filterResult = list(set(await sreachByLevel(bot, song_list, filterResult, level)) & set(filterResult))
            break
    log(f"过滤结果: {filterResult}", needPrint=(bot.testMode))
    if len(filterResult) <= 1: return filterResult
    log(f"进入曲目物量搜索", needPrint=(bot.testMode))
    log(f"进行第三轮过滤", needPrint=(bot.testMode))
    for parameter in filters:
        if parameter[:2] == "物量":
            log(f"曲目物量搜索: {parameter[2:]}", needPrint=(bot.testMode))
            if "-" in parameter[2:]:
                notesRange = parameter[2:].split("-")
                if len(notesRange)>=2:
                    if notesRange[0].isdigit() and notesRange[1].isdigit():
                        notes1 = int(notesRange[0])
                        notes2 = int(notesRange[1])
                        filters.remove(parameter)
                        filterResult = list(set(await sreachByNotes(bot, song_list, filterResult, notes1, notes2)) & set(filterResult))
                        break
                elif len(notesRange)==1:
                    if notesRange[0].isdigit():
                        notes1 = 0
                        notes2 = int(notesRange[0])
                        filters.remove(parameter)
                        filterResult = list(set(await sreachByNotes(bot, song_list, filterResult, notes1, notes2)) & set(filterResult))
                        break
            elif "+" in parameter[2:]:
                notesRange = parameter[2:].split("+")
                if notesRange[0].isdigit() and len(notesRange) == 1:
                    notes1 = int(notesRange[0])
                    notes2 = 2147483647
                    filters.remove(parameter)
                    filterResult = list(set(await sreachByNotes(bot, song_list, filterResult, notes1, notes2)) & set(filterResult))
                    break
            elif parameter[2:].isdigit():
                notes = int(parameter[2:])
                filters.remove(parameter)
                filterResult = list(set(await sreachByNotes(bot, song_list, filterResult, notes)) & set(filterResult))
                break
    log(f"过滤结果: {filterResult}", needPrint=(bot.testMode))
    if len(filterResult) <= 1: return filterResult
    log(f"进入曲目BPM搜索", needPrint=(bot.testMode))
    log(f"进行第四轮过滤", needPrint=(bot.testMode))
    for parameter in filters:
        if parameter[:3].lower() == "bpm":
            log(f"曲目物量搜索: {parameter[3:]}", needPrint=(bot.testMode))
            if "-" in parameter[3:]:
                bpmRange = parameter[3:].split("-")
                if len(bpmRange) >= 2:
                    if bpmRange[0].isdigit() and bpmRange[1].isdigit():
                        bpm1 = int(bpmRange[0])
                        bpm2 = int(bpmRange[1])
                        filters.remove(parameter)
                        filterResult = list(set(await sreachByBPM(bot, song_list, filterResult, bpm1, bpm2)) & set(filterResult))
                        break
                elif len(bpmRange) == 1:
                    if bpmRange[0].isdigit():
                        bpm1 = 0
                        bpm2 = int(bpmRange[0])
                        filters.remove(parameter)
                        filterResult = list(set(await sreachByBPM(bot, song_list, filterResult, bpm1, bpm2)) & set(filterResult))
                        break
            elif "+" in parameter[3:]:
                bpmRange = parameter[3:].split("+")
                if bpmRange[0].isdigit() and len(bpmRange) == 1:
                    bpm1 = int(bpmRange[0])
                    bpm2 = 2147483647
                    filters.remove(parameter)
                    filterResult = list(set(await sreachByBPM(bot, song_list, filterResult, bpm1, bpm2)) & set(filterResult))
                    break
            elif parameter[3:].isdigit():
                bpm = int(parameter[3:])
                filters.remove(parameter)
                filterResult = list(set(await sreachByBPM(bot, song_list, filterResult, bpm)) & set(filterResult))
                break
    log(f"过滤结果: {filterResult}", needPrint=(bot.testMode))
    if len(filterResult) <= 1: return filterResult
    log(f"进入曲目乐团名称搜索", needPrint=(bot.testMode))
    log(f"进行第五轮过滤", needPrint=(bot.testMode))
    if len(filters) > 0:
        log(f"乐团名称搜索: {" ".join(filters)}", needPrint=(bot.testMode))
        filterResult = list(set(await sreachByBand(bot, song_list, filterResult, " ".join(filters))) & set(filterResult))
    log(f"过滤结果: {filterResult}", needPrint=(bot.testMode))
    return filterResult
#难度过滤
async def filterFromDifficulty(bot, song_list, id_list, difficulty):
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
async def sreachByType(bot, songList, filterResult, songType: str):
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
async def sreachByLevel(bot, songList, filterResult, level: int | str):
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
async def sreachByBand(bot, songList, filterResult, band: str):
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
    band_name_list = await call_net(band_url)
    #模糊匹配乐团信息，返回可能参数 (Band ID)
    for id in filterResult:
        for name in band_name_list[str(songList[id]["bandId"])]["bandName"]:
            if name != None:
                if band.lower() in name.lower() and id not in result:
                    result.append(id)
    return result
#条件式搜索 - 物量
async def sreachByNotes(bot, songList, filterResult, notes1: int | str, notes2: int | str = None):
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
async def sreachByBPM(bot, songList, filterResult, bpm1: int | str, bpm2: int | str = None):
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
async def randomSreachChart(bot, msg):
    song_url = "https://bestdori.com//api/songs/all.7.json"
    song_list = await call_net(song_url)
    id_set = list(song_list.keys())
    idx = random.randint(0, len(id_set)-1)
    song = song_list[id_set[idx]]
    difficulty_set = list(song["difficulty"].keys())
    idx = random.randint(0, len(difficulty_set)-1)
    difficulty = difficulty_set[idx]
    await offical_chart(bot, msg, [str(id_set[idx])], int(difficulty))
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
    sreachKey = Config.load_from_file(key_set_path)
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
    sreachKey.dump_to_file(key_set_path)
    message = MessageChain([f" 已为谱面ID [{id}] 新增关键词 {keySet} "])
    await feedback(bot, msg, message)
#茨菇查曲
async def returnSongInfo(bot, msg, charID: str):
    bangdream_config = load_config("data/plugin/bangdream/config.yaml")
    if charID.isdigit():
        datapack = {
            "displayedServerList": [3,0],
            "text": charID,
            "useEasyBG": bangdream_config["useEasyBG"],
            "compress": bangdream_config["compress"]
        }
    else:
        uri = f"{bangdream_config[bangdream_config["use_uri"]]}/fuzzySearch"
        datapack = {"text": charID}
        result = await call_net(uri, mode="post", data_pack=datapack)
        if result == {}:
            message = "\n茨菇连接失败"
            await feedback(bot, msg, message)
            return
        if result["status"] == "success":
            datapack = {
                "displayedServerList": [3,0],
                "fuzzySearchResult": result["data"],
                "useEasyBG": bangdream_config["useEasyBG"],
                "compress": bangdream_config["compress"]
            }
        else:
            message = "\n茨菇查询失败"
            await feedback(bot, msg, message)
            return
    mode = "searchSong"
    message = await call_tsugu(mode, datapack)
    await feedback(bot, msg, message)

# == 玩家 ==
#查玩家
async def check_player_info(bot, msg, raw_message, be_at):
    raw_message = raw_message[3:].strip()
    if len(raw_message) <= 0:
        log(f"查玩家: 空参数", needPrint=(bot.testMode))
        send_message = MessageChain(["\n查询玩家信息图片"])
        send_message.add("\n可用参数:")
        send_message.add("\n-------------------------")
        send_message.add("\n[ID] [server]")
        send_message.add("\n例:114514 jp")
        await feedback(bot, msg, send_message)
        return
    server = "cn"
    player_id = raw_message
    if raw_message[-2:].lower() in ["jp", "en", "tw", "cn", "kr"]:
        server = raw_message[-2:].lower()
        player_id = raw_message[:-2].strip()
    try:
        if not player_id.isdigit():
            message = MessageChain(["参数错误"])
            await feedback(bot, msg, message)
            return
        await self_search_player(bot, msg, player_id, server)
    except:
        message = MessageChain(["查询失败"])
        await feedback(bot, msg, message)
#茨菇查玩家
async def self_search_player(bot, msg, player_id, server):
    playerID = int(player_id)
    try:
        serverSet = {"jp":0, "en":1, "tw":2, "cn":3, "kr":4}
        server = serverSet[server]
    except: server = 3
    mode = "searchPlayer"
    bangdream_config = load_config("data/plugin/bangdream/config.yaml")
    datapack = {
        "playerId": playerID,
        "mainServer": server,
        "useEasyBG": bangdream_config["useEasyBG"],
        "compress": bangdream_config["compress"]
    }
    message = await call_tsugu(mode, datapack)
    await feedback(bot, msg, message)
#玩家状态
async def get_play_info(bot, msg, user_id, id):
    #读取玩家绑定记录
    users = Config.load_from_file(user_acc_path)
    try:
        user = users[str(user_id)][id]
    except:
        message = MessageChain(["无绑定记录"])
        await feedback(bot, msg, message)
        return
    #查玩家资料
    await self_search_player(bot, msg, user["acc"], user["server"])
    return
#绑定玩家
async def bing_user(bot, msg, raw_message, be_at):
    raw_message = raw_message[4:].strip()
    if len(raw_message) <= 0:
        log(f"绑定玩家: 空参数", needPrint=(bot.testMode))
        send_message = MessageChain(["\n绑定玩家信息"])
        send_message.add("\n可用参数:")
        send_message.add("\n-------------------------")
        send_message.add("\n[ID] [server]")
        send_message.add("\n例:114514 jp")
        await feedback(bot, msg, send_message)
        return
    player_id = raw_message.strip()
    server = "cn"
    if raw_message[-2:].lower() in ["jp", "en", "tw", "cn", "kr"]:
        server = raw_message[-2:].lower()
        player_id = raw_message[:-2].strip()
    try:
        if not player_id.isdigit():
            raise Exception()
        uri = f"https://bestdori.com/api/player/{server}/{player_id}"
        data = await call_net(uri)
        if data == {}:
            message = MessageChain(["\n小生物网络连接出现问题,请等下再试"])
            await feedback(bot, message, send)
            log(f"网络连接出现问题", needPrint=(bot.testMode))
        elif data["data"]["profile"] != None:
            #读取文件
            users = Config.load_from_file(user_acc_path)
            try:
                data = users[str(msg["sender"]["user_id"])]
            except:
                data = []
            #检查数据未绑定
            for savedData in data:
                if player_id == savedData["acc"] and server == savedData["server"]:
                    message = MessageChain(["账号已存在，请勿重复储存"])
                    await feedback(bot, msg, message)
                    return
            #更新
            data.append({"acc":player_id, "server": server})
            users[str(msg["sender"]["user_id"])]=data
            #写入文件
            users.dump_to_file("data/classify/bangdream/userBinding.json")
            #反馈
            message = MessageChain(["账号储存成功"])
            await feedback(bot, msg, message)
            await checkUserBinded(bot, msg)
            return
        else:
            await feedback(bot, msg, MessageChain(["账号不存在"]))
            log(data["data"])
    except:
        message = MessageChain(["参数错误"])
        await feedback(bot, msg, message)
#绑定记录
async def checkUserBinded(bot, msg):
    message = MessageChain(["\n"])
    try:
        message.add(MessageChain(["绑定记录:"]))
        users = Config.load_from_file(user_acc_path)
        user = users[str(msg["sender"]["user_id"])]
        for i in range(len(user)):
            message.add(MessageChain([f"\n{str(i+1)}. {user[i]['acc']} {user[i]['server']}"]))
    except Exception as e:
        message.add(MessageChain(["无绑定记录"]))
    await feedback(bot, msg, message)
#删除绑定
async def delUserBinded(bot, msg, raw_message, be_at):
    raw_message = raw_message[4:].strip()
    try:
        users = Config.load_from_file(user_acc_path)
        user = users[str(msg["sender"]["user_id"])]
        if raw_message == None:
            raise Exception()
        if not raw_message.isdigit() or raw_message=="0":
            raise Exception()
        if int(raw_message)<=len(user):
            user.remove(user[int(raw_message)-1])
            users.dump_to_file(user_acc_path)
            message = MessageChain(["账号删除成功"])
            await feedback(bot, msg, message)
            await checkUserBinded(bot, msg)
    except Exception as e:
        message = MessageChain(["参数错误"])
        await feedback(bot, msg, message)
        tb = e.__traceback__
        formatted_tb = ''.join(traceback.format_tb(tb))
        log(formatted_tb)

# == 卡片 ==
#查卡
async def sreachCard(bot, msg, cardID):
    bangdream_config = load_config("data/plugin/bangdream/config.yaml")
    if cardID.isdigit():
        datapack = {
            "displayedServerList": [3,0],
            "text": cardID,
            "useEasyBG": bangdream_config["useEasyBG"],
            "compress": bangdream_config["compress"]
        }
    else:
        uri = f"{bangdream_config[bangdream_config["use_uri"]]}/fuzzySearch"
        datapack = {"text": cardID}
        result = await call_net(uri, mode="post", data_pack=datapack)
        if result == {}:
            message = MessageChain(["\n茨菇后台连接失败"])
            await feedback(bot, msg, message)
            return
        if result["status"] == "success":
            datapack = {
                "displayedServerList": [3,0],
                "fuzzySearchResult": result["data"],
                "useEasyBG": bangdream_config["useEasyBG"],
                "compress": bangdream_config["compress"]
            }
        else:
            message = MessageChain(["\n茨菇后台连接失败"])
            await feedback(bot, msg, message)
            return
    mode = "searchCard"
    message = await call_tsugu(mode, datapack)
    await feedback(bot, msg, message)
#随机查卡
async def randomSreachCard(bot, msg):
    try:
        url = "https://bestdori.com/api/cards/all.0.json"
        data = await call_net(url)
        if data == {}: raise Excepton()
    except:
        message = MessageChain(["服务器网络连接出错"])
        await feedback(bot, msg, message)
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
        data = await call_net(url)
        if data == {}: raise Exception()
    except:
        message = MessageChain(["服务器网络连接出错"])
        await feedback(bot, msg, message)
        return
    index = list(data.keys())
    idx = random.randint(0, len(index)-1)
    cardID = index[idx]
    if cardID == "":
        return
    try:
        url = f"https://bestdori.com/api/cards/{cardID}.json"
        data = await call_net(url)
        if data == {}: raise Exception()
    except:
        message = MessageChain(["服务器网络连接出错"])
        await feedback(bot, msg, message)
        return
    train = False
    if data['rarity']>=3:
        if random.randint(1, 100) <= 50: train = True
        else: train = False
    message.add(ImageMessage(getImage(data,train)))
    await feedback(bot, msg, message)
#从bestdori拉取卡面图片
def getImage(data, train):
    res = data['resourceSetName']
    if train:
        image = f"https://bestdori.com/assets/jp/characters/resourceset/{res}_rip/card_after_training.png"
    else:
        image = f"https://bestdori.com/assets/jp/characters/resourceset/{res}_rip/card_normal.png"
    return image
#查卡池
async def self_search_gacha(bot, msg, gacha_id, be_at):
    bangdream_config = load_config("data/plugin/bangdream/config.yaml")
    mode = "searchGacha"
    datapack = {
        "displayedServerList": [3, 0],
        "gachaId": gacha_id,
        "useEasyBG": bangdream_config["useEasyBG"],
        "compress": bangdream_config["compress"]
    }
    message = await call_tsugu(mode, datapack)
    await feedback(bot, msg, message)
#卡池模拟
async def self_gacha_simulate(bot, msg, raw_message, be_at):
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
    bangdream_config = load_config("data/plugin/bangdream/config.yaml")
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
    message = await call_tsugu(mode, datapack)
    await feedback(bot, msg, message)
#查角色
async def self_sreach_character(bot, msg, characterID, be_at):
    bangdream_config = load_config("data/plugin/bangdream/config.yaml")
    if characterID.isdigit():
        datapack = {
            "displayedServerList": [3,0],
            "text": characterID,
            "compress": bangdream_config["compress"]
        }
    else:
        uri = f"{bangdream_config[bangdream_config["use_uri"]]}/fuzzySearch"
        datapack = {"text": characterID}
        result = await call_net(uri, mode="post", data_pack=datapack)
        if result == {}:
            message = "\n茨菇连接失败"
            await feedback(bot, msg, message)
            return
        if result["status"] == "success":
            datapack = {
                "displayedServerList": [3,0],
                "fuzzySearchResult": result["data"],
                "compress": bangdream_config["compress"]
            }
        else:
            message = "\n茨菇查询失败"
            await feedback(bot, msg, message)
            return
    mode = "searchCharacter"
    message = await call_tsugu(mode, datapack)
    await feedback(bot, msg, message)

# == 活动 ==
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
    mode = "eventStage"
    bangdream_config = load_config("data/plugin/bangdream/config.yaml")
    if event_id == None:
        datapack = {
            "mainServer": server,
            "meta": True,
            "compress": bangdream_config["compress"]
        }
    else:
        datapack = {
            "mainServer": server,
            "eventId": event_id,
            "meta": True,
            "compress": bangdream_config["compress"]
        }
    message = await call_tsugu(mode, datapack)
    await feedback(bot, msg, message)
#查活动
async def self_search_event(bot, msg, raw_message, be_at):
    raw_message = raw_message[3:].strip()
    if len(raw_message) <= 0:
        log(f"查活动: 空参数", needPrint=(bot.testMode))
        send_message = MessageChain(["\n查询bangdream活动信息"])
        send_message.add("\n可用参数:")
        send_message.add("\n-------------------------")
        send_message.add("\n同茨菇tsugu")
        await feedback(bot, msg, send_message)
        return
    bangdream_config = load_config("data/plugin/bangdream/config.yaml")
    if raw_message.isdigit():
        datapack = {
            "displayedServerList": [3, 0],
            "text": raw_message,
            "useEasyBG": bangdream_config["useEasyBG"],
            "compress": bangdream_config["compress"]
        }
    else:
        uri = f"{bangdream_config[bangdream_config["use_uri"]]}/fuzzySearch"
        datapack = {"text": raw_message}
        result = await call_net(uri, mode="post", data_pack=datapack)
        if result == {}:
            message = "\n茨菇连接失败"
            await feedback(bot, msg, message)
            return
        if result["status"] == "success":
            datapack = {
                "displayedServerList": [3,0],
                "fuzzySearchResult": result["data"],
                "useEasyBG": bangdream_config["useEasyBG"],
                "compress": bangdream_config["compress"]
            }
        else:
            message = "\n茨菇查询失败"
            await feedback(bot, msg, message)
            return
    mode = "searchEvent"
    message = await call_tsugu(mode, datapack)
    await feedback(bot, msg, message)
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
    bangdream_config = load_config("data/plugin/bangdream/config.yaml")
    if event_id == None:
        datapack = {
            "mainServer": server,
            "tier": tier,
            "compress": bangdream_config["compress"]
        }
    else:
        datapack = {
            "mainServer": server,
            "tier": tier,
            "eventId": event_id,
            "compress": bangdream_config["compress"]
        }
    mode = "cutoffListOfRecentEvent"
    message = await call_tsugu(mode, datapack)
    await feedback(bot, msg, message)
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
    bangdream_config = load_config("data/plugin/bangdream/config.yaml")
    if event_id == None:
        datapack = {
            "mainServer": server,
            "compress": bangdream_config["compress"]
        }
    else:
        datapack = {
            "mainServer": server,
            "eventId": event_id,
            "compress": bangdream_config["compress"]
        }
    mode = "cutoffAll"
    message = await call_tsugu(mode, datapack)
    await feedback(bot, msg, message)
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
    bangdream_config = load_config("data/plugin/bangdream/config.yaml")
    if event_id == None:
        datapack = {
            "mainServer": server,
            "tier": tier,
            "compress": bangdream_config["compress"]
        }
    else:
        datapack = {
            "mainServer": server,
            "tier": tier,
            "eventId": event_id,
            "compress": bangdream_config["compress"]
        }
    mode = "cutoffDetail"
    message = await call_tsugu(mode, datapack)
    await feedback(bot, msg, message)
#查询分数表
async def self_song_meta(bot, msg, server, be_at):
    try:
        serverSet = {"jp":0, "en":1, "tw":2, "cn":3, "kr":4}
        server = serverSet[server]
    except: server = 3
    bangdream_config = load_config("data/plugin/bangdream/config.yaml")
    datapack = {
        "displayedServerList": [3, 0],
        "mainServer": server,
        "compress": bangdream_config["compress"]
    }
    mode = "songMeta"
    message = await call_tsugu(mode, datapack)
    await feedback(bot, msg, message)

# == 多人 ==
#ycm
async def self_room_list(bot, msg, raw_message, be_at):
    try:
        bangdream_config = load_config("data/plugin/bangdream/config.yaml")
        uri = f"{bangdream_config[bangdream_config["use_uri"]]}/station/queryAllRoom"
        data = await call_net(uri)
        if data == {} or data["status"] != "success":
            message = MessageChain(["\n茨菇后台连接失败"])
            await feedback(bot, msg, message)
            return
        datapack = {
            "roomList": data["data"],
            "compress": bangdream_config["compress"]
        }
        mode = "roomList"
        message = await call_tsugu(mode, datapack)
        await feedback(bot, msg, message)
    except Exception as e:
        message = MessageChain(["\n茨菇后台连接失败"])
        await feedback(bot, msg, message)
        tb = e.__traceback__
        formatted_tb = ''.join(traceback.format_tb(tb))
        log(formatted_tb)
        return
#上传车牌
async def self_submit_room_number(bot, msg, raw_message, be_at):
    raw_message = raw_message[4:].strip()
    try:
        room_number = raw_message.split(" ")
        room_number = room_number[0]
        if (len(room_number) != 5 and len(room_number) != 6) or (not room_number.isdigit()):
            message = MessageChain(["房间号非法"])
            await feedback(bot, msg, message)
        raw_message = raw_message.replace(room_number, "").strip()
        datapack = {
            "number": room_number,
            "rawMessage": raw_message,
            "platform": "qq",
            "userId": msg["sender"]["user_id"],
            "userName": msg["sender"]["nickname"],
            "time": datetime.now().time()
        }
        bangdream_config = load_config("data/plugin/bangdream/config.yaml")
        uri = f"{bangdream_config[bangdream_config["use_uri"]]}/station/submitRoomNumber"
        result = await call_net(uri, mode="post", data_pack = datapack)
        if result['status'] == "success":
            message = MessageChain(["上传成功"])
            await feedback(bot, msg, message)
        else:
            message = MessageChain([f"上传失败,{result["data"]}"])
            await feedback(bot, msg, message)
    except:
        message = MessageChain(["\n茨菇后台连接失败"])
        await feedback(bot, msg, message)

# == 猜谱面 ==
#猜谱
async def guess_chart(bot, msg, raw_message, be_at, num = 0):
    if get_places_id(msg) in guess_char_list.keys() or get_places_id(msg) in guess_card_list.keys():
        message = MessageChain(["\n已有未完成的猜谱游戏，请先结束该游戏"])
        await feedback(bot, msg, message)
        return
    log(f"猜谱 - 请求歌曲列表", needPrint=(bot.testMode))
    song_url = "https://bestdori.com//api/songs/all.7.json"
    song_list = await call_net(song_url)
    log(f"歌曲列表[{len(song_list)}]: {song_list}", needPrint=(bot.testMode))
    log(f"过滤至只剩难度>=26", needPrint=(bot.testMode))
    temp = {}
    for song in song_list:
        for d in song_list[song]["difficulty"]:
            if song_list[song]["difficulty"][d]["playLevel"]>=26:
                temp[song] = song_list[song]
                break
    log(f"歌曲列表[{len(temp)}: {temp}", needPrint=(bot.testMode))
    idx = random.randint(0, len(temp)-1)
    charID = list(temp)[idx]
    log(f"随机目标: {charID}", needPrint=(bot.testMode))
    song = song_list[charID]
    d_list = list(song["difficulty"].keys())[3:]
    for d in d_list:
        if song["difficulty"][d]["playLevel"]<26:
            d_list.remove(d)
    d = d_list[random.randint(0, len(d_list)-1)]
    log(f"随机难度: {d}", needPrint=(bot.testMode))
    try:
        charID = int(charID)
        bangdream_config = load_config("data/plugin/bangdream/config.yaml")
        datapack = {
            "displayedServerList": [3,0],
            "songId": charID,
            "difficultyId": d,
            "compress": bangdream_config["compress"]
        }
        chart = await call_net(f"{bangdream_config[bangdream_config["use_uri"]]}/songChart", mode="post", data_pack=datapack)
        if chart[0]["type"] != "base64":
            raise SyntaxError()
        data = base64.b64decode(chart[0]["string"])
        im = Image.open(io.BytesIO(data))
        #图片切割
        image_list = await split_image(image_data=im, num=num, cut_left=True, vertical_segment=((735/2) * 3))
        if num == 0: score = 10
        else: score = 21 - (num*1)
        #
        message = MessageChain(["\n猜猜这是哪首歌的谱面？\n"])
        for i in range(len(image_list)):
            #保存图片
            imageURL: str = f"data/plugin/bangdream/char/guess_{i}.jpg"
            image_list[i].save(imageURL)
            #发送图片
            message.add(ImageMessage(f"file://{bot.localtion}/{imageURL}"))
        await feedback(bot, msg, message)
        package = {
            get_places_id(msg): {
                "charID": str(charID), 
                "difficulty": str(d), 
                "tips": 0, 
                "score": score, 
                "song_data": song, 
                "chart_img": chart[0]["string"]
            }
        }
        guess_char_list.update(package)
        log(package, needPrint=(bot.testMode))
    except Exception as e:
        message = MessageChain(["\n茨菇后台连接失败"])
        await feedback(bot, msg, message)
        tb = e.__traceback__
        formatted_tb = ''.join(traceback.format_tb(tb))
        log(formatted_tb)
#猜谱回答
async def answer_guess_chart(bot, msg, answer, be_at):
    places_id = get_places_id(msg)
    if places_id not in guess_char_list.keys():
        return
    if answer.strip() in ["bzd", "不知道"]:
        song = guess_char_list.pop(places_id)
        charID = song["charID"]
        song_name = None
        for name in song["song_data"]["musicTitle"]:
            if name != None:
                song_name = name
                break
        d_set = {"3": "expert", "4": "special"}
        message = MessageChain([f"\n已结束猜谱，正确答案为:\n{charID}. {song_name} [{d_set[song['difficulty']]}] [lv{song['song_data']['difficulty'][song['difficulty']]['playLevel']}]"])
        message.add(ImageMessage(f"base64://{song["chart_img"]}"))
        await feedback(bot, msg, message)
    elif answer.strip() in ["提示"]:
        tips_id = guess_char_list[places_id]["tips"]
        if tips_id <= 4 and guess_char_list[places_id]["score"] > 0:
            guess_char_list[places_id]["score"] = max(0, guess_char_list[places_id]["score"] - 2)
        #物量 - 2
        if tips_id == 0:
            notes = guess_char_list[places_id]["song_data"]["notes"][guess_char_list[places_id]["difficulty"]]
            low = (notes // 250) * 250
            high = low + 250
            message = MessageChain([f"\n提示{tips_id+1}：该谱面物量为 {low} - {high}"])
            await feedback(bot, msg, message)
            guess_char_list[places_id]["tips"] += 1
        #难度 - 2
        elif tips_id == 1:
            level = guess_char_list[places_id]["song_data"]["difficulty"][guess_char_list[places_id]["difficulty"]]
            message = MessageChain([f"\n提示{tips_id+1}：该谱面难度为 {level['playLevel']}"])
            await feedback(bot, msg, message)
            guess_char_list[places_id]["tips"] += 1
        #乐团 - 2
        elif tips_id == 2:
            band_id = guess_char_list[places_id]["song_data"]["bandId"]
            band_name = None
            band_url = "https://bestdori.com/api/bands/all.1.json"
            band_list = await call_net(band_url)
            for name in band_list[str(band_id)]["bandName"]:
                if name == None: continue
                band_name = name
                break
            message = MessageChain([f"\n提示{tips_id+1}：该谱面所属乐团为 {band_name}"])
            await feedback(bot, msg, message)
            guess_char_list[places_id]["tips"] += 1
        #BPM - 2
        elif tips_id == 3:
            bpm_data = guess_char_list[places_id]["song_data"]["bpm"][guess_char_list[places_id]["difficulty"]]
            if len(bpm_data) == 1:
                bpm = bpm_data[0]["bpm"]
                low = (bpm // 25) * 25
                high = low + 25
                message = MessageChain([f"\n提示{tips_id+1}：该谱面BPM为 {low} - {high}"])
            else:
                bpm1 = bpm_data[0]["bpm"]
                low = (bpm1 // 25) * 25
                bpm2 = bpm_data[-1]["bpm"]
                high = (bpm2 // 25) * 25 + 25
                message = MessageChain([f"\n提示{tips_id+1}：该谱面BPM为 {low} - {high}"])
            await feedback(bot, msg, message)
            guess_char_list[places_id]["tips"] += 1
        #曲目种类 - 2
        elif tips_id == 4:
            song_type = guess_char_list[places_id]["song_data"]["tag"]
            typeSet = {"normal":"原创", "anime":"动画", "tie_up":"翻唱"}
            message = MessageChain([f"\n提示{tips_id+1}：该谱面曲目种类为 {typeSet[song_type]}"])
            await feedback(bot, msg, message)
            guess_char_list[places_id]["tips"] += 1
        #提示用完
        else:
            message = MessageChain([f"\n提示次数已用完"])
            await feedback(bot, msg, message)
    elif answer.strip().isdigit():
        charID = guess_char_list[places_id]["charID"]
        if answer.strip() != charID:
            message = MessageChain(["猜错了"])
            await feedback(bot, msg, message)
            return
        song = guess_char_list.pop(places_id)
        song_name = None
        for name in song["song_data"]["musicTitle"]:
            if name == None:
                continue
            song_name = name
            break
        d_set = {"3": "expert", "4": "special"}
        message = MessageChain([f"\n回答正确！答案为:\n{charID}. {song_name} [{d_set[song['difficulty']]}] [lv{song['song_data']['difficulty'][song['difficulty']]['playLevel']}]\n"])
        message.add(MessageChain([f"获得积分: {song['score']} 分"]))
        message.add(ImageMessage(f"base64://{song["chart_img"]}"))
        await feedback(bot, msg, message)
        await add_scroes(bot, msg, score=song["score"], add_type="chart", get_card_p=20)
    else:
        charID = guess_char_list[places_id]["charID"]
        parameters = answer.split(" ")
        temp = []
        for p in parameters:
            if len(p.strip()) <= 1:
                continue
            temp.append(p.strip())
        parameters = temp
        if len(parameters) >= 1:
            song_url = "https://bestdori.com//api/songs/all.7.json"
            song_list = await call_net(song_url)
            result = sreachFromNameMode(song_list, parameters)
            if charID in result:
                song = guess_char_list.pop(places_id)
                song_name = None
                for name in song["song_data"]["musicTitle"]:
                    if name == None:
                        continue
                    song_name = name
                    break
                d_set = {"3": "expert", "4": "special"}
                message = MessageChain([f"\n回答正确！答案为:\n{charID}. {song_name} [{d_set[song['difficulty']]}] [lv{song['song_data']['difficulty'][song['difficulty']]['playLevel']}]\n"])
                message.add(MessageChain([f"获得积分: {song['score']} 分"]))
                message.add(ImageMessage(f"base64://{song["chart_img"]}"))
                await feedback(bot, msg, message)
                await add_scroes(bot, msg, score=song["score"], add_type="chart", get_card_p=20)
                return
        if be_at:
            message = MessageChain(["猜错了"])
            await feedback(bot, msg, message)

#猜卡面
async def guess_card(bot, msg, raw_message, be_at):
    if get_places_id(msg) in guess_char_list.keys() or get_places_id(msg) in guess_card_list.keys():
        message = MessageChain(["\n已有未完成的猜谱游戏，请先结束该游戏"])
        await feedback(bot, msg, message)
        return
    star = 3
    raw_message = raw_message.replace("猜卡面", "猜卡")
    raw_message = raw_message[2:].strip()
    if len(raw_message) > 0:
        if raw_message[-1] in ["*", "星"]:
            raw_message = raw_message[:1].strip()
        if raw_message.isdigit():
            star = int(raw_message) if (int(raw_message) >= 3 and int(raw_message) <= 5) else 3
    log(f"猜卡 - 请求卡面列表", needPrint=(bot.testMode))
    card_url = "https://bestdori.com/api/cards/all.5.json"
    card_list = await call_net(card_url)
    log(f"卡面列表[{len(card_list)}: {card_list}", needPrint=(bot.testMode))
    log(f"过滤至只剩>={star}星", needPrint=(bot.testMode))
    temp = []
    for id in card_list:
        if card_list[id]["rarity"] < star:
            continue
        temp.append(id)
    log(f"卡面列表[{len(temp)}: {temp}", needPrint=(bot.testMode))
    idx = random.randint(0, len(temp)-1)
    card_id = list(temp)[idx]
    log(f"随机目标: {card_id}", needPrint=(bot.testMode))
    #
    card = await call_net(f"https://bestdori.com/api/cards/{card_id}.json")
    character = await call_net(f"https://bestdori.com/api/characters/{card["characterId"]}.json")
    uri = getImage(card, True)
    #图片切割
    image_list = await split_image(image_uri=uri, num=1, piece = 4)
    score = 5
    #
    message = MessageChain(["\n猜猜这是谁的卡面？\n"])
    #保存图片
    imageURL: str = f"data/plugin/bangdream/card/guess.jpg"
    image_list[0].convert("RGB").save(imageURL, format="JPEG")
    #发送图片
    message.add(ImageMessage(f"file://{bot.localtion}/{imageURL}"))
    await feedback(bot, msg, message)
    #
    package = {
        get_places_id(msg):{
            "cardID": str(card_id),
            "cardName": list(filter(lambda x: x is not None, card["prefix"])),
            "characterID": str(card["characterId"]),
            "characterName": list(filter(lambda x: x is not None, character["characterName"])),
            "score": score,
            "cardURI": uri
        }
    }
    guess_card_list.update(package)
    log(package, needPrint=(bot.testMode))
#猜卡面回答
async def answer_guess_card(bot, msg, answer, be_at):
    places_id = get_places_id(msg)
    if places_id not in guess_card_list.keys():
        return
    if answer.strip() in ["bzd", "不知道"]:
        card = guess_card_list.pop(places_id)
        cardID = card["cardID"]
        cardName = card["cardName"][0]
        characterName = card["characterName"][0]
        message = MessageChain([f"\n已结束猜卡面，正确答案为:\n{characterName}\n{cardID}. {cardName}\n"])
        message.add(ImageMessage(card["cardURI"]))
        await feedback(bot, msg, message)
    elif answer.strip().isdigit():
        card = guess_card_list[places_id]
        if answer.strip() != card["cardID"]:
            message = MessageChain(["猜错了"])
            await feedback(bot, msg, message)
            return
        card = guess_card_list.pop(places_id)
        cardID = card["cardID"]
        cardName = card["cardName"][0]
        characterName = card["characterName"][0]
        message = MessageChain([f"\n回答正确！已结束猜卡面，正确答案为:\n{characterName}\n{cardID}. {cardName}\n"])
        message.add(MessageChain([f"获得积分: {card['score']} 分"]))
        message.add(ImageMessage(card["cardURI"]))
        await feedback(bot, msg, message)
        await add_scroes(bot, msg, score=card["score"], add_type="chart", get_card_p=10)
    else:
        card = guess_card_list[places_id]
        if answer.strip() in card["cardName"] or answer.strip() in card["characterName"]:
            card = guess_card_list.pop(places_id)
            cardID = card["cardID"]
            cardName = card["cardName"][0]
            characterName = card["characterName"][0]
            message = MessageChain([f"\n回答正确！已结束猜卡面，正确答案为:\n{characterName}\n{cardID}. {cardName}\n"])
            message.add(MessageChain([f"获得积分: {card['score']} 分"]))
            message.add(ImageMessage(card["cardURI"]))
            await feedback(bot, msg, message)
            await add_scroes(bot, msg, score=card["score"], add_type="chart")
            return
        uri = f"{bangdream_config[bangdream_config["use_uri"]]}/fuzzySearch"
        datapack = {"text": answer}
        result = await call_net(uri, mode="post", data_pack=datapack)
        if result == {}:
            message = MessageChain(["\n网络连接不好，请再尝试"])
            await feedback(bot, msg, message)
            return
        log(result["data"], needPrint=(bot.testMode))
        try:
            for c_id in result["data"]["characterId"]:
                if str(c_id) != card["characterID"]:
                    continue
                card = guess_card_list.pop(places_id)
                cardID = card["cardID"]
                cardName = card["cardName"][0]
                characterName = card["characterName"][0]
                message = MessageChain([f"\n回答正确！已结束猜卡面，正确答案为:\n{characterName}\n{cardID}. {cardName}\n"])
                message.add(MessageChain([f"获得积分: {card['score']} 分"]))
                message.add(ImageMessage(card["cardURI"]))
                await feedback(bot, msg, message)
                await add_scroes(bot, msg, score=card["score"], add_type="chart", get_card_p=10)
                return
        except: pass
        if be_at:
            message = MessageChain(["猜错了"])
            await feedback(bot, msg, message)
