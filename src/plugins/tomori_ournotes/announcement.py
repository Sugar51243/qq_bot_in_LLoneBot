
# == Tomori OurNotes公告模块 ==

# 一次性查询: 公告列表(/announcements) / 公告详情(/announcements + id)
# 推流: /announcementStream/{tw|jp|kr|en} 四条SSE长连接
#   (后端只在公告新增/修改时推送该条内容图; 连接时不发快照, 下架不推)
#
# 注册制:
#   机器人侧总开关config["announcement_stream"](默认开启) —— 开启时bot启动自动建立四条长连接,
#   获取公告但不主动发送至任何场景;
#   场景侧开关存于数据库(默认关闭) —— 用"公告 <服务器>"注册后, 该场景才会收到对应服的推流结果

import json, time, traceback, requests
from OneBotConnecter.types import MessageChain, ImageMessage
from OneBotConnecter.loger.log_info import log
from src.db_handler.plugin_db import start_background_once
from src.plugins.tomori_ournotes.config import load_config
from src.plugins.tomori_ournotes.call_ournotes import call_ournotes, SERVER_LIST, DEFAULT_SERVER, parse_server_loose, server_display, server_hint
from src.plugins.tomori_ournotes.db import db
from src.plugins.tomori_ournotes.reply import feedback

#关闭场景推流的关键字
CLOSE_KEYWORDS = ["关闭", "取消", "停用", "off"]

#SSE断线重连间隔(秒)
RECONNECT_DELAY = 15

#流读取超时(秒): 服务端心跳25s一次, 取其数倍, 超时视为断线重连
STREAM_READ_TIMEOUT = 90

def _display(server: str) -> str:
    return server_display(server)

# == 一次性查询 ==

#公告列表 - on公告列表 (<服务器>)
def announcement_list(bot, message, parameter):
    server = DEFAULT_SERVER
    tokens = parameter.split()
    if tokens:
        server = parse_server_loose(tokens[0])
        if server is None:
            feedback(message, MessageChain([f"\n[TOMORI]服务器只支持 {server_hint()}, 例: on公告列表 tw"]))
            return
    config = load_config()
    message_chain = call_ournotes("announcements", {
        "server": server,
        "compress": config["compress"]
    })
    feedback(message, message_chain)

#公告 - on公告 (<公告ID>) (<服务器>)
#  id填入 → 一次性查询该公告详情(默认港澳台服)
#  id未填 → 按服务器注册本场景公告推流(此情况无默认值, 服务器必填)
def handle_announcement(bot, message, parameter):
    tokens = parameter.split()
    if not tokens:
        send_message = MessageChain(["\n[TOMORI]查询Our Notes游戏公告(四服务器独立)"])
        send_message.add("\n[公告ID] (<服务器>) → 查该公告详情(默认港澳台服)")
        send_message.add("\n例: on公告 23 jp")
        send_message.add("\n<服务器> → 注册本场景公告推流(新增/修改时推送)")
        send_message.add("\n例: on公告 tw")
        send_message.add("\n关闭 (<服务器>) → 关闭本场景推流(不带则关全部)")
        send_message.add("\n例: on公告 关闭")
        send_message.add("\n全量列表: on公告列表 (tw/jp/kr/en)\n")
        feedback(message, send_message)
        return
    first = tokens[0]
    #关闭本场景推流
    if first.lower() in CLOSE_KEYWORDS:
        server = None
        if len(tokens) > 1:
            server = parse_server_loose(tokens[1])
            if server is None:
                feedback(message, MessageChain([f"\n[TOMORI]服务器只支持 {server_hint()}, 例: on公告 关闭 tw"]))
                return
        close_subscription(bot, message, server)
        return
    #公告ID → 一次性查详情
    if first.isdigit():
        server = DEFAULT_SERVER
        if len(tokens) > 1:
            server = parse_server_loose(tokens[1])
            if server is None:
                feedback(message, MessageChain([f"\n[TOMORI]服务器只支持 {server_hint()}, 例: on公告 23 jp"]))
                return
        config = load_config()
        message_chain = call_ournotes("announcements", {
            "server": server,
            "id": first,
            "compress": config["compress"]
        })
        feedback(message, message_chain)
        return
    #无ID → 注册本场景推流, 服务器必填
    server = parse_server_loose(first)
    if server is None:
        feedback(message, MessageChain([f"\n[TOMORI]未指定公告ID时须填服务器({server_hint()}), 例: on公告 tw"]))
        return
    register_subscription(bot, message, server)

# == 场景订阅(注册制) ==

#本场景当前订阅的服务器列表(按四服固定顺序)
def scene_servers(scene_id: str) -> list:
    rows = [r[0] for r in db.query("SELECT server FROM announcement_subscription WHERE scene_id = ?;", (scene_id,))]
    return [s for s in SERVER_LIST if s in rows]

#某服的全部订阅场景
def subscribed_scenes(server: str) -> list:
    return [r[0] for r in db.query("SELECT scene_id FROM announcement_subscription WHERE server = ?;", (server,))]

#注册(幂等)本场景对某服的公告推流
def register_subscription(bot, message, server):
    db.execute("INSERT OR REPLACE INTO announcement_subscription (scene_id, server, created_at) VALUES (?, ?, ?);",
               (message.scene_id, server, int(time.time())))
    servers = "、".join(_display(s) for s in scene_servers(message.scene_id))
    text = f"\n[TOMORI]已在本场景注册公告推流: {_display(server)}\n当前订阅: {servers}"
    if not load_config().get("announcement_stream", True):
        text += "\n(注意: 机器人侧公告推流功能未启用, 暂时收不到推送)"
    feedback(message, MessageChain([text]))

#关闭本场景推流: 指定服务器则只关该服, 否则关闭全部
def close_subscription(bot, message, server):
    if server:
        row = db.query_one("SELECT scene_id FROM announcement_subscription WHERE scene_id = ? AND server = ?;", (message.scene_id, server))
        if not row:
            feedback(message, MessageChain([f"\n[TOMORI]本场景未注册{_display(server)}的公告推流"]))
            return
        db.execute("DELETE FROM announcement_subscription WHERE scene_id = ? AND server = ?;", (message.scene_id, server))
        servers = "、".join(_display(s) for s in scene_servers(message.scene_id))
        text = f"\n[TOMORI]已关闭本场景[{_display(server)}]的公告推流"
        text += f"\n当前订阅: {servers}" if servers else "\n当前订阅: 无"
        feedback(message, MessageChain([text]))
        return
    db.execute("DELETE FROM announcement_subscription WHERE scene_id = ?;", (message.scene_id,))
    feedback(message, MessageChain(["\n[TOMORI]已关闭本场景全部公告推流"]))

# == 公告推流(SSE长连接) ==

#启动四服务器公告推流(bot初始化时由plugin.py的plugin_listener调用)
def start_announcement_stream(bot):
    #等待bot初始化完成
    while not getattr(bot.bot, "user_id", None):
        time.sleep(1)
    if not load_config().get("announcement_stream", True):
        log("[TOMORI] 机器人侧公告推流已关闭(announcement_stream=false), 跳过连接")
        return
    for server in SERVER_LIST:
        start_background_once(f"tomori_announcement_{server}", _make_stream_target(bot, server))
    log("[TOMORI] 公告推流已启动: " + "、".join(_display(s) for s in SERVER_LIST))

def _make_stream_target(bot, server):
    def target():
        stream_server(bot, server)
    return target

#单服长连接: 断线自动重连
def stream_server(bot, server):
    config = load_config()
    url = f"{config['ournotes_uri']}/announcementStream/{server}"
    while True:
        try:
            _consume_stream(bot, server, url)
        except Exception as e:
            tb = e.__traceback__
            formatted_tb = ''.join(traceback.format_tb(tb))
            log(f"[TOMORI][{server}]公告推流连接异常: [{type(e)}] {e}\n{formatted_tb}")
        time.sleep(RECONNECT_DELAY)

#消费一条SSE流(阻塞直到断开)
def _consume_stream(bot, server, url):
    log(f"[TOMORI][{server}]正在连接公告推流: {url}")
    response = requests.get(url, stream=True, timeout=(10, STREAM_READ_TIMEOUT))
    if response.status_code != 200:
        response.close()
        raise ConnectionError(f"HTTP {response.status_code}")
    event_name = None
    data_lines = []
    try:
        for raw_line in response.iter_lines(decode_unicode=True):
            line = raw_line or ""
            #注释行(如心跳": ping")
            if line.startswith(":"):
                continue
            #空行 = 事件结束
            if line == "":
                if event_name:
                    handle_stream_event(bot, server, event_name, "\n".join(data_lines))
                event_name = None
                data_lines = []
                continue
            if line.startswith("event:"):
                event_name = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data_lines.append(line[len("data:"):].strip())
    finally:
        response.close()

#处理一条SSE事件
def handle_stream_event(bot, server, event_name, data_text):
    if event_name == "ready":
        log(f"[TOMORI][{server}]公告推流已就绪: {data_text}")
        return
    if event_name != "announcement":
        return
    try:
        payload = json.loads(data_text) if data_text else {}
    except Exception:
        log(f"[TOMORI][{server}]公告推流数据解析失败: {data_text[:120]}")
        return
    if not isinstance(payload, dict) or not payload:
        log(f"[TOMORI][{server}]公告推流数据为空, 已忽略")
        return
    kind = "新增" if payload.get("kind") == "added" else "更新"
    title = payload.get("title", "")
    images = payload.get("images", []) or []
    #无标题且无图时无内容可推, 跳过(防上游异常载荷)
    if not images and not title:
        log(f"[TOMORI][{server}]公告推流数据无标题与图片, 已忽略")
        return
    scenes = subscribed_scenes(server)
    log(f"[TOMORI][{server}]公告{kind}: {title} (本服订阅场景数: {len(scenes)})")
    #本服无场景订阅: 不主动发送
    if not scenes:
        return
    for scene_id in scenes:
        send_to_scene(bot, scene_id, server, kind, title, images)

#构造推送消息: 抬头文本 + 公告内容图
def build_announcement_message(server, kind, title, images):
    message_chain = MessageChain([f"\n[TOMORI][{_display(server)}]公告{kind}: {title}"])
    for item in images:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "base64":
            message_chain.add(ImageMessage(f"base64://{item.get('string', '')}"))
        else:
            message_chain.add(MessageChain(str(item.get("string", ""))))
    return message_chain

#向场景发送(scene_id形如 group_123 / private_456)
def send_to_scene(bot, scene_id, server, kind, title, images):
    try:
        message_chain = build_announcement_message(server, kind, title, images)
        if scene_id.startswith("group_"):
            bot.send_group_msg(int(scene_id[len("group_"):]), message_chain)
        elif scene_id.startswith("private_"):
            bot.send_private_msg(int(scene_id[len("private_"):]), message_chain)
    except Exception as e:
        tb = e.__traceback__
        formatted_tb = ''.join(traceback.format_tb(tb))
        log(f"[TOMORI]公告推流发送至[{scene_id}]失败: [{type(e)}] {e}\n{formatted_tb}")
