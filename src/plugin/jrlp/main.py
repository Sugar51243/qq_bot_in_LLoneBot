
# == 每日老婆插件文件 ==

#此文件为OneBot11-小生物的每日老婆插件涵数文件
#应用环境为LL-Bot v2.4.4

#如果不清楚具体作用，除配置外，请不要修改任何参数代码


#引用库
#  ==> pip自动下载缺失的库
# type: ignore
import os, asyncio, random
from src.importer import import_package
from src.tools.reply_message import feedback
from src.plugin.小生物积分.main import get_user_score, reduce_score
exec(import_package("date", package_from="datetime", package_pip_Name="datetime"))
exec(import_package("Config", package_from="config_io", package_pip_Name="config_io"))
exec(import_package("log" , package_from= "src.loger"))
exec(import_package(
    "MessageChain, ImageMessage, AtMessage",
    package_from= "OneBotConnecter.MessageType", package_pip_Name = "OneBotConnecter"))

#文件参数
jrlp_file = "data/plugin/jrlp/jrlp.json" #(每日老婆记录文件默认位于 data/plugin/jrlp/jrlp.json)


async def onMessage(bot, message, raw_message, be_at, msgType):
    if msgType != "Group_message": return
    # == 今日老婆 ==
    #今日老婆
    if raw_message in ["jrlp", "今日老婆"]:
        await jrlp(bot, message)
    elif raw_message == "换老婆" and has_jrlp(bot, message)[0]:
        score = get_user_score(message)
        if score["scores"] >= 10:
            if cancal_jrlp(bot, message):
                reduce_score(message, 10)
                await jrlp(bot, message)
                return
        await feedback(bot, message, MessageChain(["不许当DD哦！"]))
    elif raw_message[0] in ["牛"]:
        await n_jrlp(bot, message, raw_message)
    pass


# == 今日老婆 ==
async def jrlp(bot, msg):
    hasJrlp, jrlp, groupData, todayData, data = has_jrlp(bot, msg) 
    if not hasJrlp:
        groupData, jrlp = await get_jrlp(bot, msg["group_id"], msg["sender"]["user_id"], groupData)
        save_jrlp(bot, msg["group_id"], msg["sender"]["user_id"], jrlp)
    #发送
    log(f"配对已完成: {jrlp}", needPrint=(bot.testMode))
    if jrlp == None: 
        message = MessageChain(["单身狗"])
        await feedback(bot, msg, message)
        return
    try:
        log(f"正在获取对象资料", needPrint=(bot.testMode))
        info = await bot.get_group_member_info(group_id=msg["group_id"], user_id=jrlp, no_cache=True)
        log(f"{info}", needPrint=(bot.testMode))
        card = info['data']['card_or_nickname']
    except Exception as e: 
        tb = e.__traceback__
        formatted_tb = ''.join(traceback.format_tb(tb))
        log(formatted_tb)
        card = str(jrlp)
    avatar = f"https://q1.qlogo.cn/g?b=qq&nk={jrlp}&s=640"
    #发送
    message = f"\n你今天的老婆是: {card}"
    if str(jrlp) in bot.owner:
        message = f"\n你今天的老公是: {card}"
    message = MessageChain([message])
    message.add(MessageChain([ImageMessage(avatar)]))
    await feedback(bot, msg, message)

async def n_jrlp(bot, msg, raw_message):
    #get target
    target_id = None
    for i in msg["message"]:
        if i["type"] == "at":
            target_id = i["data"]["qq"]
            break
        elif i["type"] == "reply":
            msg_id = i["data"]["id"]
            msg = await bot.get_msg(message_id=msg_id)
            target_id = msg["data"]["sender"]["user_id"]
            break
    if not target_id or target_id == msg["sender"]["user_id"]:
        return
    #own data
    own_data_list = has_jrlp(bot, msg)
    hasJrlp, jrlp = own_data_list[0], own_data_list[1]
    #target data
    target_data_list = has_jrlp(bot, msg, group_id=msg["group_id"], user_id=target_id)
    target_hasJrlp, target_jrlp = target_data_list[0], target_data_list[1]
    #check input ok
    if not target_hasJrlp:
        await feedback(bot, msg, MessageChain(["对方未有老婆"]))
        return
    if jrlp == target_id or target_jrlp == msg["sender"]["user_id"]:
        await feedback(bot, msg, MessageChain(["不能牛/被牛自己哦"]))
        return
    #check score
    score = get_user_score(msg)
    need_score = 20 if not hasJrlp else 30
    if score["scores"] < need_score:
        await feedback(bot, msg, MessageChain([f"需要{need_score}积分哦！"]))
        return
    #cancal_jrlp
    if hasJrlp: #own
        if cancal_jrlp(bot, msg):
            reduce_score(msg, 10)
    if cancal_jrlp(bot, None, group_id=msg["group_id"], user_id=target_id): #target
        reduce_score(msg, 20)
    #save
    save_jrlp(bot, msg["group_id"], msg["sender"]["user_id"], target_jrlp)
    #reply
    message = MessageChain(["\n你已牛取", AtMessage(target_id), "的老婆"])
    info = await bot.get_group_member_info(group_id=msg["group_id"], user_id=target_jrlp, no_cache=True)
    card = info['data']['card_or_nickname']
    message.add(f"\n你今天的老婆是: {card}")
    if str(target_jrlp) in bot.owner:
        message.add(f"\n你今天的老公是: {card}")
    message.add(MessageChain([ImageMessage(f"https://q1.qlogo.cn/g?b=qq&nk={target_jrlp}&s=640")]))
    await feedback(bot, msg, message)

def cancal_jrlp(bot, msg=None, group_id=None, user_id=None):
    group_id = msg["group_id"] if not group_id else group_id
    user_id = msg["sender"]["user_id"] if not user_id else user_id
    hasJrlp, jrlp, groupData, todayData, data = has_jrlp(bot, msg, group_id, user_id)
    if not hasJrlp:
        return False
    groupData.pop(str(user_id), None)
    groupData.pop(str(jrlp), None)
    todayData[str(group_id)] = groupData
    today = str(date.today())
    data = Config({today:todayData})
    data.dump_to_file(jrlp_file)
    return True

def has_jrlp(bot, message = None, group_id=None, user_id=None):
    group_id = message["group_id"] if not group_id else group_id
    user_id = message["sender"]["user_id"] if not user_id else user_id
    #获取今日日期并查询
    today = str(date.today())
    log(f"今日日期: {today}", needPrint=(bot.testMode))
    try:
        data = Config.load_from_file(path=jrlp_file)
        todayData = data[today]
        log(f"今日数据: {todayData}", needPrint=(bot.testMode))
    except:
        log(f"今日未有数据", needPrint=(bot.testMode))
        todayData = Config()
    #从数据中获取该群数据记录
    try:
        groupData = todayData[str(group_id)]
        log(f"今日该群数据: {groupData}", needPrint=(bot.testMode))
    except:
        log(f"今日该群未有数据", needPrint=(bot.testMode))
        groupData = Config()
    #尝试查询该用户配对记录
    try:
        jrlp = groupData[str(user_id)]
        log(f"配对记录发现: {jrlp}", needPrint=(bot.testMode))
        return [True, jrlp, groupData, todayData, data]
    except:
        log(f"配对记录未发现", needPrint=(bot.testMode))
        return [False, None, groupData, todayData, data]

def save_jrlp(bot, group_id, user_id, jrlp_id):
    hasJrlp, jrlp, groupData, todayData, data = has_jrlp(bot, None, group_id, user_id)
    groupData[str(user_id)] = str(jrlp_id)
    groupData[str(jrlp_id)] = str(user_id)
    todayData[str(group_id)] = groupData
    today = str(date.today())
    data = Config({today:todayData})
    data.dump_to_file(jrlp_file)

# 配对
async def get_jrlp(bot, group_id, user_id, groupData, target_id=None):
    if not target_id:
        log(f"正在获取群成员名单", needPrint=(bot.testMode))
        member_list_data = await bot.get_group_member_list(group_id=group_id)
        log(f"{member_list_data}", needPrint=(bot.testMode))
        member_list: list = member_list_data['data']
        log(f"成员名单: {member_list}", needPrint=(bot.testMode))
        log(f"正在更新可配对群员名单", needPrint=(bot.testMode))
        temp = []
        for i in range(len(member_list)):
            if member_list[i]['user_id'] != user_id and str(member_list[i]['user_id']) not in groupData:
                temp.append(member_list[i]['user_id'])
        member_list = temp
        log(f"更新后成员名单: {member_list}", needPrint=(bot.testMode))
        #如果全员已配对 则 返回单身信息
        if len(member_list) <= 0:
            log(f"全员已配对", needPrint=(bot.testMode))
            return groupData, None
        log(f"开始配对", needPrint=(bot.testMode))
        idx = random.randint(0,len(member_list)-1)
        log(f"随机数为0-{len(member_list)-1}: {idx}", needPrint=(bot.testMode))
        target_id = member_list[idx]
        log(f"配对用户ID为: {target_id}", needPrint=(bot.testMode))
    #双方同时更新目录
    groupData[str(user_id)] = str(target_id)
    groupData[str(target_id)] = str(user_id)
    return [groupData, target_id]
