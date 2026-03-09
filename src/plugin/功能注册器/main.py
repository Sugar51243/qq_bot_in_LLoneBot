
# == 功能注册器文件 ==

#此文件为OneBot11-小生物的功能注册器涵数文件
#应用环境为LL-Bot v2.4.4

#如果不清楚具体作用，除配置外，请不要修改任何参数代码


#引用库
#  ==> pip自动下载缺失的库
# type: ignore
import os, asyncio
from src.importer import import_package
from src.tools.reply_message import feedback
exec(import_package(
    "MessageChain, ImageMessage, RecordMessage, AtMessage, EmojiMessage, ReplyMessage", 
    package_from= "OneBotConnecter.MessageType", package_pip_Name = "OneBotConnecter"))
exec(import_package("traceback"))
exec(import_package("Config", package_from="config_io", ))
exec(import_package("src.loger" , name_as= "loger"))

#文件参数
permissions_file = "data/permissions.yaml" #(权限文件默认位于 data/permissions.yaml)

waiting_leave = []


async def onMessage(bot, message, raw_message, be_at, msgType):
    if msgType == "Group_increase":
        if str(message["user_id"]) == str(bot.botAcc):
            send = MessageChain(["欢迎使用小生物，本群暂未启用任何功能。请使用'help'查询更多信息。"])
            callback = await bot.send_group_msg(message["group_id"], send)
            loger.log(f"{callback}", needPrint=(bot.testMode))
        else:
            send = MessageChain([AtMessage(message["user_id"])])
            send.add(" 欢迎")
            callback = await bot.send_group_msg(message["group_id"], send)
            loger.log(f"{callback}", needPrint=(bot.testMode))
        return
    elif msgType == "Private_increase":
        send = MessageChain(["欢迎使用小生物，暂未启用任何功能。请使用'help查询更多信息。"])
        callback = await bot.send_private_msg(message["user_id"], send)
        loger.log(f"{callback}", needPrint=(bot.testMode))
        return
    elif msgType == "Group_request":
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
                    loger.log(f"{callback}", needPrint=(bot.testMode))
                    callback = await bot.send_private_msg(
                        owner, 
                        MessageChain([f"自动通过了来自[{sender}]的加群[{group_id}]请求，附言：{comment}"])
                        )
                    loger.log(f"{callback}", needPrint=(bot.testMode))
                    return
        except: pass
        #通知管理员
        callback = await bot.send_private_msg(
            owner, 
            MessageChain([f"收到来自[{sender}]的加群[{group_id}]请求，附言：{comment}"]))
        loger.log(f"{callback}", needPrint=(bot.testMode))
        return
    elif msgType == "Private_request":
        owner = bot.owner[0]
        sender = message["user_id"]
        comment = message['comment']
        #通知管理员
        callback = await bot.send_private_msg(
            owner, 
            MessageChain([f"收到来自[{sender}]的好友请求，附言：{comment}"])
            )
        loger.log(f"{callback}", needPrint=(bot.testMode))
        return
    # == 权限系统 ==
    command = raw_message.split(" ")
    places_id = get_places_id(message)
    #注册功能
    if command[0] in ["注册权限", "注册功能", "注册插件", "启用功能", "启用插件", "注册", "启用"]:
        target = command[1:]
        await registrate(bot, message, places_id, target)
    #停用功能
    elif command[0] in ["删除权限", "删除功能", "删除插件", "停用功能", "停用插件", "删除", "停用"]:
        target = command[1:]
        await deletePermission(bot, message, places_id, target)
    elif raw_message == "确认" and places_id in waiting_leave:
        await leave(bot, msg["group_id"])
    elif raw_message == "取消" and places_id in waiting_leave:
        waiting_leave.remove(places_id)
        send = MessageChain([f"\n退群动作已取消。"])
        await feedback(bot, message, send)
    #功能列表
    elif raw_message in ["功能列表", "权限列表", "功能", "已注册功能", "已注册权限"]:
        await functionCheck(bot, message, places_id)
    elif raw_message in ["可注册功能", "可注册权限", "未注册功能", "未注册权限", "未注册", "可注册"]:
        await allowFunctionCheck(bot, message, places_id)
    #帮助文档
    elif command[0].lower() in ["查询", "帮助", "文档", "帮助文档", "help"]:
        if len(command) <= 1:
            plugin = "功能注册器"
        else: plugin = command[1]
        await help(bot, message, plugin, places_id)
    elif raw_message in ["功能注册器", "注册器"]:
        await help(bot, message, "功能注册器", places_id)


def read_file(path):
    try:
        file = open(path, "r", encoding='utf-8')
        content = file.read()
        file.close()
    except FileNotFoundError: 
        file = open(path, "w", encoding='utf-8')
        file.write("未定义")
        file.close()
        content = "未定义"
    return content

# == 权限系统 ==
# 转换成使用者ID
def get_places_id(message):
    try: places_id = f"private_{message["sender"]["user_id"]}"
    except: places_id = f"private_{message["user_id"]}"
    try: places_id = f"group_{message["group_id"]}"
    except: pass
    return places_id

# 已启用功能参数列表 => list
def get_plgin_registrated_list(message = None, places_id = None):
    if places_id == None:
        places_id = get_places_id(message)
    permissions = Config.load_from_file("data/permissions.yaml")
    permissions = permissions[places_id]
    return permissions

# 可用功能参数列表 => list message: str
def allowed_plugins(places_id):
    message = ""
    plugin_folders = os.listdir("src/plugin")
    permissions = permissions = get_plgin_registrated_list(places_id=places_id)
    plugin_folders = list(set(plugin_folders) - set(permissions))
    if len(plugin_folders) <= 0: 
        message += "\n无，请等待管理员进一步更新"
    i = 1
    for plugin in plugin_folders:
        message += f"\n{i}. {plugin}"
        info = read_file(f"src/plugin/{plugin}/info.txt")
        message += f"\n{info}"
        i += 1
    return message

# 已启用功能参数列表 => list message: str
def registrated_plugin(places_id):
    message = ""
    permissions = get_plgin_registrated_list(places_id=places_id)
    i = 1
    for plugin in permissions:
        message += f"\n{i}. {plugin}"
        info = read_file(f"src/plugin/{plugin}/info.txt")
        message += f"\n{info}"
        i += 1
    return message

# 注册功能
async def registrate(bot, msg, places_id: str, target: list):
    plugin_folders = os.listdir("src/plugin")
    i = 0
    for plugin in target:
        # 不存在的功能
        if plugin not in plugin_folders:
            message = MessageChain([f"\n启用失败,小生物未有功能: {plugin}"])
            await feedback(bot, msg, message)
            continue
        # 正常注册
        try:
            permissions = Config.load_from_file("data/permissions.yaml")
            holded_permissions = permissions[places_id]
            # 功能已注册
            if plugin in holded_permissions:
                message = MessageChain([f"\n功能已启用，请不要重复注册"])
                await feedback(bot, msg, message)
                continue
            # 功能未注册 => 注册
            holded_permissions.append(plugin)
            permissions[places_id] = holded_permissions
            permissions.dump_to_file("data/permissions.yaml")
            message = MessageChain([f"{plugin}启用成功"])
            await feedback(bot, msg, message)
            i += 1 # 计数
        # 注册失败
        except:
            message = MessageChain([f"\n后台写入失败，已帮你联系机器人管理员。请耐心等待回复……"])
            await feedback(bot, msg, message)
            break
    # 未识别出有效参数
    if i <= 0:
        message = MessageChain([f"\n未识别出有效参数, 以下为本场景可注册的功能列表:"])
        message.add(allowed_plugins(places_id))
        await feedback(bot, msg, message)

# 停用功能
async def deletePermission(bot, msg, places_id: str, target: list):
    permissions = Config.load_from_file("data/permissions.yaml")
    holded_permissions = permissions[places_id]
    stoped = []
    for plugin in target:
        # 注册器不可停用
        if plugin == "register":
            message = MessageChain([f"\n注册器不可停用"])
            await feedback(bot, msg, message)
            continue
        # 小生物退群
        if plugin == "小生物" and len(target) == 1:
            if places_id[:5] != "group":
                message = MessageChain([f"私聊不可停用小生物"])
                await feedback(bot, msg, message)
                return
            if places_id in waiting_leave:
                waiting_leave.remove(places_id)
                await leave(bot, msg["group_id"])
                return
            message = MessageChain([f"\n停用小生物后，本账号将自动退群。"])
            message.add('\n请再次输入指令或发送"确认"以确认退群\n误触发请发送"取消"')
            message.add('\n如只需关闭 除注册器以外的所有功能,可以使用"停用 all"指令。(请先取消退群)')
            message.add('\n(复制引号内容发送)')
            await feedback(bot, msg, message)
            waiting_leave.append(places_id)
            return
        # 全部停用
        if plugin.lower() in ["all", "全部", "全部功能", "已注册功能"] and len(target) == 1:
            temp = holded_permissions
            temp.remove("register")
            if len(temp) > 0:
                target = temp
                await deletePermission(bot, msg, places_id, target)
            return
        # 不存在的功能
        if plugin not in holded_permissions:
            message = MessageChain([f"\n该功能未启用: {plugin}"])
            message.add(f'\n可以使用 "启用 {plugin}" 指令启用该功能(复制引号内容发送)')
            await feedback(bot, msg, message)
            continue
        # 正常停用
        holded_permissions.remove(plugin)
        stoped.append(plugin)
    if len(stoped) > 0:
        permissions[places_id] = holded_permissions
        permissions.dump_to_file("data/permissions.yaml")
        if len(stoped) == 1: stoped = stoped[0]
        message = MessageChain([f"\n功能{stoped}停用成功"])
        await feedback(bot, msg, message)
    else:
        message = MessageChain([f"\n未识别出有效参数, 以下为本场景已启用的功能列表:"])
        message.add(registrated_plugin(places_id))
        await feedback(bot, msg, message)

# 检查已启用功能
async def functionCheck(bot, msg, places_id: str):
    message = MessageChain([f"\n以下为本场景已启用的功能列表:"])
    message.add(registrated_plugin(places_id))
    await feedback(bot, msg, message)

# 检查可注册功能
async def allowFunctionCheck(bot, msg, places_id: str):
    message = MessageChain([f"\n以下为本场景未注册且可注册的功能列表:"])
    message.add(allowed_plugins(places_id))
    await feedback(bot, msg, message)

# 退群
async def leave(bot):
    message = MessageChain([f"小生物将退群"])
    await feedback(bot, msg, message)
    callback = await bot.set_group_leave(message["group_id"])
    loger.log(f"{callback}", needPrint=(bot.testMode))

# == 帮助文档 ==
# 帮助文档
async def help(bot, msg, plugin, places_id):
    permissions = Config.load_from_file("data/permissions.yaml")
    holded_permissions = permissions[places_id]
    plugin_folders = os.listdir("src/plugin")
    if plugin not in plugin_folders:
        message = MessageChain([f"\n小生物目前未开发{plugin}功能。如有需要,可以:\n1.进群[980803820]反馈"])
        if len(bot.owner) > 0:
            message.add(f"\n2.向管理员[{bot.owner[0]}]反馈")
        await feedback(bot, msg, message)
        return
    if plugin not in holded_permissions:
        message = MessageChain([f"\n{plugin}功能未启用"])
        message.add(f'\n可以使用 "启用 {plugin}" 指令启用该功能(复制引号内容发送)')
        await feedback(bot, msg, message)
        return
    help_data = read_file(f"src/plugin/{plugin}/help.txt")
    message = MessageChain([f"\n{help_data}"])
    await feedback(bot, msg, message)