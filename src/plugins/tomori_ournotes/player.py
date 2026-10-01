
# == Tomori OurNotes玩家模块 ==

# 查排行(songRanking: 该曲前十用户与出分, 单服)
# 查玩家(searchPlayer: 玩家档案图, 单服, 服务器可由ID首位推断)

from OneBotConnecter.types import MessageChain
from src.plugins.tomori_ournotes.config import load_config
from src.plugins.tomori_ournotes.call_ournotes import call_ournotes, split_servers, server_hint, server_display
from src.plugins.tomori_ournotes.reply import feedback

#查排行 - /songRanking(单服)
def song_ranking(bot, message, parameter):
    tokens, servers = split_servers(parameter.split())
    if len(tokens) != 1 or not tokens[0].isdigit():
        send_message = MessageChain(["\n[TOMORI]查询该曲的排行榜(前十用户与出分)"])
        send_message.add("\n可用参数:")
        send_message.add("\n-------------------------")
        send_message.add("\n[歌曲ID (服务器)]")
        send_message.add(f"\n服务器: {server_hint()}")
        send_message.add("\n例: 查排行 100001 jp\n")
        feedback(message, send_message)
        return
    config = load_config()
    datapack = {
        "songId": int(tokens[0]),
        "server": servers[0],
        "compress": config["compress"]
    }
    send_message = MessageChain([f"\n[TOMORI]排行榜 [{server_display(servers[0])}]"])
    send_message.add(call_ournotes("songRanking", datapack))
    feedback(message, send_message)

#查玩家 - /searchPlayer(单服; 未指定服务器时后端按ID首位推断: 2→港澳台/3→国际/4→韩)
def search_player(bot, message, parameter):
    tokens, servers = split_servers(parameter.split(), default_servers=[])
    if len(tokens) != 1 or not tokens[0].isdigit():
        send_message = MessageChain(["\n[TOMORI]查询Our Notes账号档案(最爱卡面/名称/等级/应援数等)"])
        send_message.add("\n可用参数:")
        send_message.add("\n-------------------------")
        send_message.add("\n[玩家ID (服务器)]")
        send_message.add(f"\n服务器: {server_hint()}(可省略, 按ID首位推断; 日服须显式指定)")
        send_message.add("\n例: 查玩家 2000000000 jp\n")
        feedback(message, send_message)
        return
    config = load_config()
    datapack = {
        "playerId": tokens[0],
        "compress": config["compress"]
    }
    #未显式指定时不传server, 交由后端按ID首位推断
    if servers:
        datapack["server"] = servers[0]
    send_message = MessageChain([f"\n[TOMORI]玩家档案 [{server_display(servers[0]) if servers else '按ID推断'}]"])
    send_message.add(call_ournotes("searchPlayer", datapack))
    feedback(message, send_message)
