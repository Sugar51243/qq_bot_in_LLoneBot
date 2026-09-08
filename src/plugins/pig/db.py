
# == Pig插件数据库模块 ==

# 数据储存于sqlite(data/db/Pig.db)，分表储存:
#   record(表情记录) / permissions(用户防御设置) / config(表情功能开关) / emoji_ids(表情ID映射)

from src.db_handler.plugin_db import PluginDB

db = PluginDB("猪人", {
    "record": "CREATE TABLE IF NOT EXISTS record (user_id TEXT NOT NULL, emoji TEXT NOT NULL, times INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(user_id, emoji));",
    "permissions": "CREATE TABLE IF NOT EXISTS permissions (user_id TEXT NOT NULL, emoji TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1, PRIMARY KEY(user_id, emoji));",
    "config": "CREATE TABLE IF NOT EXISTS config (emoji TEXT PRIMARY KEY, enabled INTEGER NOT NULL DEFAULT 1);",
    "emoji_ids": "CREATE TABLE IF NOT EXISTS emoji_ids (emoji TEXT PRIMARY KEY, emoji_id INTEGER NOT NULL);"
}, db_name="Pig")

#默认表情ID映射(与v1的emoji_to_id.json一致)
_default_emoji_ids = {"❤":66, "☀":9728, "❔":10068, "㊗":12951, "🐉":128009, "🐷":128055, "🐖":128022}

for _emoji, _emoji_id in _default_emoji_ids.items():
    db.execute("INSERT OR IGNORE INTO emoji_ids (emoji, emoji_id) VALUES (?, ?);", (_emoji, _emoji_id))

def read_id(emoji):
    row = db.query_one("SELECT emoji_id FROM emoji_ids WHERE emoji = ?;", (emoji,))
    if row: return row[0]
    return None
