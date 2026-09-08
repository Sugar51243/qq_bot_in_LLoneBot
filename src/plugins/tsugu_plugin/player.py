
# == Tsugu玩家模块 ==

# 查玩家/绑定玩家/绑定记录/删除绑定/玩家状态

import traceback
from OneBotConnecter.types import MessageChain
from OneBotConnecter.loger.log_info import log
from src.plugins.tsugu_plugin.config import load_config
from src.plugins.tsugu_plugin.db import db
from src.plugins.tsugu_plugin.call_tsugu import call_tsugu, call_net
from src.tools.reply_message import feedback

#查玩家
def check_player_info(bot, message, raw_message):
    raw_message = raw_message[3:].strip()
    if len(raw_message) <= 0:
        send_message = MessageChain(["\n[TSUGU]查询玩家信息图片"])
        send_message.add("\n可用参数:")
        send_message.add("\n-------------------------")
        send_message.add("\n[ID] [server]")
        send_message.add("\n例:114514 jp")
        feedback(message, send_message)
        return
    server = "cn"
    player_id = raw_message
    if raw_message[-2:].lower() in ["jp", "en", "tw", "cn", "kr"]:
        server = raw_message[-2:].lower()
        player_id = raw_message[:-2].strip()
    try:
        if not player_id.isdigit():
            message_chain = MessageChain(["[TSUGU]参数错误"])
            feedback(message, message_chain)
            return
        self_search_player(bot, message, player_id, server)
    except:
        message_chain = MessageChain(["[TSUGU]查询失败"])
        feedback(message, message_chain)
#茨菇查玩家
def self_search_player(bot, message, player_id, server):
    playerID = int(player_id)
    try:
        serverSet = {"jp":0, "en":1, "tw":2, "cn":3, "kr":4}
        server = serverSet[server]
    except: server = 3
    mode = "searchPlayer"
    bangdream_config = load_config()
    datapack = {
        "playerId": playerID,
        "mainServer": server,
        "useEasyBG": bangdream_config["useEasyBG"],
        "compress": bangdream_config["compress"]
    }
    message_chain = call_tsugu(mode, datapack)
    feedback(message, message_chain)
#玩家状态
def get_play_info(bot, message, user_id, id):
    #读取玩家绑定记录
    users = db.query("SELECT acc, server FROM user_binding WHERE user_id = ? ORDER BY id;", (str(user_id),))
    try:
        user = users[id]
    except:
        message_chain = MessageChain(["[TSUGU]无绑定记录"])
        feedback(message, message_chain)
        return
    #查玩家资料
    self_search_player(bot, message, user[0], user[1])
    return
#绑定玩家
def bing_user(bot, message, raw_message):
    raw_message = raw_message[4:].strip()
    if len(raw_message) <= 0:
        send_message = MessageChain(["\n[TSUGU]绑定玩家信息"])
        send_message.add("\n可用参数:")
        send_message.add("\n-------------------------")
        send_message.add("\n[ID] [server]")
        send_message.add("\n例:114514 jp")
        feedback(message, send_message)
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
        data = call_net(uri)
        if data == {}:
            message_chain = MessageChain(["\n[TSUGU]小生物网络连接出现问题,请等下再试"])
            feedback(message, message_chain)
            log(f"网络连接出现问题")
        elif data["data"]["profile"] != None:
            #检查数据未绑定
            exists = db.query_one("SELECT id FROM user_binding WHERE user_id = ? AND acc = ? AND server = ?;", (str(message.user_id), str(player_id), str(server)))
            if exists:
                message_chain = MessageChain(["[TSUGU]账号已存在，请勿重复储存"])
                feedback(message, message_chain)
                return
            #更新
            db.execute("INSERT OR IGNORE INTO user_binding (user_id, acc, server) VALUES (?, ?, ?);", (str(message.user_id), str(player_id), str(server)))
            #反馈
            message_chain = MessageChain(["[TSUGU]账号储存成功"])
            feedback(message, message_chain)
            checkUserBinded(bot, message)
            return
        else:
            feedback(message, MessageChain(["[TSUGU]账号不存在"]))
            log(data["data"])
    except:
        message_chain = MessageChain(["参数错误"])
        feedback(message, message_chain)
#绑定记录
def checkUserBinded(bot, message):
    message_chain = MessageChain(["\n"])
    users = db.query("SELECT acc, server FROM user_binding WHERE user_id = ? ORDER BY id;", (str(message.user_id),))
    if len(users) <= 0:
        message_chain.add(MessageChain(["[TSUGU]无绑定记录"]))
    else:
        message_chain.add(MessageChain(["[TSUGU]绑定记录:"]))
        for i in range(len(users)):
            message_chain.add(MessageChain([f"\n{str(i+1)}. {users[i][0]} {users[i][1]}"]))
    feedback(message, message_chain)
#删除绑定
def delUserBinded(bot, message, raw_message):
    raw_message = raw_message[4:].strip()
    try:
        users = db.query("SELECT id, acc, server FROM user_binding WHERE user_id = ? ORDER BY id;", (str(message.user_id),))
        if raw_message == None:
            raise Exception()
        if not raw_message.isdigit() or raw_message=="0":
            raise Exception()
        if int(raw_message)<=len(users):
            target = users[int(raw_message)-1]
            db.execute("DELETE FROM user_binding WHERE id = ?;", (target[0],))
            message_chain = MessageChain(["[TSUGU]账号删除成功"])
            feedback(message, message_chain)
            checkUserBinded(bot, message)
    except Exception as e:
        message_chain = MessageChain(["[TSUGU]参数错误"])
        feedback(message, message_chain)
        tb = e.__traceback__
        formatted_tb = ''.join(traceback.format_tb(tb))
        log(f"[{type(e)}] {e}\n{formatted_tb}")
