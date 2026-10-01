
# == Tomori OurNotes社区模块 ==

# 查贴纸(getStampImage) / 上传车牌+ycm(车站) / 交友登记/删除交友/交友列表
# 车站与交友依赖后端MongoDB(ENABLE_DB=true), 未启用时后端返回域内错误并原样转发

from OneBotConnecter.types import MessageChain
from OneBotConnecter.loger.log_info import log
from src.plugins.tomori_ournotes.config import load_config
from src.plugins.tomori_ournotes.call_ournotes import call_ournotes, call_net, parse_server, server_hint, split_servers
from src.plugins.tomori_ournotes.reply import feedback

#贴纸类别关键词 → 后端stampType(关键词只认哪一类名称)
STAMP_SCOPE_KEY_SET = {"角色": "character", "角色名": "character", "成员": "character", "团体": "band", "乐团": "band", "乐队": "band"}

#列出全部贴纸的关键词
STAMP_ALL_KEYWORDS = ["全部", "列表", "all"]

#QQ头像外链(后端仅允许https+qlogo.cn域)
def get_qq_avatar(user_id) -> str:
    return f"https://q1.qlogo.cn/g?b=qq&nk={user_id}&s=640"

#获取发送者昵称(为空时以QQ号兜底, 后端校验要求非空)
def get_user_name(message) -> str:
    nickname = f"{message.raw_data.get('sender', {}).get('nickname', '')}".strip()
    return nickname if nickname else f"QQ{message.user_id}"

#查贴纸 - /getStampImage(三种用法: 数字ID→原图 / 关键词→搜索列表图 / 全部→全量列表图)
def get_stamp_image(bot, message, parameter):
    tokens, servers = split_servers(parameter.split())
    #类别词(角色/团体)出现在末尾时限定匹配维度
    scope = None
    if tokens and tokens[-1] in STAMP_SCOPE_KEY_SET:
        scope = STAMP_SCOPE_KEY_SET[tokens[-1]]
        tokens = tokens[:-1]
    text = " ".join(tokens)
    config = load_config()
    datapack = {
        "displayedServerList": servers,
        "compress": config["compress"]
    }
    if not text:
        send_message = MessageChain(["\n[TOMORI]查询Our Notes贴纸(四服务器独立)"])
        if scope:
            send_message.add("\n只给了类别, 请补上关键词, 例: 查贴纸 高松灯 角色")
            feedback(message, send_message)
            return
        send_message.add("\n[数字ID] → 直出贴纸原图")
        send_message.add("\n例: 查贴纸 1")
        send_message.add("\n[关键词] (类别) (服务器) → 搜索贴纸列表图(带ID与名称)")
        send_message.add("\n类别: 角色/团体(只认该类名称, 默认都认)")
        send_message.add("\n例: 查贴纸 高松灯 角色 jp")
        send_message.add("\n[全部] (服务器) → 列出该服全部贴纸")
        send_message.add(f"\n服务器: {server_hint()}(默认港澳台服)\n")
        feedback(message, send_message)
        return
    if text.isdigit():
        datapack["stampId"] = int(text)
    elif text.lower() in STAMP_ALL_KEYWORDS:
        #不传stampId/text即列出全部(scope对全量列表无意义)
        pass
    else:
        datapack["text"] = text
        if scope:
            datapack["stampType"] = scope
    message_chain = call_ournotes("getStampImage", datapack)
    feedback(message, message_chain)

#上传车牌 - /station/submitRoomNumber(同房号重复提交=刷新)
def submit_room_number(bot, message, raw_message):
    parameter = raw_message[4:].strip()
    tokens = parameter.split(" ")
    room_number = tokens[0]
    if not room_number or not room_number.isdigit():
        feedback(message, MessageChain(["\n[TOMORI]房间号非法, 例: tomori上传车牌 123456 有人来吗"]))
        return
    content = parameter[len(room_number):].strip()
    config = load_config()
    datapack = {
        "number": int(room_number),
        "rawMessage": f"{room_number} {content}".strip(),
        "platform": "qq",
        "userId": f"{message.user_id}",
        "userName": get_user_name(message),
        "avatarUrl": get_qq_avatar(message.user_id),
        "time": 120
    }
    result = call_net(f"{config['ournotes_uri']}/station/submitRoomNumber", mode="post", data_pack=datapack)
    if result == {}:
        feedback(message, MessageChain(["\n[TOMORI]OurNotes后端连接失败"]))
        return
    if result.get("status") == "success":
        feedback(message, MessageChain([f"\n[TOMORI]{result.get('data', '提交成功')}"]))
    else:
        feedback(message, MessageChain([f"\n[TOMORI]上传失败, {result.get('data', '未知错误')}"]))

#ycm - 车站列表图(/roomList未传roomList时直接查后端数据库)
def room_list(bot, message):
    config = load_config()
    datapack = {"compress": config["compress"]}
    message_chain = call_ournotes("roomList", datapack)
    feedback(message, message_chain)

#交友登记 - /friend/upload(按QQ号upsert, 一人一条)
def friend_upload(bot, message, parameter):
    if not parameter:
        feedback(message, MessageChain([f"\n[TOMORI]请提供你的游戏ID(数字), 例: 交友登记 123456789 日服"]))
        return
    tokens = parameter.split()
    player_id = tokens[0]
    if not player_id.isdigit():
        feedback(message, MessageChain([f"\n[TOMORI]请提供你的游戏ID(数字), 例: 交友登记 123456789 日服"]))
        return
    #服务器可省略(默认港澳台服), 支持短码或中文别名
    server = parse_server(tokens[1]) if len(tokens) > 1 else "tw"
    if server is None:
        feedback(message, MessageChain([f"\n[TOMORI]服务器只支持 {server_hint()}, 例: 交友登记 123456789 日服"]))
        return
    config = load_config()
    datapack = {
        "userId": f"{message.user_id}",
        "userName": get_user_name(message),
        "avatarUrl": get_qq_avatar(message.user_id),
        "playerId": player_id,
        "server": server
    }
    result = call_net(f"{config['ournotes_uri']}/friend/upload", mode="post", data_pack=datapack)
    if result == {}:
        feedback(message, MessageChain(["\n[TOMORI]OurNotes后端连接失败"]))
        return
    if result.get("status") == "success":
        feedback(message, MessageChain([f"\n[TOMORI]{result.get('data', '已记录你的交友信息')}"]))
    else:
        feedback(message, MessageChain([f"\n[TOMORI]登记失败, {result.get('data', '未知错误')}"]))

#删除交友 - /friend/delete(自报QQ号, 弱鉴权)
def friend_delete(bot, message):
    config = load_config()
    result = call_net(f"{config['ournotes_uri']}/friend/delete", mode="post", data_pack={"userId": f"{message.user_id}"})
    if result == {}:
        feedback(message, MessageChain(["\n[TOMORI]OurNotes后端连接失败"]))
        return
    if result.get("status") == "success":
        feedback(message, MessageChain([f"\n[TOMORI]{result.get('data', '已删除你的交友信息')}"]))
    else:
        feedback(message, MessageChain([f"\n[TOMORI]删除失败, {result.get('data', '未知错误')}"]))

#交友列表 - /friend/list
def friend_list(bot, message):
    config = load_config()
    datapack = {"compress": config["compress"]}
    message_chain = call_ournotes("friend/list", datapack)
    feedback(message, message_chain)
