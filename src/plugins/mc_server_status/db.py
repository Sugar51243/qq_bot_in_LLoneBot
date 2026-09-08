
# == McServerStatus插件数据库模块 ==

# 数据储存于sqlite(data/db/McServerStatus.db)，分表储存:
#   bind_data(场景绑定服务器记录)

from src.db_handler.plugin_db import PluginDB

db = PluginDB("MC服务器状态查询", {
    "bind_data": "CREATE TABLE IF NOT EXISTS bind_data (bind_id INTEGER PRIMARY KEY AUTOINCREMENT, place_id TEXT NOT NULL, server_location TEXT NOT NULL, UNIQUE(place_id, server_location));"
}, db_name="McServerStatus")
