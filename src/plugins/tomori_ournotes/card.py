
# == Tomori OurNotes卡片模块 ==

# 查卡(searchCard, 整合角色卡+支援卡) / 查角色卡(searchMemberCard) / 查支援卡(searchSupportCard)
# 查卡面(getCardIllustration) / 查角色(searchCharacter)
# 查卡池(searchGacha) / 查活动(searchEvent) / 抽卡(gachaSimulate)

from OneBotConnecter.types import MessageChain
from src.plugins.tomori_ournotes.config import load_config
from src.plugins.tomori_ournotes.call_ournotes import call_ournotes, call_fuzzy_search, split_servers, server_hint, servers_display
from src.plugins.tomori_ournotes.reply import feedback

#卡种关键词(参数中的可选词, 与后端cardType对应)
CARD_TYPE_KEY_SET = {"member": "member", "support": "support", "auto": "auto", "角色卡": "member", "成员卡": "member", "支援卡": "support", "留影": "support"}

#解析卡种/服务器参数, 返回(剩余文本, cardType或None, 服务器列表)
def parse_card_arguments(parameter: str):
    tokens, servers = split_servers(parameter.split())
    card_type = None
    if tokens and tokens[-1] in CARD_TYPE_KEY_SET:
        card_type = CARD_TYPE_KEY_SET[tokens[-1]]
        tokens = tokens[:-1]
    return " ".join(tokens), card_type, servers

#查卡(整合: 角色卡+支援卡; 可多服)
def sreach_card(bot, message, parameter):
    if not parameter:
        send_message = MessageChain(["\n[TOMORI]查询Our Notes卡片信息(角色卡+支援卡, 整数ID→详情, 否则→搜索列表)"])
        send_message.add("\n可用参数:")
        send_message.add("\n-------------------------")
        send_message.add("\n[(ID/卡名) (卡种) (服务器...)]")
        send_message.add("\n卡种: 角色卡/支援卡 (默认自动)")
        send_message.add(f"\n服务器: {server_hint()}")
        send_message.add("\n例: tomori查卡 高松灯 角色卡 jp\n")
        feedback(message, send_message)
        return
    text, card_type, servers = parse_card_arguments(parameter)
    sreach_card_common(bot, message, text, "searchCard", card_type, servers)

#查角色卡(仅成员卡)
def sreach_member_card(bot, message, parameter):
    if not parameter:
        send_message = MessageChain(["\n[TOMORI]查询Our Notes角色卡(成员卡)信息(整数ID→详情, 否则→搜索列表)"])
        send_message.add("\n可用参数:")
        send_message.add("\n-------------------------")
        send_message.add("\n[(ID/卡名) (服务器...)]")
        send_message.add(f"\n服务器: {server_hint()}")
        send_message.add("\n例: tomori查角色卡 高松灯 jp\n")
        feedback(message, send_message)
        return
    text, _, servers = parse_card_arguments(parameter)
    sreach_card_common(bot, message, text, "searchMemberCard", None, servers)

#查支援卡(仅支援卡)
def sreach_support_card(bot, message, parameter):
    if not parameter:
        send_message = MessageChain(["\n[TOMORI]查询Our Notes支援卡(留影)信息(整数ID→详情, 否则→搜索列表)"])
        send_message.add("\n可用参数:")
        send_message.add("\n-------------------------")
        send_message.add("\n[(ID/卡名) (服务器...)]")
        send_message.add(f"\n服务器: {server_hint()}")
        send_message.add("\n例: 查支援卡 高松灯 jp\n")
        feedback(message, send_message)
        return
    text, _, servers = parse_card_arguments(parameter)
    sreach_card_common(bot, message, text, "searchSupportCard", None, servers)

#查卡公共流程
def sreach_card_common(bot, message, text, mode, card_type, servers):
    if not text:
        feedback(message, MessageChain(["\n[TOMORI]请提供卡ID或卡名"]))
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
    #整合入口可传cardType; 固定种类入口不传(searchMemberCard/searchSupportCard不接受该字段)
    if card_type:
        datapack["cardType"] = card_type
    message_chain = call_ournotes(mode, datapack)
    feedback(message, message_chain)

#查卡面(原图; 单服, 取首个收录该卡的服务器)
def card_face(bot, message, parameter):
    text, card_type, servers = parse_card_arguments(parameter)
    if not text or not text.isdigit():
        feedback(message, MessageChain(["\n[TOMORI]请提供数字卡ID, 例: tomori查卡面 1 角色卡 jp"]))
        return
    datapack = {
        "displayedServerList": servers,
        "cardId": int(text)
    }
    if card_type:
        datapack["cardType"] = card_type
    message_chain = call_ournotes("getCardIllustration", datapack)
    feedback(message, message_chain)

#查角色(可多服)
def sreach_character(bot, message, parameter):
    if not parameter:
        send_message = MessageChain(["\n[TOMORI]查询Our Notes角色信息(整数ID→详情, 否则→搜索列表)"])
        send_message.add("\n可用参数:")
        send_message.add("\n-------------------------")
        send_message.add("\n[(ID/角色名) (服务器...)]")
        send_message.add(f"\n服务器: {server_hint()}")
        send_message.add("\n例: tomori查角色 高松灯 jp\n")
        feedback(message, send_message)
        return
    text, _, servers = parse_card_arguments(parameter)
    if not text:
        feedback(message, MessageChain(["\n[TOMORI]请提供角色ID或角色名"]))
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
    message_chain = call_ournotes("searchCharacter", datapack)
    feedback(message, message_chain)

#查卡池(可多服)
def sreach_gacha(bot, message, parameter):
    tokens, servers = split_servers(parameter.split())
    if len(tokens) != 1 or not tokens[0].isdigit():
        feedback(message, MessageChain([f"\n[TOMORI]请提供数字卡池ID(服务器可选: {server_hint()}), 例: tomori查卡池 1 jp"]))
        return
    config = load_config()
    datapack = {
        "displayedServerList": servers,
        "gachaId": int(tokens[0]),
        "compress": config["compress"]
    }
    message_chain = call_ournotes("searchGacha", datapack)
    feedback(message, message_chain)

#查活动(可多服)
def sreach_event(bot, message, parameter):
    if not parameter:
        send_message = MessageChain(["\n[TOMORI]查询Our Notes活动信息(整数ID→详情, 否则→搜索列表)"])
        send_message.add("\n可用参数:")
        send_message.add("\n-------------------------")
        send_message.add("\n[(ID/活动名) (服务器...)]")
        send_message.add(f"\n服务器: {server_hint()}")
        send_message.add("\n例: tomori查活动 活动名\n")
        feedback(message, send_message)
        return
    text, _, servers = parse_card_arguments(parameter)
    if not text:
        feedback(message, MessageChain(["\n[TOMORI]请提供活动ID或活动名"]))
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
    message_chain = call_ournotes("searchEvent", datapack)
    feedback(message, message_chain)

#抽卡模拟(单服)
def gacha_simulate(bot, message, parameter):
    tokens, servers = split_servers(parameter.split())
    times = None
    gacha_id = None
    for token in tokens:
        if token.isdigit():
            if times is None:
                times = int(token)
            elif gacha_id is None:
                gacha_id = int(token)
    config = load_config()
    datapack = {
        "mainServer": servers[0],
        "compress": config["compress"]
    }
    if times and times > 0:
        datapack["times"] = times
    if gacha_id:
        datapack["gachaId"] = gacha_id
    message_chain = call_ournotes("gachaSimulate", datapack)
    feedback(message, message_chain)
