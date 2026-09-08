
# == Jrlp插件数据库模块 ==

# 数据储存于sqlite(data/db/Jrlp.db)，分表储存:
#   pairing(每日配对记录: 日期/群号/用户/对象)

from src.db_handler.plugin_db import PluginDB

db = PluginDB("每日老婆", {
    "pairing": "CREATE TABLE IF NOT EXISTS pairing (date TEXT NOT NULL, group_id TEXT NOT NULL, user_id TEXT NOT NULL, partner_id TEXT NOT NULL, PRIMARY KEY(date, group_id, user_id));"
}, db_name="Jrlp")
