
# == 猪人插件入口 ==

# 由v1(src/plugin/猪人/main.py)迁移至v2插件格式
# 本文件负责指令流程，数据层位于db.py

import unicodedata
from OneBotConnecter.types import MessageChain
from OneBotConnecter.loger.log_info import log
from src.plugins.pig.db import db, read_id

# == 入口 ==

def on_all_case(bot, message) -> bool: #call case including message, poke, request ...
    if "message" in message.event_type:
        return on_msg(bot, message=message)
    return False

def on_msg(bot, message) -> bool: # message
    if message.event_type != "group_message": return False
    raw_message = message.text
    if not raw_message: return False
    sender = str(message.user_id)
    #读取数据
    package = {key: times for key, times in db.query("SELECT emoji, times FROM record WHERE user_id = ?;", (sender,))}
    keys = list(package.keys())
    for key in keys.copy():
        row = db.query_one("SELECT enabled FROM permissions WHERE user_id = ? AND emoji = ?;", (sender, key))
        enabled = row[0] if row else True
        if not enabled: continue
        if is_emoji(key): id = read_id(key)
        else: id = key
        if id == None: continue
        bot.set_msg_emoji_like(int(message.raw_data.get("message_id", 0)), id)
        times = package.get(key, 0)
        times -= 1
        if times <= 0: package.pop(key)
        else: package.update({key: times})
    for key, times in package.items():
        db.execute("INSERT OR REPLACE INTO record (user_id, emoji, times) VALUES (?, ?, ?);", (sender, key, times))
    #被pop的键需要同步删除(对应v1中直接改写整个record字典并dump)
    if package:
        placeholders = ",".join("?" for _ in package)
        db.execute(f"DELETE FROM record WHERE user_id = ? AND emoji NOT IN ({placeholders})", (sender, *package.keys()))
    else:
        db.execute("DELETE FROM record WHERE user_id = ?;", (sender,))
    #
    target_id, target_msg, face_ids = get_target(bot, message, raw_message)
    emojis = extract_emojis(raw_message)
    if face_ids or emojis: log(f"Face_ids: {face_ids} | Emojis: {emojis}")
    if target_id or target_msg: log(f"target_id: {target_id} | target_msg: {target_msg}")
    emojis_copy = emojis.copy()
    for em in emojis_copy.copy():
        #init
        if not read_id(em):
            emojis.remove(em)
            emojis_copy.remove(em)
            continue
        if db.query_one("SELECT emoji FROM config WHERE emoji = ?;", (em,)) == None:
            db.execute("INSERT OR IGNORE INTO config (emoji, enabled) VALUES (?, 1);", (em,))
        if db.query_one("SELECT emoji FROM permissions WHERE user_id = ? AND emoji = ?;", (sender, em)) == None:
            db.execute("INSERT OR IGNORE INTO permissions (user_id, emoji, enabled) VALUES (?, ?, 1);", (sender, em))
        #stop
        if "停" in raw_message and str(sender) in [str(owner_id) for owner_id in bot.bot.owner]:
            db.execute("UPDATE config SET enabled = 0 WHERE emoji = ?;", (em,))
        #start
        elif "开" in raw_message and str(sender) in [str(owner_id) for owner_id in bot.bot.owner]:
            db.execute("UPDATE config SET enabled = 1 WHERE emoji = ?;", (em,))
        #df
        if "不防" in raw_message:
            db.execute("UPDATE permissions SET enabled = 1 WHERE user_id = ? AND emoji = ?;", (sender, em))
        elif "防" in raw_message:
            db.execute("UPDATE permissions SET enabled = 0 WHERE user_id = ? AND emoji = ?;", (sender, em))
        #remove
        row = db.query_one("SELECT enabled FROM config WHERE emoji = ?;", (em,))
        if row != None and not row[0]: emojis.remove(em)
    #
    if "不防" in raw_message and emojis_copy:
        feedback_msg = MessageChain([f"已关闭对{emojis_copy}的防御"])
        message.reply_message(feedback_msg)
    elif "防" in raw_message and emojis_copy:
        feedback_msg = MessageChain([f"已开启对{emojis_copy}的防御"])
        message.reply_message(feedback_msg)
    if "停" in raw_message and str(sender) in [str(owner_id) for owner_id in bot.bot.owner] and emojis_copy:
        feedback_msg = MessageChain([f"已停止对{emojis_copy}的功能适配"])
        message.reply_message(feedback_msg)
    elif "开" in raw_message and str(sender) in [str(owner_id) for owner_id in bot.bot.owner] and emojis_copy:
        feedback_msg = MessageChain([f"已开启对{emojis_copy}的功能适配"])
        message.reply_message(feedback_msg)
    #
    if face_ids or emojis: log(f"Filtered Face_ids: {face_ids} | Emojis: {emojis}")
    if (not target_id and not target_msg) or (not emojis and not face_ids): return False
    #
    for em in emojis:
        if target_msg: bot.set_msg_emoji_like(int(target_msg[0]), read_id(em))
        for qqid in target_id:
            if "不" in raw_message:
                db.execute("DELETE FROM record WHERE user_id = ? AND emoji = ?;", (qqid, em))
            else:
                times = db.query_one("SELECT times FROM record WHERE user_id = ? AND emoji = ?;", (qqid, em))
                times = (times[0] if times else 0) + 2
                db.execute("INSERT OR REPLACE INTO record (user_id, emoji, times) VALUES (?, ?, ?);", (qqid, em, times))
    for face_id in face_ids:
        if target_msg: bot.set_msg_emoji_like(int(target_msg[0]), face_id)
        for qqid in target_id:
            if "不" in raw_message:
                db.execute("DELETE FROM record WHERE user_id = ? AND emoji = ?;", (qqid, face_id))
            else:
                times = db.query_one("SELECT times FROM record WHERE user_id = ? AND emoji = ?;", (qqid, face_id))
                times = (times[0] if times else 0) + 2
                db.execute("INSERT OR REPLACE INTO record (user_id, emoji, times) VALUES (?, ?, ?);", (qqid, face_id, times))
    log(f"record_file updated: [{target_id}]")
    return True


def get_target(bot, message, raw_message):
    target_id = []
    target_msg = []
    face_id = []
    for msg in message.message:
        if msg.type == "at":
            qqid = str(msg.data.qq)
            if not qqid == str(bot.bot.user_id) and qqid.isdigit(): target_id.append(qqid)
        elif msg.type == "face":
            id = str(msg.data.id)
            face_id.append(id)
        elif msg.type == "reply":
            msg_id = str(msg.data.id)
            target_msg.append(msg_id)
    return target_id, target_msg, face_id

def is_emoji(char):
    return unicodedata.category(char) == "So"

def extract_emojis(text):
    emojis = [c for c in text if is_emoji(c)]
    return emojis
