
from src.config_reader.config_reader import read_bot_config

def interpret_message(message, bot):
    config = read_bot_config()
    allowSlash = config.get("allowSlash", True)
    try:
        text = None
        for msg in message.message:
            if msg.type == "text":
                text = msg.data.text
                break
        message.command = text.split(" ")[0]
        if allowSlash and message.command[0] == "/":
            if not message.command[1:]: raise Exception()
            message.command = message.command[1:]
    except Exception as e:
        message.command = None
    return message