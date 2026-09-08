
# == SleepAssistant分析模块 ==

# 睡眠时间分析/早安消息生成/时间工具函数

import datetime
from OneBotConnecter.types import MessageChain
from OneBotConnecter.loger.log_info import log
from src.plugins.sleep_assistant.db import return_sleep_data
from src.tools.reply_message import feedback

def good_morning(bot, message, user_id, user_data):
    #
    sleep_datas = return_sleep_data(user_id)
    if len(sleep_datas) <= 0: return
    sleep_data_id, date, user_id, sleep_time, wake_up_time, sleep_duration = sleep_datas[-1]
    sleep_datas = list(sleep_datas)
    sleep_datas.remove((sleep_data_id, date, user_id, sleep_time, wake_up_time, sleep_duration))
    # 计算平均睡眠时长
    sleep_durations = [row[5] for row in sleep_datas if row[5] is not None]
    avg_sleep_duration = sum(sleep_durations) / len(sleep_durations) if sleep_durations else None
    log(f"用户{message.raw_data.get('user_id')}的睡眠时长为{sleep_duration:.1f}小时")
    if avg_sleep_duration: log(f"平均睡眠时长为{avg_sleep_duration:.1f}小时")
    # 计算平均起床时间
    wake_up_times = [timestamp_to_hms(row[4]) for row in sleep_datas if row[4] is not None]
    avg_wake_up_time = sum(wake_up_times) / len(wake_up_times) if wake_up_times else 0
    avg_wake_up_time_str = hms_to_str(avg_wake_up_time) if wake_up_times else None
    log(f"用户{message.raw_data.get('user_id')}的起床时间为{wake_up_time:.1f}小时")
    if wake_up_times: log(f"平均起床时间为{wake_up_times}")
    if avg_wake_up_time_str: log(f"平均起床时间为{avg_wake_up_time_str}")
    # 计算平均睡觉时间
    sleep_times = [timestamp_to_hms(row[3], mode="sleep") for row in sleep_datas if row[3] is not None]
    avg_sleep_time = sum(sleep_times) / len(sleep_times) if sleep_times else 0
    avg_sleep_time_str = hms_to_str(avg_sleep_time) if sleep_times else None
    log(f"用户{message.raw_data.get('user_id')}的睡觉时间为{sleep_time:.1f}小时")
    if sleep_times: log(f"平均睡觉时间为{sleep_times}")
    if avg_sleep_time_str: log(f"平均睡觉时间为{avg_sleep_time_str}")
    # 生成早安消息
    now = datetime.datetime.fromtimestamp(wake_up_time).strftime('%Y-%m-%d %H:%M:%S')
    send_message = MessageChain([f"\n目前时间为:\n{now} (UTC{user_data[1]:+d})\n你已经睡了{sleep_duration:.1f}小时。"])
    # 根据睡眠时长和平均睡眠时长、平均起床时间、平均睡觉时间来生成个性化的消息
    # 睡眠时长
    if avg_sleep_duration:
        sleep_duration_diff = sleep_duration - avg_sleep_duration
        msg = f"\n时长比平时多了{sleep_duration_diff:.1f}小时" if sleep_duration_diff>0 else f"\n时间比平时少了{-sleep_duration_diff:.1f}小时"
        send_message.add(msg)
    # 起床时间
    if avg_wake_up_time:
        wake_up_diff = timestamp_to_hms(wake_up_time)/3600 - avg_wake_up_time/3600
        msg = f"\n起床比平时晚了{wake_up_diff:.1f}小时" if wake_up_diff>0 else f"\n起床比平时早了{-wake_up_diff:.1f}小时"
        send_message.add(msg)
    # 睡觉时间
    if avg_sleep_time:
        time_diff = timestamp_to_hms(sleep_time, mode="sleep")/3600 - avg_sleep_time/3600
        msg = f"\n睡觉比平时迟了{time_diff:.1f}小时" if time_diff>0 else f"\n睡觉比平时早了{-time_diff:.1f}小时"
        send_message.add(msg)
    # 昨日清醒时长
    if sleep_duration:
        wake_up_duration = 24 - sleep_duration
        send_message.add(f"\n昨日总清醒时长: {int(wake_up_duration)}:{int((wake_up_duration % 1) * 60):02d}")
    # 发送早安消息
    feedback(message, send_message)
    # 额外追加
    # 根据当前时间和睡眠时长来生成个性化的消息
    now_time = timestamp_to_hour(wake_up_time)
    log(f"当前时间为{now_time:.1f}点，睡眠时长为{sleep_duration:.1f}小时")
    if now_time <= 6: # 如果当前时间在凌晨6点之前，发送早安消息
        feedback(message, MessageChain(["早！今天好早啊！今天是有事要做吗？"]))
    elif now_time <= 9: # 如果当前时间在早上9点之前
        feedback(message, MessageChain(["早安！"]))
    elif now_time <= 14 or 11 > sleep_duration > 9 or (avg_sleep_duration and sleep_duration > avg_sleep_duration + 2): # 如果当前时间在下午4点之前，或者睡眠时间超过9小时，或者睡眠时间比平均睡眠时间长了2小时以上，发送消息
        feedback(message, MessageChain(["🐖!"]))
    elif now_time <= 16: # 如果当前时间在下午4点之前，发送消息
        feedback(message, MessageChain(["🐖!晚上还要不要继续睡了？"]))

def piece_sleep_info(bot, message, user_id, user_data, now_time):
    sleep_datas = return_sleep_data(user_id)
    if len(sleep_datas) <= 0: return
    sleep_data_id, date, user_id, sleep_time, wake_up_time, sleep_duration = sleep_datas[-1]
    # 发送睡眠信息总结
    now = datetime.datetime.fromtimestamp(now_time).strftime('%Y-%m-%d %H:%M:%S')
    send_message = MessageChain([f"\n目前时间为{now} (UTC{user_data[1]:+d})，你已经睡了{sleep_duration:.1f}小时。"])
    if sleep_duration > 3:
        send_message.add("\n小睡怎么能睡超过3小时呢？🐖吗?")
    else:
        send_message.add("\n睡了个好觉吗？")
    feedback(message, send_message)

# == 时间工具 ==

def timestamp_to_hour(timestamp=None):
    time = datetime.datetime.fromtimestamp(timestamp)
    return time.hour + time.minute / 60 + time.second / 3600

def timestamp_to_sleep_duration(sleep_time, wake_up_time):
    sleep_duration = wake_up_time - sleep_time if wake_up_time >= sleep_time else wake_up_time + 24 - sleep_time
    return sleep_duration / 3600 # 将睡眠时长转换为小时

def timestamp_to_date(timestamp):
    return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')

def get_time_periods(sleep_datas, time):
    sleep_time_zone = (20, 24+5) # 默认睡觉时间为UTC的20:00-05:00
    wake_up_time_zone = (4, 17) # 默认起床时间为UTC的4:00-17:00
    #如果用户的睡眠记录超过10条，则根据用户的平均睡眠时间和平均起床时间来调整时间段
    a, b, i = 0, 0, 0
    for sleep_data_id, date, user_id, sleep_time, wakeup_time, sleep_duration in sleep_datas:
        if not sleep_time or not wakeup_time:
            continue
        if a == 0: a = timestamp_to_hour(sleep_time)
        if b == 0: b = timestamp_to_hour(wakeup_time)
        a = (a+(timestamp_to_hour(sleep_time) if timestamp_to_hour(sleep_time) >= 12 else timestamp_to_hour(sleep_time)+24))/2
        b = (b+timestamp_to_hour(wakeup_time))/2
        i+=1
    if i > 11:
        sleep_time_zone = (a-3 if a-3>0 else a+24-3, a+3 if a-3>0 else a+24+3)
        wake_up_time_zone = (b-3 if b-3>0 else b+24-3, b+8 if b-3>0 else b+24+8)
    hour_1 = timestamp_to_hour(time) if timestamp_to_hour(time)>sleep_time_zone[0] else timestamp_to_hour(time)+24
    hour_2 = timestamp_to_hour(time) if timestamp_to_hour(time)>wake_up_time_zone[0] else timestamp_to_hour(time)+24
    log(f"hour_1: {hour_1} | hour_2: {hour_2}")
    log(f"sleep_time_zone: {sleep_time_zone} | wake_up_time_zone: {wake_up_time_zone}")
    return sleep_time_zone[0] < hour_1 < sleep_time_zone[1], wake_up_time_zone[0] < hour_2 < wake_up_time_zone[1]

def timestamp_to_hms(timestamp, mode="wakeup"):
    dt = datetime.datetime.fromtimestamp(timestamp)
    if dt.hour < 12 and mode != "wakeup": seconds = (dt.hour+24) * 3600 + dt.minute * 60 + dt.second
    else: seconds = dt.hour * 3600 + dt.minute * 60 + dt.second
    return seconds

def hms_to_str(hms):
    h = int(hms/3600)
    m = int((hms - h * 3600) /60)
    s = int((hms - h * 3600) - m*60)
    return f"{h}:{m}:{s}"
