
# == Tomori OurNotes活动模块 ==

# 活动榜线(eventRanking: 该活动各乐曲榜前十用户与出分, 单服)
# 活动推荐(eventRecommend: 按目标评级SS/S/A/B列所需综合力最低的前10张谱面, 单服)
# 两者活动ID均可省略(取该服当前开放的活动)

from OneBotConnecter.types import MessageChain
from src.plugins.tomori_ournotes.config import load_config
from src.plugins.tomori_ournotes.call_ournotes import call_ournotes, split_servers, server_hint, server_display
from src.plugins.tomori_ournotes.reply import feedback

#解析活动ID(可选)与服务器, 返回(event_id或None, servers, 非法token列表)
def _parse_event_parameters(parameter: str):
    tokens, servers = split_servers(parameter.split())
    event_id = None
    invalid = []
    for token in tokens:
        if token.isdigit() and event_id is None:
            event_id = token
        else:
            invalid.append(token)
    return event_id, servers, invalid

#活动榜线 - /eventRanking(不传活动ID时取该服当前开放的活动)
def event_ranking(bot, message, parameter):
    event_id, servers, invalid = _parse_event_parameters(parameter)
    if invalid:
        feedback(message, MessageChain([f"\n[TOMORI]参数只支持活动ID与服务器({server_hint()}), 例: 活动榜线 123 jp"]))
        return
    datapack = {
        "server": servers[0],
        "compress": load_config()["compress"]
    }
    if event_id is not None:
        datapack["eventId"] = int(event_id)
    title = f"\n[TOMORI]活动榜线 [{server_display(servers[0])}]"
    if event_id is not None:
        title += f" 活动ID: {event_id}"
    else:
        title += " 当前活动"
    send_message = MessageChain([title])
    send_message.add(call_ournotes("eventRanking", datapack))
    feedback(message, send_message)

#活动推荐 - /eventRecommend(不传活动ID时取该服当前开放的活动)
def event_recommend(bot, message, parameter):
    event_id, servers, invalid = _parse_event_parameters(parameter)
    if invalid:
        feedback(message, MessageChain([f"\n[TOMORI]参数只支持活动ID与服务器({server_hint()}), 例: 活动推荐 123 jp"]))
        return
    datapack = {
        "server": servers[0],
        "compress": load_config()["compress"]
    }
    if event_id is not None:
        datapack["eventId"] = int(event_id)
    title = f"\n[TOMORI]活动推荐曲 [{server_display(servers[0])}]"
    if event_id is not None:
        title += f" 活动ID: {event_id}"
    else:
        title += " 当前活动"
    send_message = MessageChain([title])
    send_message.add(call_ournotes("eventRecommend", datapack))
    feedback(message, send_message)
