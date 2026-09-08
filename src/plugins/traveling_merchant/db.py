
# == TravelingMerchant插件数据库模块 ==

# 数据储存于sqlite(data/db/TravelingMerchant.db)，分表储存:
#   notify_record(场景推送轮次记录)

from src.db_handler.plugin_db import PluginDB

db = PluginDB("远行商人", {
    "notify_record": "CREATE TABLE IF NOT EXISTS notify_record (scene_id TEXT PRIMARY KEY, round INTEGER NOT NULL);"
}, db_name="TravelingMerchant")
