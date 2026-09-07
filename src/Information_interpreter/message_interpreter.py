
from src.config_reader.config_reader import read_bot_config
from src.core.register import gen_scene_id

def _at_me(message):
    try:
        for msg in message.message:
            if msg.type != "at": continue
            if msg.data.qq == "all" or str(msg.data.qq) == str(message.self_id):
                return True
    except: pass
    return False

def _reply_me(message, bot):
    try:
        for msg in message.message:
            if msg.type != "reply": continue
            msg_id = msg.data.id
            msg = bot.get_msg(int(msg_id))
            if str(msg.data.user_id) == str(message.self_id): 
                return True
    except: pass
    return False

def _at_other(message):
    try:
        for msg in message.message:
            if msg.type != "at": continue
            if msg.data.qq == "all" or str(msg.data.qq) != str(message.self_id):
                return True
    except: pass
    return False

def _reply_other(message, bot):
    try:
        for msg in message.message:
            if msg.type != "reply": continue
            msg_id = msg.data.id
            msg = bot.get_msg(int(msg_id))
            if str(msg.data.user_id) != str(message.self_id): 
                return True
    except: pass
    return False

def interpret_message(message, bot):
    config = read_bot_config()
    allowSlash = config.get("allowSlash", True)
    message.command = ""
    message.text = ""
    try:
        get_commanded = False
        command = ""
        text = ""
        for msg in message.message:
            if msg.type == "text":
                if not get_commanded:
                    command = msg.data.text.strip()
                    get_commanded = True
                text += f" {msg.data.text.strip()}"
        message.command = command.split(" ")[0]
        message.text = text.strip()
        if allowSlash and message.command[0] == "/":
            if not message.command[1:]: raise Exception()
            message.command = message.command[1:]
            message.text = message.text[1:]
    except: pass
    message.scene_id = gen_scene_id(message=message)
    message.at_me = _at_me(message) or _reply_me(message=message, bot=bot) or "private" in message.scene_id
    message.at_other = _at_other(message) or _reply_other(message=message, bot=bot)
    return message
