
# == GroupEvents插件数据库模块 ==

# 数据储存于sqlite(data/db/GroupEvents.db)，分表储存:
#   nickname_switch(昵称播报开关) / leave_switch(退群播报开关)

from src.db_handler.plugin_db import PluginDB

db = PluginDB("群事件播报", {
    "nickname_switch": "CREATE TABLE IF NOT EXISTS nickname_switch (group_id TEXT PRIMARY KEY, enabled INTEGER NOT NULL DEFAULT 1);",
    "leave_switch": "CREATE TABLE IF NOT EXISTS leave_switch (group_id TEXT PRIMARY KEY, enabled INTEGER NOT NULL DEFAULT 1);"
}, db_name="GroupEvents")

# == 开关操作(无记录时默认开启) ==

def nickname_enabled(group_id: str) -> bool:
    row = db.query_one("SELECT enabled FROM nickname_switch WHERE group_id = ?;", (str(group_id),))
    return True if row is None else bool(row[0])

def leave_enabled(group_id: str) -> bool:
    row = db.query_one("SELECT enabled FROM leave_switch WHERE group_id = ?;", (str(group_id),))
    return True if row is None else bool(row[0])

def set_nickname_enabled(group_id: str, enabled: bool):
    db.execute("INSERT OR REPLACE INTO nickname_switch (group_id, enabled) VALUES (?, ?);", (str(group_id), 1 if enabled else 0))

def set_leave_enabled(group_id: str, enabled: bool):
    db.execute("INSERT OR REPLACE INTO leave_switch (group_id, enabled) VALUES (?, ?);", (str(group_id), 1 if enabled else 0))
