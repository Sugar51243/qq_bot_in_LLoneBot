
# == 主文件 ==

#此文件为OneBot11-小生物的主涵数文件
#应用环境为LL-Bot v2.4.4

#如果不清楚具体作用，除配置外，请不要修改任何参数代码
#需要更多信息调试 => 请调整testMode参数为True


#引用库
#  ==> pip自动下载缺失的库
# type: ignore
import asyncio, os, traceback
import src.messageHandler as messageHandler
import src.config as config
import src.loger as loger
from src.importer import import_package
exec(import_package("OneBot", package_from="OneBotConnecter"))


#清理屏幕信息
os.system("cls")

#主涵数
async def main():
    localtion = os.path.dirname(__file__) #获取文件位置
    #加载配置
    bot_config = config.load_config("data/config.yaml") #配置文件默认位于 data/config.yaml
    uri = bot_config["uri"]
    owner = bot_config["owner"]
    botName = bot_config["botName"]
    #创建连接
    bot = OneBot(uri=uri, owner=owner, botName=botName, localtion=localtion, testMode=False)
    await bot.non_async_run(on_message=messageHandler.onMessage) #处理信息 (相关涵数位于src/messageHandler.py)

#运行
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        tb = e.__traceback__
        formatted_tb = ''.join(traceback.format_tb(tb))
        loger.log(formatted_tb)