
# == MC服务器状态查询插件入口 ==

# 由v1(src/plugin/MC服务器状态查询/main.py)迁移至v2插件格式
# 本文件负责指令路由，数据层位于db.py

import os, json, requests, traceback
from OneBotConnecter.types import MessageChain, ImageMessage, ForwardChain, NodeMessage
from OneBotConnecter.loger.log_info import log
from src.core.core_function import read_help_file
from src.plugins.mc_server_status.db import db
from src.tools.reply_message import feedback

api = "https://www.minecraftservers.cn/api/query?ip="

# == 入口 ==

def on_all_case(bot, message) -> bool: #call case including message, poke, request ...
    if "message" in message.event_type:
        return on_msg(bot, message=message)
    return False

def on_msg(bot, message) -> bool: # message
    try:
        raw_message = message.text
        if not raw_message: return False
        places_id = message.scene_id
        shart_order = False
        #==帮助文档==(裸插件ID"MC服务器状态查询"由核心显示帮助文档，避免重复)
        if raw_message in ["MC", "mc", "Mc"]:
            help_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "help.txt")
            message.reply_message(ForwardChain(read_help_file(help_file)))
            return True
        try:
            if "mc" in raw_message.lower():
                shart_order = True
            if raw_message[0:2].lower() == "mc":
                raw_message = raw_message[2:].strip()
            raw_message = raw_message.replace("服务器状态查询", "").strip()
            if raw_message[0] in ["."]: raw_message = raw_message[1:].strip()
        except: pass

        if raw_message[0:5] in ["查询服务器"] or (shart_order and raw_message[0:2] in ["查询"]):
            server_location = raw_message.replace("查询", "").strip()
            server_location = server_location.replace("服务器", "").strip()
            if not server_location:
                servers = db.query("SELECT server_location FROM bind_data WHERE place_id = ?;", (places_id,))
                if not servers:
                    feedback(message, MessageChain(["无绑定记录"]))
                    return True
                chain = ForwardChain("MC服务器状态查询")
                for server in servers:
                    try:
                        result = requests.get(api + server[0], timeout=10)
                        data = json.loads(result.text).get("data", {})
                        chain.add(NodeMessage(content=create_msg(data, server[0]).to_send_message()))
                    except Exception:
                        chain.add(NodeMessage(content=create_msg({}, server[0]).to_send_message()))
                feedback(message, chain)
                return True
            url = api + server_location
            result = requests.get(url, timeout=10)
            if result.status_code != 200:
                feedback(message, MessageChain(["接口连接失败"]))
                return True
            result = json.loads(result.text)
            if not result.get("success", False):
                feedback(message, MessageChain(["查询失败(地址错误/服务器不存在/接口不可用)"]))
                return True
            data = result.get("data", {})
            if not data:
                feedback(message, MessageChain(["空包"]))
                return True
            feedback(message, create_msg(data))
            return True

        elif raw_message[0:5] in ["绑定服务器"] or (shart_order and raw_message[0:2] in ["绑定"]):
            server_location = raw_message.replace("绑定", "").strip()
            server_location = server_location.replace("服务器", "").strip()
            if not server_location:
                feedback(message, MessageChain(["未识别IP"]))
                return True
            url = api + server_location
            result = requests.get(url, timeout=10)
            if result.status_code != 200:
                feedback(message, MessageChain(["接口连接失败"]))
                return True
            result = json.loads(result.text)
            if not result.get("success", False) or not result.get("data", False):
                feedback(message, MessageChain(["地址错误/服务器不存在/接口不可用"]))
                return True
            db.execute("INSERT OR IGNORE INTO bind_data (place_id, server_location) VALUES (?, ?);", (places_id, server_location))
            feedback(message, MessageChain(["绑定成功"]))
            return True

        elif raw_message[0:5] in ["删除服务器"] or (shart_order and raw_message[0:2] in ["删除"]):
            server_location = raw_message.replace("删除", "").strip()
            server_location = server_location.replace("服务器", "").strip()
            if not server_location:
                feedback(message, MessageChain(["未识别IP"]))
                return True
            db.execute("DELETE FROM bind_data WHERE place_id = ? AND server_location = ?;", (places_id, server_location))
            feedback(message, MessageChain(["删除成功"]))
            return True

    except Exception as e:
        tb = e.__traceback__
        formatted_tb = ''.join(traceback.format_tb(tb))
        log(f"[{type(e)}] {e}\n{formatted_tb}")
    return False

def create_msg(data, server_location = "N/A"):
    msg = MessageChain([])
    if not data or not data.get("ip", None):
        msg.add(f"ip: {data.get('ip', server_location)}\n")
        msg.add("查询状态: 失败")
        return msg
    logo = data.get("logo", "N/A")
    if "base64" not in logo:
        logo = "N/A"
    if logo != "N/A":
        logo = logo[logo.find("base64,")+7:]
        msg.add(ImageMessage(f"base64://{logo}"))
    msg.add(f"ip: {data.get('ip', server_location)}\n")
    msg.add(f"目前在线: {data.get('p', 0)}/{data.get('mp', 0)}\n")
    msg.add(f"当日在线最大/最少人数: {data.get('today_max', '0')}/{data.get('today_min', '0')}\n")
    msg.add(f"PING: {data.get('ping', 'N/A')}\n")
    msg.add(f"----------\n")
    msg.add(f"motd:\n{str(data.get('motd', 'N/A')).strip()}\n")
    msg.add(f"----------\n")
    msg.add(f"信息最后更新时间:\n{data.get('last_updated_str', 'N/A')}")
    return msg
