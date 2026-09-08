
# == 智能早安插件入口 ==

# 由v1(src/plugin/睡眠助手/main.py)迁移至v2插件格式
# 本文件负责消息流程，各功能按模块划分:
#   db(数据库操作) / analyze(睡眠分析与早安生成)

import datetime, traceback
from OneBotConnecter.types import MessageChain
from OneBotConnecter.loger.log_info import log
from src.plugins.sleep_assistant.db import get_user_data, clear_out_date_data, update_record
from src.plugins.sleep_assistant.db import plugin_off, plugin_on, good_night, non_good_night, update_time_zone
from src.plugins.sleep_assistant.db import get_last_msg_time, return_sleep_data, new_sleep_data
from src.plugins.sleep_assistant.analyze import good_morning, piece_sleep_info, get_time_periods
from src.plugins.sleep_assistant.analyze import timestamp_to_sleep_duration, timestamp_to_date
from src.tools.reply_message import feedback

# == 入口 ==

def on_all_case(bot, message) -> bool: #call case including message, poke, request ...
    return _handle(bot, message)

def on_msg(bot, message) -> bool: # message
    return _handle(bot, message)

def _handle(bot, message) -> bool:
    try:
        raw_message = message.text
        #==取得基础信息==
        user_id = message.raw_data.get("user_id", None)
        time = message.raw_data.get("time", None)
        if not user_id or not time:
            return False

        #连接数据库
        user_data = get_user_data(user_id)
        clear_out_date_data(user_id)

        #根据用户的时区调整时间戳，统一转换为用户所在时区的时间进行处理
        time = (time - 8 * 3600)
        time = (time + user_data[1] * 3600)

        #testing code
        if str(user_id) in [str(owner_id) for owner_id in bot.bot.owner]:
            time = (time - 0 * 3600)

        #==更新最后信息记录==
        update_record(user_id, time)

        #==处理插件开关指令==(裸"开启/关闭"为核心指令，避免冲突)
        if raw_message in ["关闭功能", "停用功能"] and user_data[2]:
            plugin_off(user_id)
            feedback(message, MessageChain([f"睡眠插件已关闭(对个人)"]))
            return True
        elif raw_message in ["开启功能", "启用功能"] and not user_data[2]:
            plugin_on(user_id)
            feedback(message, MessageChain([f"睡眠插件已开启(对个人)"]))
            return True
        if not user_data[2]:
            return False

        #==晚安指令和时区设置指令==
        if raw_message in ["晚安", "眠", "睡了"] and not user_data[3]:
            good_night(user_id)
            feedback(message, MessageChain(["晚安了，祝你有个好梦！"]))
            return True
        elif raw_message in ["取消晚安", "不睡了", "不眠", "不睡"] and user_data[3]:
            non_good_night(user_id)
            feedback(message, MessageChain(["好吧，记得早点睡"]))
            return True
        elif raw_message[0:4] in ["设置时区"]:
            try:
                time_zone = int(raw_message[4:].strip())
                if -12 <= time_zone <= 14:
                    update_time_zone(user_id, time_zone)
                    feedback(message, MessageChain([f"时区设置成功！当前时区为UTC{time_zone:+d}。"]))
                else:
                    feedback(message, MessageChain([f"时区设置失败！请提供一个介于-12和14之间的整数。"]))
            except ValueError:
                feedback(message, MessageChain([f"时区设置失败！请提供一个有效的整数。"]))
            return True

        #==分析==
        last_message_time = get_last_msg_time(user_id)
        now_time = time
        if last_message_time == 0:
            return False

        #睡觉时间段/起床时间段识别
        sleep_data = return_sleep_data(user_id)
        old_message_isSleep, old_message_isWakeUp = get_time_periods(sleep_data, last_message_time)
        new_message_isSleep, new_message_isWakeUp = get_time_periods(sleep_data, time)
        if user_data[3]: old_message_isSleep = True
        if raw_message in ["早", "早安", "早上好"]: new_message_isWakeUp = True
        log(f"当前时间为{datetime.datetime.fromtimestamp(now_time).strftime('%Y-%m-%d %H:%M:%S')}点")
        log(f"用户{user_id}的上条消息的睡觉时间段为：{old_message_isSleep}，起床时间段为：{old_message_isWakeUp}")
        log(f"用户{user_id}的新消息的睡觉时间段为：{new_message_isSleep}，起床时间段为：{new_message_isWakeUp}")

        #时长计算
        sleep_duration = timestamp_to_sleep_duration(last_message_time, time)
        log(f"用户{user_id}距离上次消息的时间为{sleep_duration:.1f}小时")

        #==处理==
        #如果新消息的时间戳比上次消息的时间戳大超过24小时，说明用户很久没有发消息了，更新最后消息时间并返回
        if user_data[3]: non_good_night(user_id)
        if sleep_duration >= 24:
            bot.send_msg(user_id=user_id, message=MessageChain(["昨天没发过信息呢？是很忙吗？"]), group_id=message.raw_data.get("group_id", None))
            log(f"用户{user_id}距离上次消息的时间超过24小时，更新最后消息时间并返回")
        #
        elif old_message_isSleep and new_message_isWakeUp and sleep_duration > 4:
            date = datetime.datetime.fromtimestamp(time - 24*3600).strftime('%Y%m%d')
            new_sleep_data(date, user_id, last_message_time, now_time, sleep_duration)
            good_morning(bot, message, user_id, user_data)
        #
        elif old_message_isSleep and new_message_isWakeUp and not new_message_isSleep and sleep_duration < 2 and not user_data[3]:
            bot.send_msg(user_id=message.raw_data.get("user_id"), message=MessageChain(["怎么熬夜了？"]), group_id=message.raw_data.get("group_id", None))
        #
        else:
            if user_data[3]:
                if sleep_duration >= 1.0: # 如果距离上次消息超过1.0小时，假设用户已经睡了
                    date = timestamp_to_date(now_time)
                    new_sleep_data(date, user_id, None, None, sleep_duration)
                    piece_sleep_info(bot, message, user_id, user_data, now_time)
                else:
                    log(f"用户{user_id}距离上次消息的时间不到1小时，假设用户还没有睡，发送提醒消息")
                    send_message = MessageChain(["时间不足，已取消晚安记录"])
                    bot.send_msg(user_id=user_id, message=send_message, group_id=message.raw_data.get("group_id", None))
        return True
    except Exception as e:
        tb = e.__traceback__
        formatted_tb = ''.join(traceback.format_tb(tb))
        log(f"[{type(e)}] {e}\n{formatted_tb}")
    return False
