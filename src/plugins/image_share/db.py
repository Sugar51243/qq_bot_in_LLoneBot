
# == ImageShare插件数据库模块 ==

# 数据储存于sqlite(data/db/ImageShare.db)，分表储存:
#   image_info(图片记录) / short_cut(快捷词对应图片)
# 图片本体储存于data/plugin/image_share/image_database/

import os
from src.project_locator.project_locator import get_project_location
from src.db_handler.plugin_db import PluginDB

db = PluginDB("图片分享", {
    "image_info": "CREATE TABLE IF NOT EXISTS image_info (id TEXT PRIMARY KEY, names TEXT NOT NULL, uploader TEXT NOT NULL, checksum TEXT NOT NULL);",
    "short_cut": "CREATE TABLE IF NOT EXISTS short_cut (name TEXT NOT NULL, image_id TEXT NOT NULL, PRIMARY KEY(name, image_id));"
}, db_name="ImageShare")

image_database = os.path.join(get_project_location(), "data", "plugin", "image_share", "image_database")
