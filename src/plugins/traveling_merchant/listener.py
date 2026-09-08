
# == TravelingMerchant后台推送模块 ==

# 订阅推送线程: 每轮更新后自动推送远行商人在售内容
# 由main.py在bot初始化时通过plugin_listener入口启动

import time, datetime, traceback
from OneBotConnecter.types import MessageChain
from OneBotConnecter.loger.log_info import log
from src.core.register import sreach_enabled_scene
from src.plugins.traveling_merchant.db import db
from src.plugins.traveling_merchant.merchant import get_data, get_data_from_api, hour_to_round, only_weekend_items, shop_data

#远行商人订阅推送入口(bot初始化时由main.py调用)
def plugin_listener(bot):
    #等待bot初始化完成
    while not getattr(bot.bot, "user_id", None):
        time.sleep(1)
    _listener_loop(bot)

def _listener_loop(bot):
    log("[TravelingMerchant] 远行商人订阅推送已启动")
    times = 0
    await_success = False #已推送含错误提示的信息，等待查询成功后补推
    while True:
        try:
            #时间外
            now = datetime.datetime.now()
            current_hour = now.hour
            if 0 <= current_hour < 8:
                log("[TravelingMerchant] 非活动时间，已跳过处理")
                time.sleep(1800)
                continue
            #获取信息 => 缓存轮次信息
            cached = shop_data().get("shop_data", {})
            if cached.get("round", "-1") != hour_to_round(current_hour) or await_success:
                log("[TravelingMerchant] 信息未缓存，正在查询")
                data = get_data_from_api()
                #检查状态
                if not data:
                    time.sleep(60 if await_success else 30)
                    continue
                if only_weekend_items(data):
                    log("[TravelingMerchant] 空包体")
                    times += 1
                    if times < 10:
                        time.sleep(60 if await_success else 30)
                        continue
                    #10次重试后仍未通过判定 => 推送当前数据并注明可能存在错误
                    if not await_success:
                        push_shop_data(bot, data, note="\n(注意: 以上信息可能存在错误)", record=False)
                        await_success = True
                        log("[TravelingMerchant] 已推送含错误提示的数据，等待查询成功")
                    #延长至1分钟查询一次，直到查询成功后补推
                    time.sleep(60)
                    continue
                shop_data()["shop_data"] = data
                times = 0
                await_success = False
                log("[TravelingMerchant] 缓存已更新")
            cached = shop_data().get("shop_data", {})
            #处理信息
            push_shop_data(bot, cached)
        except Exception as e:
            tb = e.__traceback__
            formatted_tb = ''.join(traceback.format_tb(tb))
            log(f"[TravelingMerchant] [{type(e)}] {e}\n{formatted_tb}")
        time.sleep(60)

def push_shop_data(bot, cached, note=None, record=True):
    #处理信息
    shop_data_msg = get_data(cached)
    shop_data_msg += "\n\n此信息由远行商人插件自动推送"
    if note: shop_data_msg += note
    shop_data_msg = shop_data_msg[1:]
    #取得目标场景
    scenes = sreach_enabled_scene("远行商人")
    for scene in scenes:
        #排除已发送或未注册的场景
        row = db.query_one("SELECT round FROM notify_record WHERE scene_id = ?;", (scene,))
        sent_round = row[0] if row else None
        if sent_round == cached.get("round", "-1"): continue
        #取得用户/群ID
        try:
            id = int(scene.split("_")[1])
        except: continue
        #发送
        try:
            if "private" in scene: bot.send_private_msg(user_id=id, message=MessageChain([shop_data_msg]))
            elif "group" in scene: bot.send_group_msg(group_id=id, message=MessageChain([shop_data_msg]))
            else: log(f"[TravelingMerchant] 无法识别的场景类型: {scene}")
        except Exception as e:
            tb = e.__traceback__
            formatted_tb = ''.join(traceback.format_tb(tb))
            log(f"[TravelingMerchant] [{type(e)}] {e}\n{formatted_tb}")
        #更新状态(含错误提示的推送不记录，等待查询成功后正常推送)
        if record:
            db.execute("INSERT OR REPLACE INTO notify_record (scene_id, round) VALUES (?, ?);", (scene, cached.get("round", "-1")))
