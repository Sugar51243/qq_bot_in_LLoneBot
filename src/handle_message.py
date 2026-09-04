
from src.Information_interpreter.message_interpreter import interpret_message
from src.config_reader.config_reader import read_bot_config


def handle_message(bot, message):
    config = read_bot_config()
    ban_user = config.get("ban_user", [])
    ban_group = config.get("ban_group", [])
    if message.user_id in ban_user or message.raw_data.get("group_id", None) in ban_group: return
    message = interpret_message(message=message, bot=bot)
    print(message.command)
    ...