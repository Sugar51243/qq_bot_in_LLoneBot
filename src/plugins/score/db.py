
# == Score插件数据库模块 ==

# 数据储存于sqlite(data/db/Score.db)，分表储存:
#   users(用户积分) / cards(加成卡) / daily_cards(每日加成记录) / daily_scores(每日积分记录)

from src.db_handler.plugin_db import PluginDB

db = PluginDB("小生物积分", {
    "users": "CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, scores REAL NOT NULL DEFAULT 0, chart REAL NOT NULL DEFAULT 0, card REAL NOT NULL DEFAULT 0, sp REAL NOT NULL DEFAULT 0, name TEXT NOT NULL DEFAULT '', use_card INTEGER NOT NULL DEFAULT 1, time REAL NOT NULL DEFAULT 0);",
    "cards": "CREATE TABLE IF NOT EXISTS cards (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, card_score REAL NOT NULL);",
    "daily_cards": "CREATE TABLE IF NOT EXISTS daily_cards (date TEXT NOT NULL, user_id TEXT NOT NULL, PRIMARY KEY(date, user_id));",
    "daily_scores": "CREATE TABLE IF NOT EXISTS daily_scores (date TEXT NOT NULL, user_id TEXT NOT NULL, PRIMARY KEY(date, user_id));"
}, db_name="Score")
