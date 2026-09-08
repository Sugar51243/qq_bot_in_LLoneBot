
# == 每日老婆插件入口 ==

# 由v1(src/plugin/jrlp/main.py)迁移至v2插件格式
# 本文件负责指令路由与配对逻辑，数据层位于db.py

import random
from datetime import date
from OneBotConnecter.types import MessageChain, ImageMessage, AtMessage
from OneBotConnecter.loger.log_info import log, error
from src.core.register import sreach_enabled_plugin
from src.db_handler.plugin_db import get_plugin_state
from src.plugins.jrlp.db import db
from src.plugins.score.scores import get_user_score, reduce_score
from src.tools.reply_message import feedback

# == 跨消息状态 ==
state = get_plugin_state("每日老婆")
if "pairing" not in state: state["pairing"] = [] #配对锁

def pairing() -> list:
    return state["pairing"]

# == 入口 ==

def on_all_case(bot, message) -> bool: #call case including message, poke, request ...
    if "message" in message.event_type:
        return on_msg(bot, message=message)
    return False

def on_msg(bot, message) -> bool: # message
    if message.event_type != "group_message": return False
    raw_message = message.text
    if not raw_message: return False
    # == 今日老婆 ==
    #jrlp为功能指令(插件ID为"每日老婆"，两者不冲突)
    if raw_message in ["jrlp", "今日老婆"]:
        jrlp(bot, message)
        return True
    elif raw_message in ["换老婆", "hlp"] and has_jrlp(message)[0]:
        score = get_user_score(message)
        if score["scores"] >= 10:
            if cancal_jrlp(message):
                reduce_score(message, 10)
                jrlp(bot, message)
                return True
        if "小生物积分" in sreach_enabled_plugin(message.scene_id):
            feedback(message, MessageChain(["需要10积分哦！"]))
        else:
            feedback(message, MessageChain(["不许当DD哦！"]))
        return True
    elif raw_message[0] in ["牛"]:
        n_jrlp(bot, message)
        return True
    return False


# == 今日老婆 ==
def jrlp(bot, message):
    hasJrlp, jrlp_id = has_jrlp(message)
    if not hasJrlp:
        if pairing():
            feedback(message, MessageChain(["正在配对"]))
            return
        pairing().append(str(message.user_id))
        try:
            jrlp_id = get_jrlp(bot, message)
        except Exception:
            try:
                jrlp_id = get_jrlp(bot, message)
            except Exception as e:
                error(f"[{type(e)}] {e}")
                feedback(message, MessageChain(["配对时出现错误"]))
                if str(message.user_id) in pairing():
                    pairing().remove(str(message.user_id))
                return
        if str(message.user_id) in pairing():
            pairing().remove(str(message.user_id))
    #发送
    log(f"配对已完成: {jrlp_id}")
    if jrlp_id == None:
        feedback(message, MessageChain(["单身狗"]))
        return
    try:
        log(f"正在获取对象资料")
        info = bot.get_group_member_info(group_id=message.raw_data.get("group_id"), user_id=jrlp_id, no_cache=True)
        log(f"{info.raw_data}")
        card = info.data.card_or_nickname
    except Exception as e:
        error(f"[{type(e)}] {e}")
        card = str(jrlp_id)
    avatar = f"https://q1.qlogo.cn/g?b=qq&nk={jrlp_id}&s=640"
    #发送
    send = f"\n你今天的老婆是: {card}"
    if str(jrlp_id) in [str(owner_id) for owner_id in bot.bot.owner]:
        send = f"\n你今天的老公是: {card}"
    message_chain = MessageChain([send])
    message_chain.add(MessageChain([ImageMessage(avatar)]))
    feedback(message, message_chain)

def n_jrlp(bot, message):
    #get target
    target_id = None
    for i in message.message:
        if i.type == "at":
            target_id = str(i.data.qq)
            break
        elif i.type == "reply":
            msg_id = i.data.id
            reply_msg = bot.get_msg(msg_id)
            try:
                target_id = str(reply_msg.data.sender.user_id)
            except: pass
            break
    if not target_id or target_id == str(message.user_id):
        return
    #own data
    hasJrlp, jrlp_id = has_jrlp(message)
    #target data
    target_hasJrlp, target_jrlp = has_jrlp(message, group_id=str(message.raw_data.get("group_id")), user_id=target_id)
    #check input ok
    if not target_hasJrlp:
        feedback(message, MessageChain(["对方未有老婆"]))
        return
    if jrlp_id == target_id or target_jrlp == str(message.user_id):
        feedback(message, MessageChain(["不能牛/被牛自己哦"]))
        return
    #check score
    score = get_user_score(message)
    need_score = 20 if not hasJrlp else 30
    if score["scores"] < need_score:
        feedback(message, MessageChain([f"需要{need_score}积分哦！"]))
        return
    #cancal_jrlp
    if hasJrlp: #own
        if cancal_jrlp(message):
            reduce_score(message, 10)
    if cancal_jrlp(message, group_id=str(message.raw_data.get("group_id")), user_id=target_id): #target
        reduce_score(message, 20)
    #save
    save_jrlp(message, str(message.raw_data.get("group_id")), str(message.user_id), target_jrlp)
    #reply
    message_chain = MessageChain(["\n你已牛取", AtMessage(target_id), "的老婆"])
    info = bot.get_group_member_info(group_id=message.raw_data.get("group_id"), user_id=target_jrlp, no_cache=True)
    try:
        card = info.data.card_or_nickname
    except:
        card = str(target_jrlp)
    message_chain.add(f"\n你今天的老婆是: {card}")
    if str(target_jrlp) in [str(owner_id) for owner_id in bot.bot.owner]:
        message_chain.add(f"\n你今天的老公是: {card}")
    message_chain.add(MessageChain([ImageMessage(f"https://q1.qlogo.cn/g?b=qq&nk={target_jrlp}&s=640")]))
    feedback(message, message_chain)

def cancal_jrlp(message, group_id=None, user_id=None):
    group_id = str(message.raw_data.get("group_id")) if not group_id else str(group_id)
    user_id = str(message.user_id) if not user_id else str(user_id)
    hasJrlp, jrlp_id = has_jrlp(message, group_id, user_id)
    if not hasJrlp:
        return False
    today = str(date.today())
    db.execute("DELETE FROM pairing WHERE date = ? AND group_id = ? AND (user_id = ? OR user_id = ?);", (today, group_id, user_id, jrlp_id))
    return True

def has_jrlp(message, group_id=None, user_id=None):
    group_id = str(message.raw_data.get("group_id")) if not group_id else str(group_id)
    user_id = str(message.user_id) if not user_id else str(user_id)
    #获取今日日期并查询
    today = str(date.today())
    log(f"今日日期: {today}")
    row = db.query_one("SELECT partner_id FROM pairing WHERE date = ? AND group_id = ? AND user_id = ?;", (today, group_id, user_id))
    if row:
        log(f"配对记录发现: {row[0]}")
        return [True, row[0]]
    log(f"配对记录未发现")
    return [False, None]

def save_jrlp(message, group_id, user_id, jrlp_id):
    today = str(date.today())
    db.execute("INSERT OR REPLACE INTO pairing (date, group_id, user_id, partner_id) VALUES (?, ?, ?, ?);", (today, str(group_id), str(user_id), str(jrlp_id)))
    db.execute("INSERT OR REPLACE INTO pairing (date, group_id, user_id, partner_id) VALUES (?, ?, ?, ?);", (today, str(group_id), str(jrlp_id), str(user_id)))

# 配对
def get_jrlp(bot, message, target_id=None):
    if not target_id:
        log(f"正在获取群成员名单")
        member_list_data = bot.get_group_member_list(group_id=message.raw_data.get("group_id"))
        log(f"{member_list_data.raw_data}")
        member_list: list = member_list_data.data
        log(f"成员名单: {member_list}")
        log(f"正在更新可配对群员名单")
        today = str(date.today())
        paired_rows = db.query("SELECT user_id FROM pairing WHERE date = ? AND group_id = ?;", (today, str(message.raw_data.get("group_id"))))
        paired_ids = [row[0] for row in paired_rows]
        temp = []
        for i in range(len(member_list)):
            if str(member_list[i]['user_id']) != str(message.user_id) and str(member_list[i]['user_id']) not in paired_ids:
                temp.append(member_list[i]['user_id'])
        member_list = temp
        log(f"更新后成员名单: {member_list}")
        #如果全员已配对 则 返回单身信息
        if len(member_list) <= 0:
            log(f"全员已配对")
            return None
        log(f"开始配对")
        idx = random.randint(0,len(member_list)-1)
        log(f"随机数为0-{len(member_list)-1}: {idx}")
        target_id = member_list[idx]
        log(f"配对用户ID为: {target_id}")
    #双方同时更新目录
    save_jrlp(message, str(message.raw_data.get("group_id")), str(message.user_id), str(target_id))
    return target_id
