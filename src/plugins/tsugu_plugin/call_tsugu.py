
import json, traceback, requests, os
from OneBotConnecter.types import MessageChain, ImageMessage
from src.project_locator.project_locator import get_project_location
from src.config_reader.config_reader import read_config
from OneBotConnecter.loger.log_info import log

_backup_uri = {"tsugu_uri": "backup_tsugu_uri", "backup_tsugu_uri": "tsugu_uri"}
path = os.path.dirname(os.path.abspath(__file__))
tsugu_config = os.path.join(path, "tsugu_config.yaml")

#查询茨菇
async def call_tsugu(mode, data_pack, uri = None):
    global _backup_uri
    waiting_try = []
    if uri == None:
        bangdream_config = read_config(tsugu_config)
        waiting_try.append(bangdream_config[bangdream_config["use_uri"]])
        waiting_try.append(bangdream_config[_backup_uri[bangdream_config["use_uri"]]])
        if bangdream_config["use_uri"] == "tsugu_uri": uri_type = ["Tsugu公共服务器", "本地茨菇服务器"]
        else: uri_type = ["小生物茨菇服务器", "Tsugu公共服务器"]
    else: 
        waiting_try.append(uri)
        uri_type = ["自定义服务器"]
    for idx in range(len(waiting_try)):
        tsugu_uri = waiting_try[idx]
        try:
            result = requests.post(f"{tsugu_uri}/{mode}", json=data_pack, timeout=bangdream_config["time_out"])
            if result.status_code != 200: raise ConnectionError()
            result = json.loads(result.text)
            message = MessageChain([f"\n正在使用[{uri_type[idx]}]:"])
            for i in result:
                if i["type"] == "base64":
                    message.add(ImageMessage(f"base64://{i["string"]}"))
                else: message.add(MessageChain(i["string"]))
            return message
        except Exception as e:
            tb = e.__traceback__
            formatted_tb = ''.join(traceback.format_tb(tb))
            log(f"正在使用{uri_type[idx]}:\n[{type(e)}] {e}\n{formatted_tb}")
    message = MessageChain(["\n无法连接茨菇后端"])
    return message

#查询网络
async def call_net(uri, mode="get", data_pack=None):
    global _backup_uri
    bangdream_config = read_config(tsugu_config)
    try:
        if mode == "get":
            result = requests.get(uri, timeout=10)
        else:
            result = requests.post(uri, json=data_pack, timeout=bangdream_config["time_out"])
        if result.status_code != 200: raise ConnectionError()
        result = json.loads(result.text)
        return result
    except Exception as e:
        tb = e.__traceback__
        formatted_tb = ''.join(traceback.format_tb(tb))
        log(f"正在使用{uri}:\n[{type(e)}] {e}\n{formatted_tb}")
        bangdream_config = read_config(tsugu_config)
        inuesd_tsugu_uri = bangdream_config[bangdream_config["use_uri"]]
        backup_tsugu_uri = bangdream_config[_backup_uri[bangdream_config["use_uri"]]]
        if uri[:len(inuesd_tsugu_uri)] == inuesd_tsugu_uri:
            uri = f"{backup_tsugu_uri}{uri[len(inuesd_tsugu_uri):]}"
            return await call_net(uri, mode, data_pack)
        return {}
