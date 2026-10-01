
# == OurNotes后端连接工具 ==

# OurNotes后端(项目代号Tomori)响应协议与茨菇tsugu兼容:
# 图片类端点返回[{type:'string'|'base64', string}](listToBase64)
# 领域错误以HTTP 200返回['错误: ...']字符串数组
# JSON类端点(fuzzySearch/songChartData)返回{status, data}

import json, traceback, requests
from OneBotConnecter.types import MessageChain, ImageMessage
from OneBotConnecter.loger.log_info import log
from src.plugins.tomori_ournotes.config import load_config

# == 服务器(游戏区域) ==

#四个游戏区域短码(与后端Server.ts一致); 港澳台服的历史别名hk-tw-mo后端仍接受
SERVER_LIST = ["tw", "jp", "kr", "en"]

#区域展示名
SERVER_DISPLAY = {"tw": "港澳台服", "jp": "日服", "kr": "韩服", "en": "国际服"}

#默认服务器(指令未指定时)
DEFAULT_SERVER = "tw"
DEFAULT_SERVERS = [DEFAULT_SERVER]

#服务器别名(小写比较) → 短码; 单字"日/韩"歧义大, 不参与通用抽取(仅公告等服务器专用参数可用)
SERVER_ALIAS = {
    "tw": "tw", "hk-tw-mo": "tw", "hk": "tw", "hktwmo": "tw",
    "港澳台服": "tw", "港台服": "tw", "台服": "tw",
    "jp": "jp", "日服": "jp",
    "kr": "kr", "韩服": "kr",
    "en": "en", "国际服": "en", "全球服": "en",
}
SERVER_ALIAS_LOOSE = {"日": "jp", "韩": "kr"}

#解析服务器参数(短码或别名), 无法识别返回None
def parse_server(token: str):
    return SERVER_ALIAS.get(f"{token}".strip().lower())

#宽松解析(额外接受单字"日/韩"), 供服务器专用参数(公告等)使用
def parse_server_loose(token: str):
    key = f"{token}".strip().lower()
    return SERVER_ALIAS.get(key) or SERVER_ALIAS_LOOSE.get(key)

#从tokens中抽取服务器token(不区分位置, 按出现顺序去重), 返回(其余tokens, 服务器短码列表)
#  未指定时用default_servers; 默认[DEFAULT_SERVER]
def split_servers(tokens: list, default_servers: list = None):
    rest = []
    servers = []
    for token in tokens:
        server = parse_server(token)
        if server:
            if server not in servers:
                servers.append(server)
        else:
            rest.append(token)
    if not servers:
        servers = list(DEFAULT_SERVERS if default_servers is None else default_servers)
    return rest, servers

#区域展示名
def server_display(server: str) -> str:
    return SERVER_DISPLAY.get(server, server)

#服务器参数提示文案
def server_hint() -> str:
    return "tw(港澳台服) / jp(日服) / kr(韩服) / en(国际服)"

#服务器列表提示文案(如 港澳台服、日服)
def servers_display(servers: list) -> str:
    return "、".join(server_display(s) for s in servers)

#解析后端错误响应体(如404占位的{status:'fail',...}/400参数校验的{status:'failed',...}), 解析失败返回None
def parse_error_body(result) -> str:
    try:
        data = json.loads(result.text)
        if isinstance(data, dict) and data.get("status") in ("fail", "failed") and "data" in data:
            return str(data.get("data", ""))
    except Exception:
        pass
    return None

#调用OurNotes后端 - 图片类端点(listToBase64协议)
def call_ournotes(mode, data_pack, uri = None):
    config = load_config()
    if uri == None:
        uri = config["ournotes_uri"]
    try:
        result = requests.post(f"{uri}/{mode}", json=data_pack, timeout=config["time_out"])
        if result.status_code != 200:
            #如404占位/500等带域内错误体, 转发其文案
            error_text = parse_error_body(result)
            if error_text:
                message = MessageChain([f"\n[TOMORI]{error_text}"])
            else:
                message = MessageChain([f"\n[TOMORI]后端响应异常(HTTP {result.status_code})"])
            return message
        result = json.loads(result.text)
        #参数校验错误返回{status:'failed', ...}
        if not isinstance(result, list):
            data = result.get("data", "请求失败") if isinstance(result, dict) else "请求失败"
            message = MessageChain([f"\n[TOMORI]{data}"])
            return message
        message = MessageChain(["\n"])
        for i in result:
            if i["type"] == "base64":
                message.add(ImageMessage(f"base64://{i['string']}"))
            else:
                message.add(MessageChain(i["string"]))
        return message
    except Exception as e:
        tb = e.__traceback__
        formatted_tb = ''.join(traceback.format_tb(tb))
        log(f"[TOMORI]连接{uri}/{mode}失败:\n[{type(e)}] {e}\n{formatted_tb}")
    message = MessageChain(["\n[TOMORI]无法连接OurNotes后端"])
    return message

#调用OurNotes后端 - JSON类端点
def call_net(uri, mode="get", data_pack=None):
    config = load_config()
    try:
        if mode == "get":
            result = requests.get(uri, timeout=10)
        else:
            result = requests.post(uri, json=data_pack, timeout=config["time_out"])
        if result.status_code != 200:
            #如404占位等带域内错误体, 转为fail结果交由调用方转发文案
            error_text = parse_error_body(result)
            if error_text:
                return {"status": "fail", "data": error_text}
            raise ConnectionError()
        result = json.loads(result.text)
        return result
    except Exception as e:
        tb = e.__traceback__
        formatted_tb = ''.join(traceback.format_tb(tb))
        log(f"[TOMORI]连接{uri}失败:\n[{type(e)}] {e}\n{formatted_tb}")
        return {}

#fuzzySearch分词(后端索引按区域分片, 传入servers保证与后续搜索区域一致)
def call_fuzzy_search(text: str, servers: list = None) -> dict:
    config = load_config()
    datapack = {"text": text}
    if servers:
        datapack["displayedServerList"] = servers
    return call_net(f"{config['ournotes_uri']}/fuzzySearch", mode="post", data_pack=datapack)
