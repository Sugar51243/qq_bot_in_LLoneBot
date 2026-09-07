

def on_all_case(bot, message) -> bool: #call case including message, poke, request ...
    if "message" in message.event_type:
        return on_msg(bot, message=message)

def on_msg(bot, message) -> bool: # message
    if message.command == "echo":
        message.reply_message(message.to_send_message())
        return True
    return False