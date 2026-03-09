
# == 信息处理文件 ==

#此文件为OneBot11-小生物的信息处理涵数文件
#应用环境为LL-Bot v2.4.4

#如果不清楚具体作用，除配置外，请不要修改任何参数代码


#引用库
#  ==> pip自动下载缺失的库
# type: ignore
import os, asyncio
from src.importer import import_package
import src.config as config_reader

exec(import_package("traceback"))
exec(import_package("Config", package_from="config_io", ))
exec(import_package("datetime", package_from= "datetime"))
exec(import_package("src.loger" , name_as= "loger"))
#自动加载插件文件夹下的所有文件
plugin_folders = os.listdir("src/plugin") #插件文件夹位于src/plugin
for folder in plugin_folders:
    exec(f"from src.plugin.{folder}.main import onMessage as {folder}_onMessage")

#文件参数
permissions_file = "data/permissions.yaml" #(权限文件默认位于 data/permissions.yaml)


# == 涵数 ==

#主涵数
async def onMessage(bot, message):
    start_time = datetime.now()
    #信息处理计时器 - 开始计时
    msgType = identifyMsgType(message) #识别信息种类
    consleLog(message, msgType) #打印console log => 信息记录
    raw_message, be_at = await beAt(bot, message)
    if msgType[0:7] == "Private": be_at = True
    await handleMessage(bot, message, raw_message, be_at, msgType) #正式开始处理信息本体
    #信息处理计时器 - 结束计时
    end_time = datetime.now()
    #打印计时
    endTimeStr = end_time.strftime(format="%Y-%m-%d %H:%M:%S")
    loger.log(f"[{endTimeStr}] [Message Handler]: 指令执行时长为: [{end_time-start_time}]", needPrint=(bot.testMode))
    loger.log("")

#信息处理涵数
async def handleMessage(bot, message, raw_message, be_at, msgType):
    # == 正式开始处理信息本体 ==
    try:
        permissions = readPermissions(message)
        for plugin in permissions:
            func_name = f"{plugin}_onMessage"
            func = globals().get(func_name)
            if func is None:
                loger.log(f"[Error] 未找到指令种类处理函数: {func_name}\n")
                continue
            try:
                result = func(bot, message, raw_message, be_at, msgType)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e: 
                tb = e.__traceback__
                formatted_tb = ''.join(traceback.format_tb(tb))
                loger.log(formatted_tb)
    #报错处理
    except Exception as e: 
        tb = e.__traceback__
        formatted_tb = ''.join(traceback.format_tb(tb))
        loger.log(formatted_tb)
    # == 信息处理结束 ==

# == 工具涵数 ==

#确认信息是否被艾特或回复
async def beAt(bot, message):
    be_at = False #暂存
    raw_message = "" #暂存
    try:
        raw_message = message["raw_message"] #信息原数据
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
        #结构为: [CQ:reply,id={信息ID}]
        if "[CQ:reply,id=" in raw_message and "]" in raw_message:
            #从结构中取出 信息ID
            idx = raw_message.find("[CQ:reply,id=")
            relpy_id = raw_message[idx+13:]
            idx = relpy_id.find("]")
            relpy_id = relpy_id[:idx]
            #取得 信息并确实发送者
            try:
                replyed_msg = await bot.get_msg(relpy_id)
                loger.log(f"{replyed_msg}", needPrint=(bot.testMode))
                if str(replyed_msg["data"]["sender"]["user_id"]) == str(bot.botAcc):
                    raw_message = raw_message.replace(f"[CQ:reply,id={relpy_id}]","").strip()
                    be_at = True
            except: pass
        if len(raw_message)<1:
            raw_message = f"blankmsg,id:{message["message_id"]}"
        #
    except Exception as e: pass
    #返回已处理信息及艾特状态
    config = config_reader.load_config("data/config.yaml") #加载配置文件
    allowSlash = config["allowSlash"]
    if allowSlash:
        try:
            if raw_message[0] == "/":
                raw_message = raw_message[1:]
        except: pass
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
        loger.log(f"{output}")
    except Exception as e: 
        print(e) 
        print(f"UN-Log Info:\n{output}")

#检查群权限
def readPermissions(message):
    try: places_id = f"group_{message["group_id"]}"
    except: 
        try: places_id = f"private_{message['sender']['user_id']}"
        except: places_id = f"private_{message['user_id']}"
    #获取群权限
    try: 
        permissions = Config.load_from_file(permissions_file)
        permissions = permissions[places_id]
        if permissions == None: raise Exception()
    #初始化群权限
    except: 
        #检查文件存在
        try: permissions = Config.load_from_file(permissions_file)
        except: permissions = Config()
        #初始化
        permissions[places_id] = ["功能注册器"]
        permissions.dump_to_file(permissions_file)
        permissions = ["功能注册器"]
    #返回
    return permissions
