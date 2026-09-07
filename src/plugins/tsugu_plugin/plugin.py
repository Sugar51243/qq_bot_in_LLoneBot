
import os

path = os.path.dirname(os.path.abspath(__file__))
tsugu_config = os.path.join(path, "tsugu_config.yaml")

def on_all_case(bot, message) -> bool: #call case including message, poke, request ...
    if "message" in message.event_type:
        return on_msg(bot, message=message)

def on_msg(bot, message) -> bool: # message
    return False