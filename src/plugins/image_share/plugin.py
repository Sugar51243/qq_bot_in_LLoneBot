
# == 图片分享插件入口 ==

# 由v1(src/plugin/图片分享/main.py)迁移至v2插件格式
# 本文件负责指令路由与上传流程，数据层位于db.py

import os, hashlib, requests, traceback
import random
from OneBotConnecter.types import MessageChain, ImageMessage
from OneBotConnecter.loger.log_info import log
from src.db_handler.plugin_db import get_plugin_state, dumps, loads
from src.plugins.image_share.db import db, image_database
from src.tools.reply_message import feedback

# == 跨消息状态 ==
state = get_plugin_state("图片分享")
if "waiting_upload" not in state: state["waiting_upload"] = {}

def waiting_upload() -> dict:
    return state["waiting_upload"]

# == 入口 ==

def on_all_case(bot, message) -> bool: #call case including message, poke, request ...
    if "message" in message.event_type:
        return on_msg(bot, message=message)
    return False

def on_msg(bot, message) -> bool: # message
    raw_message = message.text
    if not raw_message and str(message.user_id) not in list(waiting_upload().keys()): return False
    if "添加" in raw_message:
        raw_message = raw_message[raw_message.index("添加")+2:].strip()
        if raw_message:
            add_shortcut(bot, message, raw_message)
            return True
    #结束等待上传
    if raw_message.strip() in ["结束"] and str(message.user_id) in list(waiting_upload().keys()):
        del waiting_upload()[str(message.user_id)]
        feedback(message, MessageChain(["已结束上传"]))
        return True
    #等待上传状态中收到图片 => 自动上传
    if str(message.user_id) in list(waiting_upload().keys()):
        image_list = []
        for msg in message.message:
            if msg.type == "image":
                image_list.append(msg.data.__dict__)
        if image_list:
            name_list = waiting_upload()[str(message.user_id)]
            uploaded = upload_image(bot, message, name_list, image_list)
            feedback(message, MessageChain([f"已上传{len(uploaded)}张照片"]))
            return True
    #看看<图片分类名称> => 获取该分类图片
    if raw_message[0:2] == "看看":
        name = raw_message[2:].strip()
        images = getImage(name)
        if images:
            image_id = images[random.randint(0, len(images)-1)]
            feedback(message, ImageMessage(os.path.join(image_database, f"{image_id}.png")))
            return True
        if name:
            feedback(message, MessageChain([f"未有分类[{name}]的图片"]))
            return True
    return False

def add_shortcut(bot, message, raw_message):
    image_list = []
    name_list = []
    for msg in message.message:
        #Image sended
        if msg.type == "image":
            image_list.append(msg.data.__dict__)
        #Image replied
        elif msg.type == "reply":
            target = bot.get_msg(msg.data.id)
            try:
                for target_msg in target.data.message:
                    if target_msg.get("type") == "image":
                        image_list.append(target_msg["data"])
            except: pass
        #Get image name
        elif msg.type == "text":
            if "添加" in msg.data.text:
                raw_message = msg.data.text[msg.data.text.index("添加")+2:].strip()
                name_list = raw_message.split(" ")
    #Image Name missing
    if not name_list:
        feedback(message, MessageChain(["请在“添加”后输入图片分类名称"]))
        return
    #Image missing -> waiting for image
    if not image_list:
        if str(message.user_id) not in list(waiting_upload().keys()):
            waiting_upload()[str(message.user_id)] = name_list
            feedback(message, MessageChain(["正在等待图片信息, 结束上传请发送“结束”"]))
        else:
            feedback(message, MessageChain(["已有正处理分类，请先结束上传"]))
        return
    #Image and Name available -> upload
    uploaded = upload_image(bot, message, name_list, image_list)
    end_upload(message, uploaded)

def upload_image(bot, message, name_list, image_list):
    uploaded = [] #temp to save uploaded image info
    for image in image_list:
        try:
            #get image content
            image = requests.get(image["url"], timeout=10).content
            checksum = hashlib.md5(image).hexdigest()
            id = get_id_by_order()
            #update image info
            image_uploaded = False #temp status to check if image already uploaded
            row = db.query_one("SELECT id FROM image_info WHERE checksum = ?;", (checksum,))
            if row: #image already uploaded
                id = row[0] #update id to the existing one
                image_uploaded = True #set status to True
            if not image_uploaded: #image not uploaded yet, save new image info and image to database
                db.execute("INSERT OR IGNORE INTO image_info (id, names, uploader, checksum) VALUES (?, ?, ?, ?);",
                    (str(id), dumps(name_list), str(message.user_id), checksum))
                #save image to database
                os.makedirs(image_database, exist_ok=True)
                with open(f"{image_database}/{id}.png", "wb") as f:
                    f.write(image)
            else: #image already uploaded, update name list
                row = db.query_one("SELECT names FROM image_info WHERE id = ?;", (str(id),))
                info_names = loads(row[0]) if row else []
                info_names = list(set(info_names + name_list))
                db.execute("UPDATE image_info SET names = ? WHERE id = ?;", (dumps(info_names), str(id)))
            #save shortcut
            for name in name_list:
                db.execute("INSERT OR IGNORE INTO short_cut (name, image_id) VALUES (?, ?);", (str(name), str(id)))
        except Exception as e:
            tb = e.__traceback__
            formatted_tb = ''.join(traceback.format_tb(tb))
            log(f"[{type(e)}] {e}\n{formatted_tb}")
        uploaded.append(id)
    return uploaded

def get_id_by_order():
    row = db.query("SELECT id FROM image_info;")
    if not row:
        return "1"
    else:
        return str(max([int(i[0]) for i in row]) + 1)

def end_upload(message, uploaded):
    if str(message.user_id) in list(waiting_upload().keys()):
        del waiting_upload()[str(message.user_id)]
    uploaded_image_num = len(uploaded)
    if uploaded_image_num > 0:
        feedback_msg = MessageChain([f"已上传 {uploaded_image_num} 张图片"])
    else:
        feedback_msg = MessageChain(["上传失败"])
    feedback(message, feedback_msg)

def getImage(name):
    rows = db.query("SELECT image_id FROM short_cut WHERE name = ?;", (name,))
    return [row[0] for row in rows]
