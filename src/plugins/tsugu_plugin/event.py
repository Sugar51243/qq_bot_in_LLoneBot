
# == Tsugu活动/分数线模块 ==

# 查试炼/查活动/lsycx/ycxall/ycx/分数表

import re
from OneBotConnecter.types import MessageChain
from src.plugins.tsugu_plugin.config import load_config
from src.plugins.tsugu_plugin.call_tsugu import call_tsugu, call_net
from src.tools.reply_message import feedback

#查试炼
def self_event_stage(bot, message, raw_message):
    raw_message = raw_message[3:].strip()
    server = raw_message[-2:]
    try:
        serverSet = {"jp":0, "en":1, "tw":2, "cn":3, "kr":4}
        server = serverSet[server]
        raw_message = raw_message[:-2].strip()
    except: server = 3
    event_id = None
    if len(raw_message)>0:
        if raw_message.isdigit():
            event_id = int(raw_message)
    mode = "eventStage"
    bangdream_config = load_config()
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
    message_chain = call_tsugu(mode, datapack)
    feedback(message, message_chain)
#查活动
def self_search_event(bot, message, raw_message):
    raw_message = raw_message[3:].strip()
    if len(raw_message) <= 0:
        send_message = MessageChain(["\n[TSUGU]查询bangdream活动信息"])
        send_message.add("\n可用参数:")
        send_message.add("\n-------------------------")
        send_message.add("\n同茨菇tsugu")
        feedback(message, send_message)
        return
    bangdream_config = load_config()
    if raw_message.isdigit():
        datapack = {
            "displayedServerList": [3, 0],
            "text": raw_message,
            "useEasyBG": bangdream_config["useEasyBG"],
            "compress": bangdream_config["compress"]
        }
    else:
        uri = f"{bangdream_config[bangdream_config['use_uri']]}/fuzzySearch"
        datapack = {"text": raw_message}
        result = call_net(uri, mode="post", data_pack=datapack)
        if result == {}:
            message_chain = "\n[TSUGU]茨菇连接失败"
            feedback(message, message_chain)
            return
        if result["status"] == "success":
            datapack = {
                "displayedServerList": [3,0],
                "fuzzySearchResult": result["data"],
                "useEasyBG": bangdream_config["useEasyBG"],
                "compress": bangdream_config["compress"]
            }
        else:
            message_chain = "\n[TSUGU]茨菇查询失败"
            feedback(message, message_chain)
            return
    mode = "searchEvent"
    message_chain = call_tsugu(mode, datapack)
    feedback(message, message_chain)
#lsycx
def lsycx(bot, message, raw_message):
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
    bangdream_config = load_config()
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
    message_chain = call_tsugu(mode, datapack)
    feedback(message, message_chain)
#ycxall
def ycxall(bot, message, raw_message):
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
    bangdream_config = load_config()
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
    message_chain = call_tsugu(mode, datapack)
    feedback(message, message_chain)
#ycx
def self_ycx(bot, message, raw_message):
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
    bangdream_config = load_config()
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
    message_chain = call_tsugu(mode, datapack)
    feedback(message, message_chain)
#查询分数表
def self_song_meta(bot, message, server):
    try:
        serverSet = {"jp":0, "en":1, "tw":2, "cn":3, "kr":4}
        server = serverSet[server]
    except: server = 3
    bangdream_config = load_config()
    datapack = {
        "displayedServerList": [3, 0],
        "mainServer": server,
        "compress": bangdream_config["compress"]
    }
    mode = "songMeta"
    message_chain = call_tsugu(mode, datapack)
    feedback(message, message_chain)
