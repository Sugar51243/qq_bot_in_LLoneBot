
# == GifCreator插件数据库模块 ==

# 数据储存于sqlite(data/db/GifCreator.db)，分表储存:
#   nick_names(昵称绑定QQ)

from src.db_handler.plugin_db import PluginDB

db = PluginDB("表情包合成", {
    "nick_names": "CREATE TABLE IF NOT EXISTS nick_names (nick TEXT PRIMARY KEY, user_id TEXT NOT NULL);"
}, db_name="GifCreator")

def read_nick_names() -> dict:
    result = {}
    for nick, user_id in db.query("SELECT nick, user_id FROM nick_names;"):
        result[nick] = user_id
    return result
