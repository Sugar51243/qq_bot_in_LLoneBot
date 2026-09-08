
# == Tsugu快捷词模块 ==

from src.plugins.tsugu_plugin.db import db

#新增快捷词 => 返回是否绑定成功(False为禁止套娃)
def add_order(user_id, order, target) -> bool:
    saved = [row[0] for row in db.query("SELECT target FROM short_order WHERE user_id = ?;", (str(user_id),))]
    if order in saved:
        return False
    db.execute("INSERT OR IGNORE INTO short_order (user_id, order_key, target) VALUES (?, ?, ?);", (str(user_id), str(order), str(target)))
    return True
#触发快捷词
def read_order(user_id, raw_message):
    row = db.query_one("SELECT target FROM short_order WHERE user_id = ? AND order_key = ?;", (str(user_id), raw_message))
    if row:
        return row[0]
    return None
