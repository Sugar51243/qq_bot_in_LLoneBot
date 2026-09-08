
# == 茨菇后端连接工具 ==

import json, traceback, requests
from OneBotConnecter.types import MessageChain, ImageMessage
from OneBotConnecter.loger.log_info import log
from src.plugins.tsugu_plugin.config import load_config

_backup_uri = {"tsugu_uri": "backup_tsugu_uri", "backup_tsugu_uri": "tsugu_uri"}

#查询茨菇
def call_tsugu(mode, data_pack, uri = None):
    if uri == None:
        bangdream_config = load_config()
        if bangdream_config["use_uri"] == "tsugu_uri":
            waiting_try = [
                (bangdream_config["tsugu_uri"], "Tsugu公共服务器"),
                (bangdream_config["backup_tsugu_uri"], "本地茨菇服务器"),
            ]
        else:
            waiting_try = [
                (bangdream_config["backup_tsugu_uri"], "小生物茨菇服务器"),
                (bangdream_config["tsugu_uri"], "Tsugu公共服务器"),
            ]
    else:
        waiting_try = [(uri, "自定义服务器")]
    for tsugu_uri, uri_type in waiting_try:
        if not tsugu_uri: continue #样本配置中备份服务器可能为空
        try:
            result = requests.post(f"{tsugu_uri}/{mode}", json=data_pack, timeout=bangdream_config["time_out"])
            if result.status_code != 200: raise ConnectionError()
            result = json.loads(result.text)
            message = MessageChain([f"\n正在使用[{uri_type}]:"])
            for i in result:
                if i["type"] == "base64":
                    message.add(ImageMessage(f"base64://{i['string']}"))
                else: message.add(MessageChain(i["string"]))
            return message
        except Exception as e:
            tb = e.__traceback__
            formatted_tb = ''.join(traceback.format_tb(tb))
            log(f"正在使用{uri_type}:\n[{type(e)}] {e}\n{formatted_tb}")
    message = MessageChain(["\n无法连接茨菇后端"])
    return message

#查询网络
def call_net(uri, mode="get", data_pack=None):
    bangdream_config = load_config()
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
        inuesd_tsugu_uri = bangdream_config[bangdream_config["use_uri"]]
        backup_tsugu_uri = bangdream_config[_backup_uri[bangdream_config["use_uri"]]]
        if not inuesd_tsugu_uri or not backup_tsugu_uri:
            return {}
        if uri[:len(inuesd_tsugu_uri)] == inuesd_tsugu_uri:
            uri = f"{backup_tsugu_uri}{uri[len(inuesd_tsugu_uri):]}"
            return call_net(uri, mode, data_pack)
        return {}
