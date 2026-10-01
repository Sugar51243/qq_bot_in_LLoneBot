
# == Tomori OurNotes插件入口 ==

# 接入本地OurNotes后端API(项目代号Tomori, 响应协议与茨菇tsugu兼容)
# 本文件仅负责指令路由，各功能按模块划分:
#   config(配置) / call_ournotes(后端连接) / db(数据库) / reply(多图嵌套聊天记录)
#   chart(谱面) / song(歌曲) / card(卡片) / event(活动榜线/推荐)
#   community(贴纸/车站/交友) / keyword(关键词) / announcement(公告: 一次性查询 + 注册制推流)
# 指令约定: 指令默认可裸用, 仅当指令与茨菇tsugu冲突且本场景已启用tsugu时
#   才需带前缀(tomori/ournotes/音符); 裸插件ID(tomori_ournotes)由核心显示帮助文档

import traceback
from OneBotConnecter.loger.log_info import log
from src.core.register import sreach_enabled_plugin
from src.plugins.tomori_ournotes.chart import sreach_chart, get_chart_data
from src.plugins.tomori_ournotes.song import sreach_song, song_meta, random_song
from src.plugins.tomori_ournotes.card import sreach_card, sreach_member_card, sreach_support_card, card_face, sreach_character, sreach_gacha, sreach_event, gacha_simulate
from src.plugins.tomori_ournotes.community import get_stamp_image, submit_room_number, room_list, friend_upload, friend_delete, friend_list
from src.plugins.tomori_ournotes.announcement import announcement_list, handle_announcement, start_announcement_stream
from src.plugins.tomori_ournotes.player import song_ranking, search_player
from src.plugins.tomori_ournotes.event import event_ranking, event_recommend
from src.plugins.tomori_ournotes.keyword import add_keyword, delete_keyword

#bot初始化时启动公告推流(main.py的load_plugin_listeners统一扫描调用)
def plugin_listener(bot):
    start_announcement_stream(bot)

#指令前缀(与茨菇tsugu冲突时使用)
PREFIX_SET = ["tomori", "ournotes", "音符", "on", "tmr"]

#与茨菇tsugu指令冲突的指令(本场景启用tsugu时须带前缀)
CONFLICT_COMMANDS = ["查谱", "查曲", "查卡", "查卡面", "查角色", "查卡池", "查活动", "卡池模拟", "抽卡模拟", "上传车牌", "ycm", "查玩家"]

def _conflict_with_tsugu(raw_message: str) -> bool:
    for cmd in CONFLICT_COMMANDS:
        if raw_message[:len(cmd)] == cmd:
            return True
    return False

def on_all_case(bot, message) -> bool: #call case including message, poke, request ...
    if "message" in message.event_type:
        return on_msg(bot, message=message)
    return False

def on_msg(bot, message) -> bool: # message
    try:
        return _handle(bot, message, message.text)
    except Exception as e:
        tb = e.__traceback__
        formatted_tb = ''.join(traceback.format_tb(tb))
        log(f"[TOMORI][{type(e)}] {e}\n{formatted_tb}")
    return False

def _handle(bot, message, raw_message: str) -> bool:
    if not raw_message: return False
    #剥离指令前缀
    prefixed = False
    for prefix in PREFIX_SET:
        if raw_message[:len(prefix)].lower() == prefix:
            raw_message = raw_message[len(prefix):].strip()
            prefixed = True
            break
    if not raw_message: return False
    #无前缀且指令与茨菇tsugu冲突时, 仅当tsugu未启用才由本插件接管
    if not prefixed and _conflict_with_tsugu(raw_message) and "tsugu" in sreach_enabled_plugin(message.scene_id):
        return False
    # == 谱面 ==
    # 查谱
    if raw_message[:2] == "查谱":
        parameter = raw_message.replace("查谱面", "查谱")
        parameter = parameter[2:].strip()
        sreach_chart(bot, message, parameter)
        return True
    # 谱面数据
    elif raw_message[:4] == "谱面数据":
        get_chart_data(bot, message, raw_message[4:].strip())
        return True
    # == 歌曲 ==
    # 查曲
    elif raw_message[:2] == "查曲":
        sreach_song(bot, message, raw_message[2:].strip())
        return True
    # 曲效率(歌曲meta效率排行; 曲表为旧名保留)
    elif raw_message[:3] == "曲效率":
        song_meta(bot, message, raw_message[3:].strip())
        return True
    # 曲表(旧名)
    elif raw_message[:2] == "曲表":
        song_meta(bot, message, raw_message[2:].strip())
        return True
    # 随机曲
    elif raw_message[:3] == "随机曲":
        random_song(bot, message, raw_message[3:].strip())
        return True
    # == 卡片 ==
    # 查卡面
    elif raw_message[:3] == "查卡面":
        card_face(bot, message, raw_message[3:].strip())
        return True
    # 卡面
    elif raw_message[:2] == "卡面":
        card_face(bot, message, raw_message[2:].strip())
        return True
    # 查卡池
    elif raw_message[:3] == "查卡池":
        sreach_gacha(bot, message, raw_message[3:].strip())
        return True
    # 查角色卡(需在查角色之前匹配)
    elif raw_message[:4] == "查角色卡":
        sreach_member_card(bot, message, raw_message[4:].strip())
        return True
    # 查支援卡
    elif raw_message[:4] == "查支援卡":
        sreach_support_card(bot, message, raw_message[4:].strip())
        return True
    # 查卡
    elif raw_message[:2] == "查卡":
        sreach_card(bot, message, raw_message[2:].strip())
        return True
    # 查角色
    elif raw_message[:3] == "查角色":
        sreach_character(bot, message, raw_message[3:].strip())
        return True
    # 查活动
    elif raw_message[:3] == "查活动":
        sreach_event(bot, message, raw_message[3:].strip())
        return True
    # 活动榜线
    elif raw_message[:4] == "活动榜线":
        event_ranking(bot, message, raw_message[4:].strip())
        return True
    # 榜线(活动榜线别名)
    elif raw_message[:2] == "榜线":
        event_ranking(bot, message, raw_message[2:].strip())
        return True
    # 活动推荐
    elif raw_message[:4] == "活动推荐":
        event_recommend(bot, message, raw_message[4:].strip())
        return True
    # 推荐曲(活动推荐别名)
    elif raw_message[:3] == "推荐曲":
        event_recommend(bot, message, raw_message[3:].strip())
        return True
    # 抽卡
    elif raw_message[:2] == "抽卡":
        gacha_simulate(bot, message, raw_message[2:].strip())
        return True
    # 卡池模拟(抽卡别名)
    elif raw_message[:4] == "卡池模拟":
        gacha_simulate(bot, message, raw_message[4:].strip())
        return True
    # == 玩家/排行 ==
    # 查排行
    elif raw_message[:3] == "查排行":
        song_ranking(bot, message, raw_message[3:].strip())
        return True
    # 查玩家(与tsugu查玩家冲突)
    elif raw_message[:3] == "查玩家":
        search_player(bot, message, raw_message[3:].strip())
        return True
    # 查账号(查玩家别名)
    elif raw_message[:3] == "查账号":
        search_player(bot, message, raw_message[3:].strip())
        return True
    # == 公告 ==
    # 公告列表(须在公告之前匹配)
    elif raw_message[:4] == "公告列表":
        announcement_list(bot, message, raw_message[4:].strip())
        return True
    # 公告(填ID→查详情; 未填→注册本场景推流; 关闭→取消注册)
    elif raw_message[:2] == "公告":
        handle_announcement(bot, message, raw_message[2:].strip())
        return True
    # == 社区 ==
    # 查贴纸
    elif raw_message[:3] == "查贴纸":
        get_stamp_image(bot, message, raw_message[3:].strip())
        return True
    # 上传车牌(与tsugu冲突)
    elif raw_message[:4] == "上传车牌":
        submit_room_number(bot, message, raw_message)
        return True
    # ycm(与tsugu冲突)
    elif raw_message.lower() == "ycm":
        room_list(bot, message)
        return True
    # 交友登记
    elif raw_message[:4] == "交友登记":
        friend_upload(bot, message, raw_message[4:].strip())
        return True
    # 删除交友
    elif raw_message[:4] == "删除交友":
        friend_delete(bot, message)
        return True
    # 交友列表
    elif raw_message[:4] == "交友列表":
        friend_list(bot, message)
        return True
    # 新增关键词
    elif raw_message[:5] == "新增关键词":
        add_keyword(bot, message, raw_message[5:].strip())
        return True
    # 删除关键词
    elif raw_message[:5] == "删除关键词":
        delete_keyword(bot, message, raw_message[5:].strip())
        return True
    return False
