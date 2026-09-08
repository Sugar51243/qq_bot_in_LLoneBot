
# == Pjsk曲库模块 ==

# 曲库为静态缓存文件(data/plugin/pjsk/musics.json)

import os, json
from OneBotConnecter.loger.log_info import log
from src.project_locator.project_locator import get_project_location

song_list_file = os.path.join(get_project_location(), "data", "plugin", "pjsk", "musics.json")

def get_song_list():
    try:
        file = open(song_list_file, "r", encoding="utf-8")
        context = file.read()
        song_list = json.loads(context)
        log(f"song list: {len(song_list)}")
        return song_list
    except Exception as e: log(f"API error: {e}")
    return []

def song_id(parameter: list):
    log(f"parameter: {parameter}")
    if not parameter: return None
    test = parameter[0]
    if test.isdigit(): return [int(parameter[0])]
    song_list = get_song_list()
    #歌名
    temp = list(song_list)
    for p in parameter:
        temp = [song for song in temp if p.lower() in song["title"].lower()]
    log(f"Filtered: {temp}")
    return [song["id"] for song in temp]
