
# == SleepAssistant插件数据库模块 ==

# 数据储存于sqlite(data/db/SleepAssistant.db)，分表储存:
#   users(用户设置) / record(发言时间记录) / sleep_data(睡眠记录)

from src.db_handler.plugin_db import PluginDB

db = PluginDB("睡眠助手", {
    "users": "CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, time_zone INTEGER NOT NULL DEFAULT 8, plugin_on INTEGER NOT NULL DEFAULT 0, good_nighted INTEGER NOT NULL DEFAULT 0);",
    "record": "CREATE TABLE IF NOT EXISTS record (message_id INTEGER PRIMARY KEY AUTOINCREMENT, time REAL NOT NULL, user_id INTEGER NOT NULL);",
    "sleep_data": "CREATE TABLE IF NOT EXISTS sleep_data (sleep_data_id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, user_id INTEGER, sleep_time REAL, wake_up_time REAL, sleep_duration REAL);"
}, db_name="SleepAssistant")

# == 数据库操作 ==

def get_user_data(user_id):
    db.execute("INSERT OR IGNORE INTO users (user_id, time_zone, plugin_on, good_nighted) VALUES (?, 8, 0, 0);", (user_id,))
    row = db.query_one("SELECT * FROM users WHERE user_id = ?;", (user_id,))
    return row

def update_record(user_id, time):
    db.execute("INSERT INTO record (time, user_id) VALUES (?, ?);", (time, user_id))

def plugin_on(user_id):
    db.execute("UPDATE users SET plugin_on = 1 WHERE user_id = ?;", (user_id,))

def plugin_off(user_id):
    db.execute("UPDATE users SET plugin_on = 0 WHERE user_id = ?;", (user_id,))

def good_night(user_id):
    db.execute("UPDATE users SET good_nighted = 1 WHERE user_id = ?;", (user_id,))

def non_good_night(user_id):
    db.execute("UPDATE users SET good_nighted = 0 WHERE user_id = ?;", (user_id,))

def update_time_zone(user_id, time_zone):
    db.execute("UPDATE users SET time_zone = ? WHERE user_id = ?;", (time_zone, user_id))

def get_last_msg_time(user_id):
    rows = db.query("SELECT time FROM record WHERE user_id = ?;", (user_id,))
    if rows:
        row = rows[-2]
        return row[0]
    return 0

def return_sleep_data(user_id):
    return db.query("SELECT * FROM sleep_data WHERE user_id = ?;", (user_id,))

def new_sleep_data(date, user_id, sleep_time, wake_up_time, sleep_duration):
    rows = db.query_one("SELECT * FROM sleep_data WHERE user_id = ? AND date = ?;", (user_id, date))
    if not rows:
        db.execute("INSERT INTO sleep_data (date, user_id, sleep_time, wake_up_time, sleep_duration) VALUES (?, ?, ?, ?, ?);", (date, user_id, sleep_time, wake_up_time, sleep_duration))
    else:
        id = rows[0]
        date = date if date else rows[1]
        user_id = user_id if user_id else rows[2]
        sleep_time = sleep_time if sleep_time else rows[3]
        wake_up_time = wake_up_time if wake_up_time else rows[4]
        if sleep_duration and rows[5]:
            sleep_duration += rows[5]
        else:
            sleep_duration = sleep_duration if sleep_duration else rows[5]
        db.execute("UPDATE sleep_data SET date = ?, user_id = ?, sleep_time = ?, wake_up_time = ?, sleep_duration = ? WHERE sleep_data_id = ?;", (date, user_id, sleep_time, wake_up_time, sleep_duration, id))

def clear_out_date_data(user_id):
    rows = db.query("SELECT time FROM record WHERE user_id = ?;", (user_id,))
    if len(rows) > 30:
        for i in range(15):
            time = rows[i][0]
            db.execute("DELETE FROM record WHERE user_id = ? AND time = ?;", (user_id, time))
