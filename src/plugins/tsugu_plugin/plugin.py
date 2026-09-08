
# == Tsugu插件入口 ==

# 由v1(src/plugin/tsugu/main.py)迁移至v2插件格式
# 本文件仅负责指令路由，各功能按模块划分:
#   config(配置) / db(数据库) / call_tsugu(茨菇连接)
#   chart(谱面) / player(玩家) / card(卡片) / event(活动) / multi(多人)
#   guess(猜谱/猜卡) / order(快捷词)

import random, traceback
from OneBotConnecter.types import MessageChain
from OneBotConnecter.loger.log_info import log
from src.core.register import sreach_enabled_plugin
from src.plugins.tsugu_plugin.chart import sreachChart, offical_chart, randomSreachChart, add_key_word_for_song, returnSongInfo
from src.plugins.tsugu_plugin.player import check_player_info, get_play_info, bing_user, checkUserBinded, delUserBinded
from src.plugins.tsugu_plugin.card import card_face, sreachCard, randomSreachCard, randomGetCard, self_search_gacha, self_gacha_simulate, self_sreach_character
from src.plugins.tsugu_plugin.event import self_event_stage, self_search_event, lsycx, ycxall, self_ycx, self_song_meta
from src.plugins.tsugu_plugin.multi import self_room_list, self_submit_room_number
from src.plugins.tsugu_plugin.guess import guess_chart, answer_guess_chart, guess_card, answer_guess_card, guess_char_list, guess_card_list
from src.plugins.tsugu_plugin.order import add_order, read_order
from src.tools.reply_message import feedback

# == 入口 ==

def on_all_case(bot, message) -> bool: #call case including message, poke, request ...
    if "message" in message.event_type:
        return on_msg(bot, message=message)
    return False

def on_msg(bot, message) -> bool: # message
    try:
        return _handle(bot, message, message.text)
    except Exception as e:
        tb = e.__traceback__
        formatted_tb = ''.join(traceback.format_tb(tb))
        log(f"[TSUGU][{type(e)}] {e}\n{formatted_tb}")
    return False

def _handle(bot, message, raw_message: str, short_order = False) -> bool:
    if not raw_message: return False
    if raw_message[0:5].lower() in ["tsugu"]: raw_message = raw_message[5:]
    places_id = message.scene_id
    #触发快捷词
    if not short_order:
        target = read_order(str(message.user_id), raw_message)
        if target:
            return _handle(bot, message, target, short_order=True)
    #新增快捷词
    if raw_message[0:4] == "新增指令":
        raw_message = raw_message[4:].strip()
        order = raw_message.split(" ")
        send_message = MessageChain(["\n[TSUGU]未检测出指令/快捷词"])
        if len(order) < 1:
            feedback(message, send_message)
            return True
        if len(order[0]) < 1:
            feedback(message, send_message)
            return True
        order = order[0]
        target = raw_message[len(order):].strip()
        if len(target) <= 0:
            feedback(message, send_message)
            return True
        if add_order(str(message.user_id), order, target):
            feedback(message, MessageChain(["[TSUGU]绑定完成"]))
        else:
            feedback(message, MessageChain(["[TSUGU]禁止套娃"]))
        return True
    # == 谱面 ==
    # 查谱
    if raw_message[0:2] == "查谱":
        parameter = raw_message.replace("查谱面", "查谱")
        parameter = parameter[2:].strip()
        if len(parameter) <= 0:
            send_message = MessageChain(["\n[TSUGU]查询bangdream官方或bestdori sonolus社区谱面图片"])
            send_message.add("\n可用参数:")
            send_message.add("\n-------------------------")
            send_message.add("\n[(歌名/关键词/ID) 难度]")
            send_message.add("\n例:六兆年 sp")
            send_message.add("\n-------------------------")
            send_message.add("\n[(等级/乐团名称/歌曲种类/BPM/物量) 难度]")
            send_message.add("\n例:萝 lv27 翻唱 BPM100+ 物量500+ hd\n")
            feedback(message, send_message)
            return True
        sreachChart(bot, message, parameter)
        return True
    # 自制查谱
    elif raw_message[0:4] == "查自制谱":
        parameter = raw_message.replace("查自制谱面", "查自制谱")
        parameter = parameter[4:].strip()
        if len(parameter) <= 0:
            send_message = MessageChain(["\n[TSUGU]查询bestdori sonolus社区谱面图片"])
            send_message.add("\n可用参数:")
            send_message.add("\n-------------------------")
            send_message.add("\n[ID]")
            send_message.add("\n例:114514")
            feedback(message, send_message)
            return True
        try:
            charID = parameter
            if not charID.isdigit(): raise Exception()
            from src.plugins.tsugu_plugin.chart import sonolus_chart
            from src.plugins.tsugu_plugin.call_tsugu import call_net
            url = "https://bestdori.com/api/post/details?id=" + charID
            data = call_net(url)
            if data == {}:
                send = MessageChain(["\n[TSUGU]小生物网络连接出现问题,请等下再试"])
                feedback(message, send)
                log(f"网络连接出现问题")
                return True
            log(f"Bestdori接口回复: {data}")
            chartDetail = data["post"]
            sonolus_chart(bot, message, chartDetail, charID)
            return True
        except Exception as e:
            tb = e.__traceback__
            formatted_tb = ''.join(traceback.format_tb(tb))
            log(f"[{type(e)}] {e}\n{formatted_tb}")
            send = MessageChain(["[TSUGU]自制谱面ID参数错误"])
            feedback(message, send)
            return True
    # 查官谱
    elif raw_message[0:3] == "查官谱":
        parameter = raw_message.replace("查官谱面", "查官谱")
        command = parameter[3:].strip()
        if len(command) <= 0:
            send_message = MessageChain(["\n[TSUGU]查询bangdream官方谱面图片"])
            send_message.add("\n可用参数:")
            send_message.add("\n-------------------------")
            send_message.add("\n[(歌名/关键词/ID) 难度]")
            send_message.add("\n例:六兆年 sp")
            send_message.add("\n-------------------------")
            send_message.add("\n[(等级/乐团名称/歌曲种类/BPM/物量) 难度]")
            send_message.add("\n例:萝 lv27 翻唱 BPM100+ 物量500+ hd\n")
            feedback(message, send_message)
            return True
        parameters = command.split(" ")
        difficulty = parameters[-1].lower()
        difficultyKeySet = {"ez":0, "nm":1, "hd":2, "ex":3, "sp":4, "easy":0, "normal":1, "hard":2, "expert":3, "special":4}
        try:
            difficulty = difficultyKeySet[difficulty]
            parameters = parameters[:-1]
        except: difficulty = 3
        offical_chart(bot, message, parameters, difficulty)
        return True
    # 随机查谱
    elif raw_message in ["随机查谱", "随机谱面"]:
        randomSreachChart(bot, message)
        return True
    # 新增搜索词
    elif raw_message[:5] == "新增搜索词":
        add_key_word_for_song(bot, message, raw_message)
        return True
    # 查曲
    elif raw_message[0:2] == "查曲":
        songID = raw_message[2:].strip()
        if len(songID) <= 0:
            send_message = MessageChain(["\n[TSUGU]查询bangdream官方歌曲信息"])
            send_message.add("\n可用参数:")
            send_message.add("\n-------------------------")
            send_message.add("\n同茨菇tsugu")
            feedback(message, send_message)
            return True
        returnSongInfo(bot, message, songID)
        return True
    # == 玩家 ==
    #查玩家
    elif raw_message[0:3] == "查玩家":
        check_player_info(bot, message, raw_message)
        return True
    # 绑定玩家
    elif raw_message[0:4] == "绑定玩家":
        bing_user(bot, message, raw_message)
        return True
    # 绑定记录
    elif raw_message[0:4] == "绑定记录":
        checkUserBinded(bot, message)
        return True
    # 删除绑定
    elif raw_message[0:4] == "删除绑定":
        delUserBinded(bot, message, raw_message)
        return True
    # 玩家状态
    elif raw_message[0:4] == "玩家状态":
        raw_message = raw_message[4:].strip()
        id = 0
        if len(raw_message) > 0:
            if raw_message.isdigit():
                if int(raw_message) > 0:
                    id = int(raw_message)-1
        get_play_info(bot, message, str(message.user_id), id)
        return True
    # 逮捕
    elif raw_message[0:2] == "逮捕" and message.event_type == "group_message":
        raw_message = raw_message[2:].strip()
        targetID = None
        for i in message.message:
            if i.type == "at":
                targetID = str(i.data.qq)
                break
            elif i.type == "reply":
                msg_id = i.data.id
                reply_msg = bot.get_msg(msg_id)
                try:
                    targetID = str(reply_msg.data.sender.user_id)
                except: pass
                break
        if not targetID:
            send_message = MessageChain(["\n[TSUGU]查询群友的玩家信息"])
            send_message.add("\n可用参数:")
            send_message.add("\n-------------------------")
            send_message.add("\n[艾特/回复]")
            send_message.add("\n例:@群主")
            feedback(message, send_message)
            return True
        get_play_info(bot, message, targetID, 0)
        return True
    # == 卡片 ==
    # 查卡面
    elif raw_message[0:3] == "查卡面":
        cardID = raw_message[3:].strip()
        if len(cardID) <= 0:
            send_message = MessageChain(["\n[TSUGU]查询bangdream官方卡面图片"])
            send_message.add("\n可用参数:")
            send_message.add("\n-------------------------")
            send_message.add("\n同茨菇tsugu")
            feedback(message, send_message)
            return True
        if cardID.isdigit() == True:
            card_face(bot, message, cardID)
        return True
    # 随机查卡
    elif raw_message == "随机查卡":
        randomSreachCard(bot, message)
        return True
    # 随机卡面
    elif raw_message == "随机卡面":
        randomGetCard(bot, message)
        return True
    # 查卡池 - search_gacha - serverlist, id
    elif raw_message[0:3] == "查卡池":
        raw_message = raw_message[3:].strip()
        if len(raw_message) <= 0 or not raw_message.isdigit():
            send_message = MessageChain(["\n[TSUGU]查询bangdream官方卡池信息"])
            send_message.add("\n可用参数:")
            send_message.add("\n-------------------------")
            send_message.add("\n同茨菇tsugu")
            feedback(message, send_message)
            return True
        self_search_gacha(bot, message, raw_message)
        return True
    # 查卡
    elif raw_message[0:2] == "查卡":
        cardID = raw_message[2:].strip()
        if len(cardID) <= 0:
            send_message = MessageChain(["\n[TSUGU]查询bangdream官方卡片信息"])
            send_message.add("\n可用参数:")
            send_message.add("\n-------------------------")
            send_message.add("\n同茨菇tsugu")
            feedback(message, send_message)
            return True
        if random.randint(1,100) > 50 and str(cardID) == "947":
                send = MessageChain(["[TSUGU]不许查!!!"])
                feedback(message, send)
                return True
        sreachCard(bot, message, cardID)
        return True
    # 查角色
    elif raw_message[0:3] == "查角色":
        characterID = raw_message[3:].strip()
        if len(characterID) <= 0:
            send_message = MessageChain(["\n[TSUGU]查询bangdream官方角色信息"])
            send_message.add("\n可用参数:")
            send_message.add("\n-------------------------")
            send_message.add("\n同茨菇tsugu")
            feedback(message, send_message)
            return True
        self_sreach_character(bot, message, characterID)
        return True
    # 卡池模拟
    elif raw_message[0:4] in ["卡池模拟", "抽卡模拟"]:
        command = raw_message[4:].strip()
        self_gacha_simulate(bot, message, command)
        return True
    # == 活动 ==
    # 查试炼
    elif raw_message[0:3] == "查试炼":
        self_event_stage(bot, message, raw_message)
        return True
    # 查活动
    elif raw_message[0:3] == "查活动":
        self_search_event(bot, message, raw_message)
        return True
    # lsycx
    elif raw_message[0:5].lower() == "lsycx":
        lsycx(bot, message, raw_message)
        return True
    # ycxall
    elif raw_message[0:6].lower() == "ycxall":
        ycxall(bot, message, raw_message)
        return True
    # ycx
    elif raw_message[0:3].lower() == "ycx" or raw_message.lower() == "k":
        self_ycx(bot, message, raw_message)
        return True
    # 分数表
    elif raw_message[0:3] == "分数表":
        server = raw_message[3:].strip()
        self_song_meta(bot, message, server)
        return True
    # ycm - query_room_number
    elif raw_message.lower() == "ycm":
        self_room_list(bot, message)
        return True
    # 上传车牌
    elif raw_message[0:4] == "上传车牌":
        self_submit_room_number(bot, message, raw_message)
        return True
    # 猜谱面
    elif "小生物积分" in sreach_enabled_plugin(places_id) and raw_message[0:2] in ["猜谱"]:
        raw_message = raw_message.replace("猜谱面", "猜谱")
        raw_message = raw_message[2:].strip()
        num = 0
        if len(raw_message)>0:
            if raw_message.isdigit():
                if int(raw_message) >0 and int(raw_message) <= 5:
                    num = int(raw_message)
        guess_chart(bot, message, raw_message, num)
        return True
    elif raw_message!="" and places_id in guess_char_list():
        answer_guess_chart(bot, message, raw_message)
        return True
    # 猜卡面
    elif "小生物积分" in sreach_enabled_plugin(places_id) and raw_message[0:2] in ["猜卡"]:
        guess_card(bot, message, raw_message)
        return True
    elif raw_message!="" and places_id in guess_card_list():
        answer_guess_card(bot, message, raw_message)
        return True
    return False
