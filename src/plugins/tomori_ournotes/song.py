
# == Tomori OurNotes歌曲模块 ==

# 查曲(searchSong) / 曲表(songMeta) / 随机曲(songRandom)

from OneBotConnecter.types import MessageChain
from OneBotConnecter.loger.log_info import log
from src.plugins.tomori_ournotes.config import load_config
from src.plugins.tomori_ournotes.call_ournotes import call_ournotes, call_fuzzy_search, split_servers, server_hint, servers_display
from src.plugins.tomori_ournotes.reply import feedback

#查曲(静态实体: 可多服对比, 如 "查曲 迷星叫 tw jp")
def sreach_song(bot, message, parameter):
    tokens, servers = split_servers(parameter.split())
    text = " ".join(tokens)
    if not text:
        send_message = MessageChain(["\n[TOMORI]查询Our Notes歌曲信息(整数ID→详情, 否则→搜索列表)"])
        send_message.add("\n可用参数:")
        send_message.add("\n-------------------------")
        send_message.add("\n[(ID/歌名) (服务器...)]")
        send_message.add(f"\n服务器: {server_hint()}")
        send_message.add("\n多服写多个(如 tw jp), 默认港澳台服")
        send_message.add("\n例: tomori查曲 迷星叫 jp\n")
        feedback(message, send_message)
        return
    config = load_config()
    if text.isdigit():
        datapack = {
            "displayedServerList": servers,
            "text": text,
            "compress": config["compress"]
        }
    else:
        result = call_fuzzy_search(text, servers)
        if result == {} or result.get("status") != "success":
            feedback(message, MessageChain(["\n[TOMORI]OurNotes后端连接失败"]))
            return
        datapack = {
            "displayedServerList": servers,
            "fuzzySearchResult": result["data"],
            "compress": config["compress"]
        }
    message_chain = call_ournotes("searchSong", datapack)
    feedback(message, message_chain)

#曲效率(歌曲meta效率排行: 击奏live/自由live两榜各前15张谱面, 可多服只影响显示语言)
def song_meta(bot, message, parameter):
    tokens, servers = split_servers(parameter.split())
    if tokens:
        feedback(message, MessageChain([f"\n[TOMORI]服务器只支持 {server_hint()}, 例: 曲效率 tw jp"]))
        return
    log(f"[TOMORI]曲效率: {servers_display(servers)}")
    config = load_config()
    datapack = {
        "displayedServerList": servers,
        "mainServer": servers[0],
        "compress": config["compress"]
    }
    message_chain = call_ournotes("songMeta", datapack)
    feedback(message, message_chain)

#随机曲(单服, 取服务器列表首个; 关键词可选)
def random_song(bot, message, parameter):
    tokens, servers = split_servers(parameter.split())
    config = load_config()
    datapack = {
        "displayedServerList": servers,
        "mainServer": servers[0],
        "compress": config["compress"]
    }
    text = " ".join(tokens)
    if text and not text.isdigit():
        datapack["text"] = text
    message_chain = call_ournotes("songRandom", datapack)
    feedback(message, message_chain)
