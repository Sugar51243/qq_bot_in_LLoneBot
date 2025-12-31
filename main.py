import src.messageHandler
import asyncio, os, traceback
try:
    from OneBotConnecter import OneBot
except:
    os.system("pip install OneBotConnecter")
    exec(f"from OneBotConnecter import OneBot")
try:
    from config_io import Config
except:
    os.system("pip install config-io")
    exec(f"from config_io import Config")
os.system("cls")

async def main():

    localtion = os.path.dirname(__file__)
    config = Config.load_from_file("data/config.yaml")
    uri = config["uri"]
    owner = config["owner"]
    botName = config["botName"]
    #botFunction = config["botFunction"]
    bot = OneBot(uri=uri, owner=owner, botName=botName, localtion=localtion)
    await bot.run(on_message=src.messageHandler.onMessage)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except:
        traceback.print_exc()
        os.system("pause")
