
# == Tomori OurNotes插件数据库模块 ==

# 数据储存于sqlite(data/db/tomori_ournotes.db)，分表储存:
#   announcement_subscription(公告推流订阅: 场景→服务器, 一场景可订阅多服)

from src.db_handler.plugin_db import PluginDB

db = PluginDB("tomori_ournotes", {
    "announcement_subscription": "CREATE TABLE IF NOT EXISTS announcement_subscription (scene_id TEXT NOT NULL, server TEXT NOT NULL, created_at INTEGER NOT NULL, PRIMARY KEY (scene_id, server));"
})
