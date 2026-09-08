
# == Tsugu多人模式模块 ==

# ycm(车牌房间列表)/上传车牌

import traceback
from OneBotConnecter.types import MessageChain
from OneBotConnecter.loger.log_info import log
from src.plugins.tsugu_plugin.config import load_config
from src.plugins.tsugu_plugin.call_tsugu import call_tsugu, call_net
from src.tools.reply_message import feedback

#ycm
def self_room_list(bot, message):
    try:
        bangdream_config = load_config()
        uri = f"{bangdream_config['tsugu_uri']}/station/queryAllRoom"
        data = call_net(uri)
        if data == {} or data["status"] != "success":
            message_chain = MessageChain(["\n[TSUGU]茨菇后台连接失败"])
            feedback(message, message_chain)
            return
        datapack = {
            "roomList": data["data"],
            "compress": bangdream_config["compress"]
        }
        mode = "roomList"
        message_chain = call_tsugu(mode, datapack)
        feedback(message, message_chain)
    except Exception as e:
        message_chain = MessageChain(["\n[TSUGU]茨菇后台连接失败"])
        feedback(message, message_chain)
        tb = e.__traceback__
        formatted_tb = ''.join(traceback.format_tb(tb))
        log(f"[{type(e)}] {e}\n{formatted_tb}")
        return
#上传车牌
def self_submit_room_number(bot, message, raw_message):
    raw_message = raw_message[4:].strip()
    try:
        room_number = raw_message.split(" ")
        room_number = room_number[0]
        if (len(room_number) != 5 and len(room_number) != 6) or (not room_number.isdigit()):
            message_chain = MessageChain(["[TSUGU]房间号非法"])
            feedback(message, message_chain)
            return
        raw_message = raw_message.replace(room_number, "").strip()
        datapack = {
            "number": room_number,
            "rawMessage": f"{room_number} {raw_message}",
            "platform": "qq",
            "userId": f"{message.user_id}",
            "userName": f"{message.raw_data.get('sender', {}).get('nickname', '')}",
            "avatarUrl": f"https://q1.qlogo.cn/g?b=qq&nk={message.user_id}&s=640",
            "time": 120
        }
        bangdream_config = load_config()
        uri = f"{bangdream_config['tsugu_uri']}/station/submitRoomNumber"
        result = call_net(uri, mode="post", data_pack = datapack)
        if result['status'] == "success":
            message_chain = MessageChain([f"[TSUGU]已转接茨菇:\n{result['data']}"])
            feedback(message, message_chain)
        else:
            message_chain = MessageChain([f"[TSUGU]上传失败,{result['data']}"])
            feedback(message, message_chain)
    except:
        message_chain = MessageChain(["\n[TSUGU]茨菇后台连接失败"])
        feedback(message, message_chain)
