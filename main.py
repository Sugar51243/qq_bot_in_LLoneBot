from OneBotConnecter.OneBot import OneBot
from src.config_reader.config_reader import read_bot_config
from src.console.print_data import print_message
from src.handle_message import handle_message

def on_message(bot, message):
    print_message(message)
    global allowSlash
    handle_message(bot, message)

def main():
    config = read_bot_config()
    uri = config.get("uri", "ws://127.0.0.1:3001")
    owner = config.get("owner", [])
    bot = OneBot(url=uri, call_function=on_message, owner=owner)
    bot.run()

if __name__ == "__main__":
    main()