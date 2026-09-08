
# == TravelingMerchant远行商人数据模块 ==

# API请求与数据格式化

import json, requests, datetime, traceback
from OneBotConnecter.loger.log_info import log
from src.db_handler.plugin_db import get_plugin_state

weekend_items_keys = ["球", "残缺魔镜", "适格钥匙", "能力钥匙"]
except_all_day_items = ["棱镜球"]

def shop_data() -> dict:
    state = get_plugin_state("远行商人")
    if "shop_data" not in state: state["shop_data"] = {}
    return state

def get_data(data=None):
    result = "获取远行商人数据失败，请稍后再试！"
    try:
        if not data:
            data = get_data_from_api()
            if data and not only_weekend_items(data):
                shop_data()["shop_data"] = data
        if not data: return result
        result = "\n"
        fetchedAt = data.get("fetchedAt", None)
        if fetchedAt:
            time = fetchedAt.split("T")
            time = time[1][:8].split(":")
            result += f"数据更新时间: {int(time[0])+8}:{time[1]}:{time[2]}"
        next_update = data.get("nextRefreshBeijing", None)
        if next_update:
            next_update = datetime.datetime.strptime(next_update, "%Y-%m-%d %H:%M:%S")
            now = datetime.datetime.now()
            dif = next_update - now
            result += f"\n距离下次更新: {str(dif)[:7]}"
        result += f"\n\n远行商人({data.get('round', '未知')}轮)正在出售以下物品:"
        items = data.get("items", [])
        if not items: return result + "\n无数据"
        all_day = []
        week_end = []
        this_round = []
        for item in items:
            if item.get('rounds', []) != [1, 2, 3, 4]:
                this_round.append(item)
                continue
            inKey = False
            for key in weekend_items_keys:
                if (key in item.get('name', None) or item.get('name', None) == key) and not item.get('name', None) in except_all_day_items:
                    week_end.append(item)
                    inKey = True
                    break
            if not inKey: all_day.append(item)
        for i, item in enumerate(this_round, start=1):
            if i == 1: result += "\n-----------本轮物品-----------"
            result += f"\n{i}. {item.get('name', '未知')} - 价格: {item.get('priceRaw', '未知')} (x{item.get('limit', '未知')})"
        for i, item in enumerate(all_day, start=1):
            if i == 1: result += "\n-----------本日物品-----------"
            result += f"\n{i}. {item.get('name', '未知')} - 价格: {item.get('priceRaw', '未知')} (x{item.get('limit', '未知')})"
        for i, item in enumerate(week_end, start=1):
            if i == 1: result += "\n-----------周末限定-----------"
            result += f"\n{i}. {item.get('name', '未知')} - 价格: {item.get('priceRaw', '未知')} (x{item.get('limit', '未知')})"
        result += "\n-------------------------------"
    except Exception as e:
        tb = e.__traceback__
        formatted_tb = ''.join(traceback.format_tb(tb))
        log(f"[TravelingMerchant] [{type(e)}] {e}\n{formatted_tb}")
    return result

def get_data_from_api():
    try:
        result = requests.get(f"https://rocokingdomworld.org/api/merchant/live")
        if result.status_code == 200:
            json_data = json.loads(result.text)
            log(f"[TravelingMerchant] API返回: {json_data}")
            return json_data
    except Exception as e: pass
    return None

def hour_to_round(hour):
    if 8 <= hour < 12:
        return 1
    elif hour < 16:
        return 2
    elif hour < 20:
        return 3
    elif hour < 24:
        return 4
    else: return -1

def only_weekend_items(data):
    if not data: return True
    items = data.get("items", [])
    for item in items:
        if item.get("rounds", None) != [1, 2, 3, 4]:
            return False
    return True
