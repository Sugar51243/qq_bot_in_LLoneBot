import os
try:
    from OneBotConnecter.MessageType import MessageChain, ImageMessage
except:
    os.system("pip install OneBotConnecter")
    exec("from OneBotConnecter.MessageType import MessageChain, ImageMessage")
lib_list = ["asyncio", "re", "random", "traceback", "time"]
for lib in lib_list:
    try:
        exec(f"import {lib}")
    except:
        os.system(f"pip install {lib}")
        exec(f"import {lib}")
try:
    from config_io import Config
except:
    os.system(f"pip install {config-io}")
    exec(f"from config_io import Config")
from datetime import datetime
plugin_folders = os.listdir("src/classify")
#dynamically import all handler modules in src.classify
for folder in plugin_folders:
    exec(f"from src.classify.{folder}.{folder}Handler import {folder}Mode")


user_lock = []
waiting_group_request = {}
waiting_friend_request = {}

#确认信息是否被艾特或回复
async def beAt(bot, message):
    raw_message = message["raw_message"] #信息原数据
    be_at = False #暂存
    #艾特信息
    #结构为: [CQ:at,qq={QQID}]
    if f"[CQ:at,qq={bot.botAcc}," in raw_message:
        idx = raw_message.find(f"[CQ:at,qq={bot.botAcc},")
        temp = raw_message[idx:]
        idx = temp.find("]")
        temp = temp[:idx+1]
        raw_message = raw_message.replace(temp,"").strip()
        be_at = True
    #结构为: @{QQID} | robotName
    allowedAt = [f"@{bot.botAcc}"] #QQID
    allowedAt.extend(bot.botName) #robotName
    for allowAt in allowedAt:
        if f"@{allowAt}" in raw_message:
            raw_message = raw_message.replace(f"@{allowAt}","").strip()
            be_at = True
        if allowAt in raw_message:
            raw_message = raw_message.replace(allowAt,"").strip()
            be_at = True
    #结构为: 小号 且 机械主
    allowedAt = [f"@小号", "小号"]
    for allowAt in allowedAt:
        if (allowAt in raw_message) and str(message["sender"]["user_id"]) in bot.owner:
            raw_message = raw_message.replace(allowAt,"").strip()
            be_at = True
    #回复信息
    #结构为: [CQ:reply,qq={信息ID}]
    if "[CQ:reply,id=" in raw_message and "]" in raw_message:
        #从结构中取出 信息ID
        idx = raw_message.find("[CQ:reply,id=")
        relpy_id = raw_message[idx+13:]
        idx = relpy_id.find("]")
        relpy_id = relpy_id[:idx]
        #取得 信息并确实发送者
        replyed_msg = await bot.get_msg(relpy_id)
        if replyed_msg["data"]["sender"]["user_id"] == bot.botAcc:
            raw_message = raw_message.replace(f"[CQ:reply,id={relpy_id}]","").strip()
            be_at = True
    if len(raw_message)<1:
        raw_message = f"blankmsg,id:{message["message_id"]}"
    #返回已处理信息及艾特状态
    return [raw_message, be_at]

#
def identifyMsgType(message):
    msgType: str
    try:
        groupID = message["group_id"]
        msgType = "Group_"
    except: msgType = "Private_"
    match (message["post_type"]):
        case "message":
            msgType += "message"
        case "notice":
            if message["notice_type"] == "notify":
                if message["sub_type"] == "poke":
                    msgType += "poke"
            elif message["notice_type"] == "group_recall" or message["notice_type"] == "friend_recall":
                msgType += "recall"
            elif message["notice_type"] == "group_admin":
                if message["sub_type"] == "set":
                    msgType += "setAdmin"
                elif message["sub_type"] == "unset":
                    msgType += "unsetAdmin"
            elif message["notice_type"] == "group_ban":
                if message["sub_type"] == "ban":
                    msgType += "ban"
                elif message["sub_type"] == "lift_ban":
                    msgType += "liftBan"
            elif message["notice_type"] == "group_msg_emoji_like":
                msgType += "msg_emoji_like"
            else:
                print(message["notice_type"])
        case "request":
            msgType += "request"
        case "message_sent":
            msgType += "message"
        case _:
            print(message["post_type"])
    return msgType

#
def consleLog(message, msgType):
    current_time = datetime.now()
    output = f"[{current_time}]:[{msgType}]\n"
    match (msgType):
        case "Group_message":
            group_id = message["group_id"]
            user_id = message["user_id"]
            user_nickname = message["sender"]["nickname"]
            raw_message = message["message"]
            message_id = message["message_id"]
            output += f"--[{group_id}]{user_nickname}[{user_id}]:[{message_id}]\n"
            output += f"{raw_message}"
        case "Group_recall":
            group_id = message["group_id"]
            user_id = message["user_id"]
            message_id = message["message_id"]
            output += f"--[{group_id}]{user_id}撤回了信息:"
            output += f"{message_id}"
        case "Group_poke":
            group_id = message["group_id"]
            user_id = message["user_id"]
            target_id = message["target_id"]
            output += f"--[{group_id}]{user_id}戳了戳:"
            output += f"{target_id}"
        case "Private_message":
            user_id = message["user_id"]
            user_nickname = message["sender"]["nickname"]
            raw_message = message["message"]
            message_id = message["message_id"]
            output += f"--{user_nickname}[{user_id}]:[{message_id}]\n"
            output += f"{raw_message}"
        case "Private_recall":
            user_id = message["user_id"]
            message_id = message["message_id"]
            output += f"--{user_id}撤回了信息:"
            output += f"{message_id}"
        case "Private_poke":
            user_id = message["user_id"]
            output += f"--{user_id}戳了戳:"
            output += "你"
        case "Group_setAdmin":
            group_id = message["group_id"]
            user_id = message["user_id"]
            output += f"--[{group_id}]{user_id}被设置为管理员"
        case "Group_unsetAdmin":
            group_id = message["group_id"]
            user_id = message["user_id"]
            output += f"--[{group_id}]{user_id}被取消管理员资格"
        case "Group_ban":
            group_id = message["group_id"]
            user_id = message["user_id"]
            duration = message["duration"]
            output += f"--[{group_id}]{user_id}被禁言了{duration}秒"
        case "Group_liftBan":
            group_id = message["group_id"]
            user_id = message["user_id"]
            output += f"--[{group_id}]{user_id}被解除禁言"
        case _:
            output += str(message)
    print(f"{output}\n")

#
def readPermissions(message):
    group_id = str(message["group_id"])
    try: 
        permissions = Config.load_from_file("data/permissions.yaml")
        permissions = permissions[group_id]
        if permissions == None: raise Exception()
    except: 
        try: permissions = Config.load_from_file("data/permissions.yaml")
        except: permissions = Config()
        permissions[group_id] = ["general"]
        permissions.dump_to_file("data/permissions.yaml")
        permissions = ["general"]
    return permissions

#
async def handleGroupMessage(bot, message, raw_message, be_at):
    try:
        #取得发送群已注册的指令种类 或 注册基础通用种类功能
        permissions = readPermissions(message)
        #按种类处理信息
        for permission in permissions:
            func_name = f"{permission}Mode"
            func = globals().get(func_name)
            if func is None:
                print(f"[Error] 未找到指令种类处理函数: {func_name}")
                continue
            try:
                result = func(bot, message, raw_message, be_at)
                if asyncio.iscoroutine(result):
                    await result
            except: traceback.print_exc()
    except: traceback.print_exc()
#
async def handleMessage(bot, message, msgType):
    #process timer
    start_time = datetime.now()
    try:
        #黑名单群屏蔽
        if "Group" in msgType:
            config = Config.load_from_file("data/config.yaml")
            backlist = config["backlist"]
            if str(message["group_id"]) in backlist:
                return
        #处理群消息
        if msgType == "Group_message":
            [raw_message, be_at] = await beAt(bot, message)
            #测试指令
            if raw_message.lower() == "test" and be_at:
                img = ImageMessage(f"file://{bot.location}/data/image/botStatus/botStatus.gif")
                msg = MessageChain(["我在~\n", img])
                callback = await bot.reply_to_message(message, msg)
                return
            elif raw_message[-3:] == "out" and (str(message["sender"]["user_id"]) in bot.owner or str(message["sender"]["user_id"]) in user_lock):
                removed = []
                for ms in message["message"]:
                    if ms["type"] == "at":
                        target = ms["data"]["qq"]
                        if str(target) in user_lock:
                            user_lock.remove(str(target))
                            removed.append(target)
                if len(removed)>0:
                    msg = MessageChain([f"已解除{removed}的锁定"])
                    await bot.reply_to_message(message, msg)
                    return
            #用户锁，防止多线程炸机
            if message["sender"]["user_id"] in user_lock:
                if be_at:
                    await bot.reply_to_message(message, MessageChain(["别炸我机了，我处理不过来辣"]))
                return
            user_lock.append(str(message["sender"]["user_id"]))
            #处理群消息
            try:
                await asyncio.wait_for(handleGroupMessage(bot, message, raw_message, be_at), timeout=10)
            except asyncio.TimeoutError:
                pass
            #释放用户锁
            user_lock.remove(str(message["sender"]["user_id"]))
        #处理群戳一戳
        elif msgType == "Group_poke":
            if message['target_id'] == bot.botAcc:
                await onPoke(bot, message)
        #处理私聊消息
        elif msgType == "Private_message":
            pass
        #处理群管理员变更通知
        elif msgType == "Group_setAdmin":
            if str(message["user_id"]) in bot.owner:
                msg = MessageChain(["恭喜主人成为管理员！(●'◡'●)"])
                await bot.send_group_msg(message["group_id"], msg)
            elif str(message["user_id"]) == str(bot.botAcc):
                msg = MessageChain(["谢谢群主设置的管理员！o( ❛ᴗ❛ )o︎"])
                await bot.send_group_msg(message["group_id"], msg)
        #处理群管理员变更通知
        elif msgType == "Group_unsetAdmin":
            if str(message["user_id"]) == str(bot.botAcc):
                msg = MessageChain(["管理员资格被取消了(。>︿<)"])
                await bot.send_group_msg(message["group_id"], msg)
        #处理ban通知
        elif msgType == "Group_ban":
            pass
        #处理ban通知
        elif msgType == "Group_liftBan":
            if str(message["user_id"]) == str(bot.botAcc):
                msg = MessageChain(["谢谢解禁我(●'◡'●)"])
                await bot.send_group_msg(message["group_id"], msg)
        #处理表情点赞通知
        elif msgType == "Group_msg_emoji_like":
            pass
        #处理加群请求
        elif msgType == "Group_request":
            try:
                try:
                    friendsList = await bot.get_friend_list()
                    for friend in friendsList["data"]:
                        if friend["user_id"] == message["user_id"]:
                            await bot.set_group_add_request(flag=message['flag']) 
                            await bot.send_private_msg(bot.owner[0], MessageChain([f"自动通过了来自[{message['user_id']}]的加群[{message['group_id']}]请求，附言：{message['comment']}"]))
                            return
                except: pass
                await bot.send_private_msg(bot.owner[0], MessageChain([f"收到来自[{message['user_id']}]的加群[{message['group_id']}]请求，附言：{message['comment']}"]))
            except: pass
            """
            waiting_group_request[message['group_id']] = message['flag']
            msg = MessageChain(["正在等候的加群请求:\n"])
            keys = waiting_group_request.keys()
            for num in len(keys):
                msg.append(f"{num}. {keys[num]}\n")
            await bot.send_private_msg(bot.owner[0], msg)
            """
        #处理加好友请求
        elif msgType == "Private_request":
            try:
                await bot.send_private_msg(bot.owner[0], MessageChain([f"收到来自[{message['user_id']}]的好友请求，附言：{message['comment']}"]))
            except: pass
            """
            waiting_friend_request[message['user_id']] = message['flag']
            msg = MessageChain(["正在等候的加好友请求:\n"])
            keys = waiting_friend_request.keys()
            for num in len(keys):
                msg.append(f"{num}. {keys[num]}\n")
            await bot.send_private_msg(bot.owner[0], msg)
            """
    except Exception as e: 
        traceback.print_exc()
        print("")
    #process timer end
    end_time = datetime.now()
    #log execution time in test mode
    if bot.testMode:
        endTimeStr = end_time.strftime(format="%Y-%m-%d %H:%M:%S")
        print(f"[{endTimeStr}] [Group Message Handler]: 指令执行时长为: [{end_time-start_time}]")

#
async def onMessage(bot, message):
    msgType = identifyMsgType(message)
    if bot.testMode == True:
        print(message)
    consleLog(message, msgType)
    await handleMessage(bot, message, msgType)

async def onPoke(bot, msg):
    event = 18
    idx = random.randint(0, event)
    if idx == 0:
        message = MessageChain(["戳我干嘛(#`O′)"])
        await bot.send_group_msg(msg["group_id"], message)
        return
    if idx == 1:
        message = MessageChain(["别戳我(。>︿<)"])
        await bot.send_group_msg(msg["group_id"], message)
        return
    if idx == 2:
        message = MessageChain(["(｡･ˇ_ˇ･｡:)"])
        await bot.send_group_msg(msg["group_id"], message)
        return
    if idx == 3:
        message = MessageChain(["咬死你＼(`Δ’)／"])
        await bot.send_group_msg(msg["group_id"], message)
        return
    if idx == 4:
        message = MessageChain(["你知道我的真身是什么吗？(●'◡'●)"])
        await bot.send_group_msg(msg["group_id"], message)
        time.sleep(1.5)
        await bot.group_poke(msg['group_id'], msg['user_id'])
        message = MessageChain(["其实是广东双马尾o( ❛ᴗ❛ )o︎"])
        await bot.send_group_msg(msg["group_id"], message)
        return
    if idx == 5:
        message = MessageChain(["_(:зゝ∠)_"])
        await bot.send_group_msg(msg["group_id"], message)
        return
    if idx == 6:
        message = MessageChain(["老子戳回来！(｀へ´*)"])
        await bot.send_group_msg(msg["group_id"], message)
        await bot.group_poke(msg['group_id'], msg['user_id'])
        return
    if idx == 6:
        message = MessageChain(["老子戳回来！(｀へ´*)"])
        await bot.send_group_msg(msg["group_id"], message)
        await bot.group_poke(msg['group_id'], msg['user_id'])
        return
    if idx == 7:
        message = MessageChain(["无不无聊？＼(`Δ’)／"])
        await bot.send_group_msg(msg["group_id"], message)
        return
    if idx == 8:
        message = MessageChain(["再戳我睡了..."])
        await bot.send_group_msg(msg["group_id"], message)
        return
    if idx == 9:
        message = MessageChain(["睡了(｀へ´*)"])
        await bot.send_group_msg(msg["group_id"], message)
        return
    if idx == 10:
        message = MessageChain(["艹！"])
        await bot.send_group_msg(msg["group_id"], message)
        return
    if idx == 11:
        for i in range(3):
            await bot.group_poke(msg['group_id'], msg['user_id'])
            time.sleep(5)
        message = MessageChain(["爽了？"])
        await bot.send_group_msg(msg["group_id"], message)
        return
    if idx == 12:
        return
    if idx == 13:
        message = MessageChain(["你干嘛戳我？"])
        await bot.send_group_msg(msg["group_id"], message)
        return
    if idx == 14:
        message = MessageChain(["戳你麻痹！"])
        await bot.send_group_msg(msg["group_id"], message)
        return
    if idx == 15:
        message = MessageChain(["再戳试试？"])
        await bot.send_group_msg(msg["group_id"], message)
        return
    if idx == 16:
        message = MessageChain(["你有完没完？"])
        await bot.send_group_msg(msg["group_id"], message)
        return
    if idx == 17:
        message = MessageChain(["别戳了，烦死了！"])
        await bot.send_group_msg(msg["group_id"], message)
        return
    if idx == 18:
        message = MessageChain(["戳死你！"])
        await bot.send_group_msg(msg["group_id"], message)
        for i in range(3):
            await bot.group_poke(msg['group_id'], msg['user_id'])
            time.sleep(5)
        return
