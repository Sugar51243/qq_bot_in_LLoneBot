
# == Tsugu插件数据库模块 ==

# 数据储存于sqlite(data/db/Tsugu.db)，分表储存:
#   user_binding(玩家绑定) / key_set(搜索关键词) / short_order(快捷词) / card_cache(卡面缓存)

from src.db_handler.plugin_db import PluginDB

db = PluginDB("tsugu", {
    "user_binding": "CREATE TABLE IF NOT EXISTS user_binding (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, acc TEXT NOT NULL, server TEXT NOT NULL, UNIQUE(user_id, acc, server));",
    "key_set": "CREATE TABLE IF NOT EXISTS key_set (keyword TEXT PRIMARY KEY, song_ids TEXT NOT NULL);",
    "short_order": "CREATE TABLE IF NOT EXISTS short_order (user_id TEXT NOT NULL, order_key TEXT NOT NULL, target TEXT NOT NULL, PRIMARY KEY(user_id, order_key));",
    "card_cache": "CREATE TABLE IF NOT EXISTS card_cache (card_id TEXT PRIMARY KEY, data TEXT NOT NULL);"
}, db_name="Tsugu")
