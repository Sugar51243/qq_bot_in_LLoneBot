
# == 信息处理文件 ==

#此文件为OneBot11-小生物的信息处理涵数文件
#应用环境为LL-Bot v2.4.4

#如果不清楚具体作用，除配置外，请不要修改任何参数代码


#引用库
#  ==> pip自动下载缺失的库
import os
try: from OneBotConnecter.MessageType import MessageChain, ImageMessage, AtMessage
except:
    os.system("pip install OneBotConnecter")
    exec("from OneBotConnecter.MessageType import MessageChain, ImageMessage", "AtMessage")
try: import asyncio, re, random, traceback, time
except:
    lib_list = ["asyncio", "re", "random", "traceback", "time"]
    for lib in lib_list:
        try:
            exec(f"import {lib}")
        except:
            os.system(f"pip install {lib}")
            exec(f"import {lib}")
try: from config_io import Config
except:
    os.system(f"pip install config-io")
    exec(f"from config_io import Config")
from datetime import datetime
from src.loger import log
#自动加载插件文件夹下的所有文件
plugin_folders = os.listdir("src/classify") #插件文件夹位于src/classify
for folder in plugin_folders:
    exec(f"from src.classify.{folder}.{folder}Handler import {folder}Mode")



#信息参数
user_lock = [] #用户锁
waiting_group_request = {} #加群请求列表 == 未完成
waiting_friend_request = {} #好友请求列表 == 未完成

#文件参数
permissions_file = "data/permissions.yaml" #(权限文件默认位于 data/permissions.yaml)


# == 涵数 ==

#主涵数
async def onMessage(bot, message):
    start_time = datetime.now()
    #信息处理计时器 - 开始计时
    msgType = identifyMsgType(message) #识别信息种类
    consleLog(message, msgType) #打印console log => 信息记录
    await handleMessage(bot, message, msgType) #正式开始处理信息本体
    #信息处理计时器 - 结束计时
    end_time = datetime.now()
    #打印计时
    endTimeStr = end_time.strftime(format="%Y-%m-%d %H:%M:%S")
    log(f"[{endTimeStr}] [Message Handler]: 指令执行时长为: [{end_time-start_time}]", needPrint=(bot.testMode))
    log("")

#信息处理涵数
async def handleMessage(bot, message, msgType):
    # == 正式开始处理信息本体 ==
    try:
        #黑名单群屏蔽
        if "Group" in msgType:
            config = Config.load_from_file("data/config.yaml")
            backlist = config["backlist"]
            if str(message["group_id"]) in backlist:
                log("该群处于黑名单，已跳过", needPrint=bot.testMode)
                return
        #处理群消息
        if msgType == "Group_message":
            await onGroupMessage(bot, message)
        #处理群戳一戳
        elif msgType == "Group_poke":
            await onPoke(bot, message)
        #处理私聊消息
        elif msgType == "Private_message":
            await onPrivateMessage(bot, message)
        #处理群管理员变更通知
        elif msgType == "Group_setAdmin":
            await onSetAdmin(bot, message)
        #处理群管理员变更通知
        elif msgType == "Group_unsetAdmin":
            await onUnSetAdmin(bot, message)
        #处理ban通知
        elif msgType == "Group_ban":
            await onBan(bot, message)
        #处理ban通知
        elif msgType == "Group_liftBan":
            await onLiftBan(bot, message)
        #处理表情点赞通知
        elif msgType == "Group_msg_emoji_like":
            await onGroup_msg_emoji_like(bot, message)
        #处理加群请求
        elif msgType == "Group_request":
            await onGroup_request(bot, message)
        #处理加好友请求
        elif msgType == "Private_request":
            await onPrivate_request(bot, message)
        #处理加群通知
        elif msgType == "Group_increase":
            await onGroup_increase(bot, message)
    #报错处理
    except Exception as e: 
        tb = e.__traceback__
        formatted_tb = ''.join(traceback.format_tb(tb))
        log(formatted_tb)
    # == 信息处理结束 ==

# == 各种类信息处理涵数 ==

#群消息
async def onGroupMessage(bot, message):
    # == 信息初始化 ==
    [raw_message, be_at] = await beAt(bot, message) #提取艾特
    sender = str(message["sender"]["user_id"])
    # == 特殊锁前指令 == 
    #测试指令
    if raw_message.lower() == "test" and be_at:
        img = ImageMessage(f"file://{bot.localtion}/data/image/botStatus/botStatus.gif")
        msg = MessageChain(["我在~\n", img])
        callback = await bot.reply_to_message(message, msg)
        log(f"{callback}", needPrint=(bot.testMode))
        return
    #强制解锁 => 用户锁
    elif raw_message[-3:] == "out" and (sender in bot.owner or sender in user_lock):
        target = [sender] #需要强制解锁的用户对象
        removed = [] #缓存
        #获取所有用户参数
        target.extend([pessage["data"]["qq"] for pessage in message["message"] if pessage["type"] == "at"])
        #去重
        target = list(set(target))
        #从用户锁里删除
        for user in target:
            if user in user_lock:
                user_lock.remove(str(user))
                removed.append(user)
        #反馈
        if len(removed)>0:
            msg = MessageChain([f"已解除对{removed}的锁定"])
            callback = await bot.reply_to_message(message, msg)
            log(f"{callback}", needPrint=(bot.testMode))
            return
    
    # == 用户锁 ==
    if sender in user_lock:
        #查询反馈
        if be_at: 
            callback = await bot.reply_to_message(message, MessageChain(["别炸我机了，我处理不过来辣"]))
            log(f"{callback}", needPrint=(bot.testMode))
        return
    user_lock.append(sender)

    # == 处理群消息 ==
    try:
        await asyncio.wait_for(handleGroupMessage(bot, message, raw_message, be_at), timeout=10)
    except asyncio.TimeoutError:
        pass
    # == 群消息处理结束 ==

    #释放用户锁
    user_lock.remove(sender)
#群消息内核
async def handleGroupMessage(bot, message, raw_message, be_at):
    try:
        #取得发送群已注册的指令种类 或 注册基础通用种类功能
        permissions = readPermissions(message)
        #按种类处理信息
        for permission in permissions:
            func_name = f"{permission}Mode"
            func = globals().get(func_name)
            if func is None:
                log(f"[Error] 未找到指令种类处理函数: {func_name}\n")
                continue
            try:
                result = func(bot, message, raw_message, be_at)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e: 
                tb = e.__traceback__
                formatted_tb = ''.join(traceback.format_tb(tb))
                log(formatted_tb)
    except Exception as e: 
        tb = e.__traceback__
        formatted_tb = ''.join(traceback.format_tb(tb))
        log(formatted_tb)

#私聊消息
async def onPrivateMessage(bot, message):
    pass

#群戳一戳
async def onPoke(bot, message):
    if message['target_id'] != bot.botAcc:
        return
    group_id = message["group_id"]
    sender = message['user_id']
    event = 18
    idx = random.randint(0, event)
    if idx == 0:
        msg = MessageChain(["戳我干嘛(#`O′)"])
        callback = await bot.send_group_msg(group_id, msg)
        log(f"{callback}", needPrint=(bot.testMode))
        return
    if idx == 1:
        msg = MessageChain(["别戳我(。>︿<)"])
        callback = await bot.send_group_msg(group_id, msg)
        log(f"{callback}", needPrint=(bot.testMode))
        return
    if idx == 2:
        msg = MessageChain(["(｡･ˇ_ˇ･｡:)"])
        callback = await bot.send_group_msg(group_id, msg)
        log(f"{callback}", needPrint=(bot.testMode))
        return
    if idx == 3:
        msg = MessageChain(["咬死你＼(`Δ’)／"])
        callback = await bot.send_group_msg(group_id, msg)
        log(f"{callback}", needPrint=(bot.testMode))
        return
    if idx == 4:
        msg = MessageChain(["你知道我的真身是什么吗？(●'◡'●)"])
        callback = await bot.send_group_msg(group_id, msg)
        log(f"{callback}", needPrint=(bot.testMode))
        time.sleep(1.5)
        callback = await bot.group_poke(group_id, sender)
        log(f"{callback}", needPrint=(bot.testMode))
        msg = MessageChain(["其实是广东双马尾o( ❛ᴗ❛ )o︎"])
        callback = await bot.send_group_msg(group_id, msg)
        log(f"{callback}", needPrint=(bot.testMode))
        return
    if idx == 5:
        msg = MessageChain(["_(:зゝ∠)_"])
        callback = await bot.send_group_msg(group_id, msg)
        log(f"{callback}", needPrint=(bot.testMode))
        return
    if idx == 6:
        msg = MessageChain(["老子戳回来！(｀へ´*)"])
        callback = await bot.send_group_msg(group_id, msg)
        log(f"{callback}", needPrint=(bot.testMode))
        callback = await bot.group_poke(group_id, sender)
        log(f"{callback}", needPrint=(bot.testMode))
        return
    if idx == 7:
        msg = MessageChain(["无不无聊？＼(`Δ’)／"])
        callback = await bot.send_group_msg(group_id, msg)
        log(f"{callback}", needPrint=(bot.testMode))
        return
    if idx == 8:
        msg = MessageChain(["再戳我睡了..."])
        callback = await bot.send_group_msg(group_id, msg)
        log(f"{callback}", needPrint=(bot.testMode))
        return
    if idx == 9:
        msg = MessageChain(["睡了(｀へ´*)"])
        callback = await bot.send_group_msg(group_id, msg)
        log(f"{callback}", needPrint=(bot.testMode))
        return
    if idx == 10:
        msg = MessageChain(["艹！"])
        callback = await bot.send_group_msg(group_id, msg)
        log(f"{callback}", needPrint=(bot.testMode))
        return
    if idx == 11:
        for i in range(3):
            callback = await bot.group_poke(group_id, sender)
            log(f"{callback}", needPrint=(bot.testMode))
            time.sleep(5)
        msg = MessageChain(["爽了？"])
        callback = await bot.send_group_msg(group_id, msg)
        log(f"{callback}", needPrint=(bot.testMode))
        return
    if idx == 12:
        return
    if idx == 13:
        msg = MessageChain(["你干嘛戳我？"])
        callback = await bot.send_group_msg(group_id, msg)
        log(f"{callback}", needPrint=(bot.testMode))
        return
    if idx == 14:
        msg = MessageChain(["戳你麻痹！"])
        callback = await bot.send_group_msg(group_id, msg)
        log(f"{callback}", needPrint=(bot.testMode))
        return
    if idx == 15:
        msg = MessageChain(["再戳试试？"])
        callback = await bot.send_group_msg(group_id, msg)
        log(f"{callback}", needPrint=(bot.testMode))
        return
    if idx == 16:
        msg = MessageChain(["你有完没完？"])
        callback = await bot.send_group_msg(group_id, msg)
        log(f"{callback}", needPrint=(bot.testMode))
        return
    if idx == 17:
        msg = MessageChain(["别戳了，烦死了！"])
        callback = await bot.send_group_msg(group_id, msg)
        log(f"{callback}", needPrint=(bot.testMode))
        return
    if idx == 18:
        msg = MessageChain(["戳死你！"])
        callback = await bot.send_group_msg(group_id, msg)
        log(f"{callback}", needPrint=(bot.testMode))
        for i in range(3):
            callback = await bot.group_poke(group_id, sender)
            log(f"{callback}", needPrint=(bot.testMode))
            time.sleep(5)
        return
#表情点赞
async def onGroup_msg_emoji_like(bot, message):
    pass

#设置群管理员
async def onSetAdmin(bot, message):
    target = str(message["user_id"])
    group_id = message["group_id"]
    if target in bot.owner: #bot.owner = [...]
        msg = MessageChain(["恭喜主人成为管理员！(●'◡'●)"])
        callback = await bot.send_group_msg(group_id, msg)
        log(f"{callback}", needPrint=(bot.testMode))
    elif target == str(bot.botAcc): #bot.botAcc = int
        msg = MessageChain(["谢谢群主设置的管理员！o( ❛ᴗ❛ )o︎"])
        callback = await bot.send_group_msg(group_id, msg)
        log(f"{callback}", needPrint=(bot.testMode))
#取消群管理员
async def onUnSetAdmin(bot, message):
    if str(message["user_id"]) == str(bot.botAcc):
        msg = MessageChain(["管理员资格被取消了(。>︿<)"])
        callback = await bot.send_group_msg(message["group_id"], msg)
        log(f"{callback}", needPrint=(bot.testMode))

#设置Ban
async def onBan(bot, message):
    pass
#解除Ban
async def onLiftBan(bot, message):
    if str(message["user_id"]) == str(bot.botAcc):
        msg = MessageChain(["谢谢解禁我(●'◡'●)"])
        callback = await bot.send_group_msg(message["group_id"], msg)
        log(f"{callback}", needPrint=(bot.testMode))

#加群请求
async def onGroup_request(bot, message):
    owner = bot.owner[0]
    sender = message["user_id"]
    group_id = message['group_id']
    comment = message['comment']
    #自动通过好友内的群邀请
    try:
        friendsList = await bot.get_friend_list()
        for friend in friendsList["data"]:
            if friend["user_id"] == sender:
                callback = await bot.set_group_add_request(flag=message['flag']) 
                log(f"{callback}", needPrint=(bot.testMode))
                callback = await bot.send_private_msg(
                    owner, 
                    MessageChain([f"自动通过了来自[{sender}]的加群[{group_id}]请求，附言：{comment}"])
                    )
                log(f"{callback}", needPrint=(bot.testMode))
                return
    except: pass
    #通知管理员
    callback = await bot.send_private_msg(
        owner, 
        MessageChain([f"收到来自[{sender}]的加群[{group_id}]请求，附言：{comment}"]))
    log(f"{callback}", needPrint=(bot.testMode))
    """
    waiting_group_request[message['group_id']] = message['flag'] #将加群请求放入等候列表
    msg = MessageChain(["正在等候的加群请求:\n"])
    keys = waiting_group_request.keys()
    for idx in len(keys):
        msg.add(f"  {idx}. {keys[idx]}\n")
    callback = await bot.send_private_msg(owner, msg)
    log(f"{callback}", needPrint=(bot.testMode))
    """
#加好友请求
async def onPrivate_request(bot, message):
    owner = bot.owner[0]
    sender = message["user_id"]
    comment = message['comment']
    #通知管理员
    callback = await bot.send_private_msg(
        owner, 
        MessageChain([f"收到来自[{sender}]的好友请求，附言：{comment}"])
        )
    log(f"{callback}", needPrint=(bot.testMode))
    """
    waiting_friend_request[message['user_id']] = message['flag'] #将好友请求放入等候列表
    msg = MessageChain(["正在等候的加好友请求:\n"])
    keys = waiting_friend_request.keys()
    for idx in len(keys):
        msg.append(f"{idx}. {keys[idx]}\n")
    callback = await bot.send_private_msg(owner, msg)
    """

#加群通知
async def onGroup_increase(bot, message):
    group_id = message["group_id"]
    user_id = message["user_id"]
    #小生物被加进群时触发
    if str(user_id) == str(bot.botAcc):
        msg = MessageChain(["小生物已加入\n本群已自动注册通用类功能权限\n请输入'功能列表'以查看权限"])
        callback = await bot.send_group_msg(group_id, msg)
        log(f"{callback}", needPrint=(bot.testMode))
    #其他人加群时触发
    else:
        msg = MessageChain([AtMessage(user_id)])
        msg.add(" 欢迎")
        callback = await bot.send_group_msg(group_id, msg)
        log(f"{callback}", needPrint=(bot.testMode))


# == 工具涵数 ==

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
        try:
            replyed_msg = await bot.get_msg(relpy_id)
            log(f"{replyed_msg}", needPrint=(bot.testMode))
            if replyed_msg["data"]["sender"]["user_id"] == bot.botAcc:
                raw_message = raw_message.replace(f"[CQ:reply,id={relpy_id}]","").strip()
                be_at = True
        except: pass
    if len(raw_message)<1:
        raw_message = f"blankmsg,id:{message["message_id"]}"
    #返回已处理信息及艾特状态
    return [raw_message, be_at]

#识别信息种类
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
            elif message["notice_type"] == "group_increase":
                msgType += "increase"
            else:
                log(f"发现未定义通知种类: {message["notice_type"]}\n")
        case "request":
            msgType += "request"
        case "message_sent":
            msgType += "message"
        case _:
            log(f"发现未定义信息种类: {message["post_type"]}\n")
    return msgType

#打印信息记录
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
            output += f"--[Group:{group_id}]{user_nickname}[User:{user_id}]:[{message_id}]\n"
            output += f"{raw_message}"
        case "Group_recall":
            group_id = message["group_id"]
            user_id = message["user_id"]
            message_id = message["message_id"]
            output += f"--[Group:{group_id}]{user_id}撤回了信息:{message_id}"
        case "Group_poke":
            group_id = message["group_id"]
            user_id = message["user_id"]
            target_id = message["target_id"]
            output += f"--[Group:{group_id}]{user_id}戳了戳:{target_id}"
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
    try:
        log(f"{output}")
    except Exception as e: 
        print(e) 
        print(f"UN-Log Info:\n{output}")

#检查群权限
def readPermissions(message):
    group_id = str(message["group_id"])
    #获取群权限
    try: 
        permissions = Config.load_from_file(permissions_file)
        permissions = permissions[group_id]
        if permissions == None: raise Exception()
    #初始化群权限
    except: 
        #检查文件存在
        try: permissions = Config.load_from_file(permissions_file)
        except: permissions = Config()
        #初始化
        permissions[group_id] = ["general"]
        permissions.dump_to_file(permissions_file)
        permissions = ["general"]
    #返回
    return permissions
