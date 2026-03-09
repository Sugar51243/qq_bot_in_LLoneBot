
# == 茨菇互动插件文件 ==

#此文件为OneBot11-小生物的茨菇互动插件涵数文件
#应用环境为LL-Bot v2.4.4

#如果不清楚具体作用，除配置外，请不要修改任何参数代码


#引用库
#  ==> pip自动下载缺失的库
# type: ignore
import os, asyncio, json, traceback
from src.importer import import_package
from src.plugin.tsugu.config import load_config
exec(import_package("requests"))
exec(import_package("log" , package_from= "src.loger"))
exec(import_package(
    "MessageChain, ImageMessage", 
    package_from= "OneBotConnecter.MessageType", package_pip_Name = "OneBotConnecter"))

#查询茨菇
async def call_tsugu(mode, data_pack, uri = None):
    if uri == None:
        bangdream_config = load_config("data/plugin/bangdream/config.yaml")
        tsugu_uri = bangdream_config[bangdream_config["use_uri"]]
    else: tsugu_uri = uri
    try:
        result = requests.post(f"{tsugu_uri}/{mode}", json=data_pack, timeout=bangdream_config["time_out"])
        if result.status_code != 200: raise ConnectionError()
        result = json.loads(result.text)
        message = MessageChain(["\n"])
        for i in result:
            if i["type"] == "base64":
                message.add(ImageMessage(f"base64://{i["string"]}"))
            else: message.add(MessageChain(i["string"]))
        return message
    except Exception as e:
        bangdream_config = load_config("data/plugin/bangdream/config.yaml")
        if tsugu_uri == bangdream_config["tsugu_uri"]:
            tsugu_uri = bangdream_config["backup_tsugu_uri"]
            message = MessageChain(["\n本地服务器连接失败，以下结果为转接公共服务器结果。"])
            message.add(await call_tsugu(mode, data_pack, uri = tsugu_uri))
            return message
        message = MessageChain(["\n无法连接茨菇后端"])
        tb = e.__traceback__
        formatted_tb = ''.join(traceback.format_tb(tb))
        log(formatted_tb)
        return message

#查询网络
async def call_net(uri, mode="get", data_pack=None):
    bangdream_config = load_config("data/plugin/bangdream/config.yaml")
    try:
        if mode == "get":
            result = requests.get(uri, timeout=10)
        else:
            result = requests.post(uri, json=data_pack, timeout=bangdream_config["time_out"])
        if result.status_code != 200: raise ConnectionError()
        result = json.loads(result.text)
        return result
    except Exception as e:
        bangdream_config = load_config("data/plugin/bangdream/config.yaml")
        if uri[:len(bangdream_config["tsugu_uri"])] == bangdream_config["tsugu_uri"]:
            uri = f"{bangdream_config["backup_tsugu_uri"]}{uri[len(bangdream_config["tsugu_uri"]):]}"
            return await call_net(uri, mode, data_pack)
        tb = e.__traceback__
        formatted_tb = ''.join(traceback.format_tb(tb))
        log(formatted_tb)
        return {}
