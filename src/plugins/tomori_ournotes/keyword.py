
# == Tomori OurNotes关键词模块 ==

# 新增关键词(keyword/upload) / 删除关键词(keyword/delete)
# 为角色/角色卡/支援卡/歌曲挂一个便于检索的别名(关键词参与模糊搜索)
# 依赖后端MongoDB(ENABLE_DB=true), 未启用时后端返回域内错误并原样转发

from OneBotConnecter.types import MessageChain
from src.plugins.tomori_ournotes.config import load_config
from src.plugins.tomori_ournotes.call_ournotes import call_net
from src.plugins.tomori_ournotes.reply import feedback

#实体类型关键词 → 后端entityType
KEYWORD_TYPE_KEY_SET = {
    "角色": "character", "character": "character",
    "角色卡": "card", "成员卡": "card", "card": "card",
    "支援卡": "supportCard", "留影": "supportCard", "supportcard": "supportCard",
    "歌曲": "song", "song": "song",
}

#关键词长度上限(与后端MAX_KEYWORD_LENGTH一致)
MAX_KEYWORD_LENGTH = 32

#解析关键词参数, 返回(entity_type, entity_id, keyword, 错误文案)
def _parse_keyword_parameters(parameter: str):
    tokens = parameter.split()
    if len(tokens) < 3:
        return None, None, None, "参数不足"
    entity_type = KEYWORD_TYPE_KEY_SET.get(tokens[0].lower())
    if entity_type is None:
        return None, None, None, "类型只支持 角色/角色卡/支援卡/歌曲"
    entity_id = tokens[1]
    if not entity_id.isdigit() or int(entity_id) < 1:
        return None, None, None, "请提供数字实体ID"
    keyword = " ".join(tokens[2:]).strip()
    if not keyword:
        return None, None, None, "请提供关键词"
    if len(keyword) > MAX_KEYWORD_LENGTH:
        return None, None, None, f"关键词过长(上限{MAX_KEYWORD_LENGTH}字)"
    return entity_type, int(entity_id), keyword, None

#关键词操作帮助
def _keyword_help(action: str, example: str) -> MessageChain:
    send_message = MessageChain([f"\n[TOMORI]{action}关键词(为角色/角色卡/支援卡/歌曲挂检索别名)"])
    send_message.add("\n可用参数:")
    send_message.add("\n-------------------------")
    send_message.add("\n[类型] [实体ID] [关键词]")
    send_message.add("\n类型: 角色/角色卡/支援卡/歌曲")
    send_message.add(f"\n例: {example}\n")
    return send_message

#新增关键词 - /keyword/upload(弱鉴权: 以QQ号留痕)
def add_keyword(bot, message, parameter):
    entity_type, entity_id, keyword, error = _parse_keyword_parameters(parameter)
    if error:
        send_message = _keyword_help("新增", "新增关键词 歌曲 100001 迷星叫")
        if parameter.strip():
            send_message.add(f"\n({error})\n")
        feedback(message, send_message)
        return
    config = load_config()
    result = call_net(f"{config['ournotes_uri']}/keyword/upload", mode="post", data_pack={
        "userId": f"{message.user_id}",
        "entityType": entity_type,
        "entityId": entity_id,
        "keyword": keyword
    })
    if result == {}:
        feedback(message, MessageChain(["\n[TOMORI]OurNotes后端连接失败"]))
        return
    if result.get("status") == "success":
        feedback(message, MessageChain([f"\n[TOMORI]{result.get('data', '已添加关键词')}"]))
    else:
        feedback(message, MessageChain([f"\n[TOMORI]添加失败, {result.get('data', '未知错误')}"]))

#删除关键词 - /keyword/delete(只能删自己上传的)
def delete_keyword(bot, message, parameter):
    entity_type, entity_id, keyword, error = _parse_keyword_parameters(parameter)
    if error:
        send_message = _keyword_help("删除", "删除关键词 歌曲 100001 迷星叫")
        if parameter.strip():
            send_message.add(f"\n({error})\n")
        feedback(message, send_message)
        return
    config = load_config()
    result = call_net(f"{config['ournotes_uri']}/keyword/delete", mode="post", data_pack={
        "userId": f"{message.user_id}",
        "entityType": entity_type,
        "entityId": entity_id,
        "keyword": keyword
    })
    if result == {}:
        feedback(message, MessageChain(["\n[TOMORI]OurNotes后端连接失败"]))
        return
    if result.get("status") == "success":
        feedback(message, MessageChain([f"\n[TOMORI]{result.get('data', '已删除该关键词')}"]))
    else:
        feedback(message, MessageChain([f"\n[TOMORI]删除失败, {result.get('data', '未知错误')}"]))
