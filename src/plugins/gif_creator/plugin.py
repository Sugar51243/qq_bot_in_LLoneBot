
# == 图片合成插件入口 ==

# 由v1(src/plugin/表情包合成/main.py)迁移至v2插件格式
# 本文件负责指令路由与合成处理，各模块:
#   db(昵称绑定) / img_tools(图像处理工具)
# 模板GIF位于data/plugin/gif_creator/，输出位于data/plugin/gif_creator/output/

import os, traceback, requests
from io import BytesIO
from PIL import Image
import numpy as np
from OneBotConnecter.types import MessageChain, ImageMessage
from OneBotConnecter.loger.log_info import log
from src.project_locator.project_locator import get_project_location
from src.plugins.gif_creator.db import read_nick_names
from src.plugins.gif_creator.img_tools import get_target_img, image_to_c, make_up_gif
from src.plugins.gif_creator.img_tools import get_img, get_img_frame, save_gif, get_command_direction, change_speed_frame
from src.tools.reply_message import feedback

# 文件路径
template_dir = os.path.join(get_project_location(), "data", "plugin", "gif_creator")
img_output_path = os.path.join(template_dir, "output")
bit_path = os.path.join(template_dir, "Erenn.gif")
fuck_path = os.path.join(template_dir, "fuc.gif")

# == 入口 ==

def on_all_case(bot, message) -> bool: #call case including message, poke, request ...
    if "message" in message.event_type:
        return on_msg(bot, message=message)
    return False

def on_msg(bot, message) -> bool: # message
    if message.event_type not in ["group_message", "private_message"]:
        return False
    raw_message = message.text
    if not raw_message: return False
    if message.event_type == "group_message":
        # 抽
        if raw_message[0] in ["抽"]:
            log(f"图片合成 - 抽")
            sender = message.user_id
            #获取头像
            [avatar_path, avatar_path_1] = image_get_target(bot, message, raw_message, message.at_me)
            if [avatar_path, avatar_path_1] == [None, None]: return False #无目标时不视为已处理
            outputGIF = os.path.join(img_output_path, "bit", f"{sender}_bit.gif")
            #合成
            try:
                bit(
                    user_1 = avatar_path,
                    user_2 = avatar_path_1,
                    output_path = outputGIF
                    )
                msg = ImageMessage(outputGIF)
                callback = bot.send_group_msg(message.raw_data.get("group_id"), msg)
                log(f"{callback.raw_data}")
            except Exception as e:
                tb = e.__traceback__
                formatted_tb = ''.join(traceback.format_tb(tb))
                log(f"[{type(e)}] {e}\n{formatted_tb}")
            return True
        # 撅
        elif raw_message[0] in ["撅", "艹"]:
            log(f"图片合成 - 撅")
            sender = message.user_id
            #获取头像
            [avatar_path, avatar_path_1] = image_get_target(bot, message, raw_message, message.at_me)
            if [avatar_path, avatar_path_1] == [None, None]: return False #无目标时不视为已处理
            outputGIF = os.path.join(img_output_path, "fuck", f"{sender}_fuc.gif")
            #合成
            try:
                fuck(
                    user_1 = avatar_path,
                    user_2 = avatar_path_1,
                    output_path = outputGIF)
                msg = ImageMessage(outputGIF)
                callback = bot.send_group_msg(message.raw_data.get("group_id"), msg)
                log(f"{callback.raw_data}")
            except Exception as e:
                tb = e.__traceback__
                formatted_tb = ''.join(traceback.format_tb(tb))
                log(f"[{type(e)}] {e}\n{formatted_tb}")
            return True
    #镜像
    if raw_message[:2] in ["镜像"]:
        log(f"图片合成 - 镜像")
        mirror(bot, message, raw_message)
        return True
    #变速
    elif raw_message[:3] in ["渐变速"]:
        log(f"图片合成 - 渐变速")
        change_speed_gradient(bot, message, raw_message)
        return True
    elif raw_message[:2] in ["变速"]:
        log(f"图片合成 - 变速")
        change_speed(bot, message, raw_message)
        return True
    elif raw_message[0] in ["摸"]:
        log(f"图片合成 - 摸")
        sender = message.user_id
        output_path = os.path.join(img_output_path, "touch", f"{sender}_touch.gif")
        touch(bot, message, output_path)
        return True
    return False

#抽
def bit(user_1, user_2, output_path):
    avatar_path = user_1
    avatar_path_1 = user_2
    gif_path = bit_path
    # 读取原GIF的所有帧和时长
    isGIF, gif_frames, gif_durations = get_img_frame(gif_path)
    # 获取图片二进制数据
    try:
        avatar, avatar_1 = get_target_img(avatar_path, avatar_path_1, 22, 22)
    except Exception as e:
        tb = e.__traceback__
        formatted_tb = ''.join(traceback.format_tb(tb))
        log(f"[{type(e)}] {e}\n{formatted_tb}")
        return
    # 头像图片 -> 圆形头像
    avatar = image_to_c(avatar)
    avatar_1 = image_to_c(avatar_1)
    # 逐帧替换头像
    positions = [(84, 25), (87, 24), (87, 28), (86, 28), (62, 26), (59, 28), (76, 20), (85, 25), (80, 23)]
    positions_1 = [(12, 69), (15, 66), (14, 67), (15, 66), (17, 67), (14, 63), (21, 56), (15, 62), (17, 69)]
    new_frames = make_up_gif(gif_frames, avatar, avatar_1, positions, positions_1)
    # 保存新GIF
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    save_gif(new_frames, gif_durations, output_path)
#撅
def fuck(user_1, user_2, output_path):
    avatar_path = user_1
    avatar_path_1 = user_2
    gif_path = fuck_path
    # 读取原GIF的所有帧和时长
    isGIF, gif_frames, gif_durations = get_img_frame(gif_path)
    # 获取图片二进制数据
    try:
        avatar, avatar_1 = get_target_img(avatar_path, avatar_path_1, 120, 120)
    except Exception as e:
        tb = e.__traceback__
        formatted_tb = ''.join(traceback.format_tb(tb))
        log(f"[{type(e)}] {e}\n{formatted_tb}")
        return
    # 头像图片 -> 圆形头像
    avatar = image_to_c(avatar)
    avatar_1 = image_to_c(avatar_1)
    avatar = avatar.rotate(30, expand=True)
    avatar_1 = avatar_1.rotate(100, expand=True)
    # 逐帧替换头像
    positions = [(95, -30), (90, -15), (110, -30)]
    positions_1 = [(-10, 165), (0, 160), (-10, 140)]
    new_frames = make_up_gif(gif_frames, avatar, avatar_1, positions, positions_1)
    # 保存新GIF
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    save_gif(new_frames, gif_durations, output_path)
#摸
def touch(bot, message, output_path, reply = None):
    user_id = None
    for ms in message.message:
        log(f"正在检查消息: {ms.__dict__}")
        if not ms.type in ["at", "text", "reply"]: continue
        if ms.type == "at":
            user_id = ms.data.qq
            break
        elif ms.type == "text":
            target_msg = ms.data.text
            target_msg = target_msg.replace("摸", "").strip()
            nickNameList = read_nick_names()
            user_id = nickNameList.get(target_msg.lower(), None)
            if user_id: break
            target_msg = target_msg.replace("@", "").strip()
            if target_msg.isdigit():
                user_id = target_msg
                break
        elif ms.type == "reply":
            reply_id = ms.data.id
            reply_msg = bot.get_msg(reply_id)
            reply_message = type("TmpMsg", (), {})()
            reply_message.message = []
            for raw_msg in reply_msg.data.message:
                item = type("TmpItem", (), {})()
                item.type = raw_msg.get("type")
                item.data = type("TmpData", (), {})()
                for k, v in raw_msg.get("data", {}).items():
                    setattr(item.data, k, v)
                reply_message.message.append(item)
            base = reply if reply else message
            touch(bot, reply_message, output_path, base)
            return
    base = reply if reply else message
    if not user_id:
        return
    url = f"https://uapis.cn/api/v1/image/motou?qq={user_id}"
    result = requests.get(url=url)
    if result.status_code != 200:
        feedback(base, MessageChain(["接口连接失败"]))
        return
    if result.headers.get("Content-Type", None) != "image/gif":
        feedback(base, MessageChain(["今月接口用量超额/无法使用"]))
        return
    data = result.content
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb+") as file:
        file.write(data)
    feedback(base, ImageMessage(output_path))

#镜像
def mirror(bot, message, raw_message):
    command = raw_message[raw_message.find("镜像")+2:].strip()
    target_l, target_h = get_command_direction(command)
    if not target_l and not target_h: target_l = "left"
    reply_id, user_id = None, None
    imageName, url = None, None
    messages = message.message
    log("正在查找回复消息")
    #查找图片消息、回复消息和艾特消息
    size_limit = 7000000
    reply_msg = None
    for ms in messages:
        log(f"正在检查消息: {ms.__dict__}")
        if ms.type == "reply":
            reply_id = ms.data.id
            break
        elif ms.type == "image":
            log(f"图片size: {ms.data.file_size}")
            if int(ms.data.file_size) >= size_limit:
                log("图片过大，无法处理")
                msg = MessageChain(["\n图片过大，无法处理"])
                feedback(message, msg)
                continue
            imageName = ms.data.file
            url = ms.data.url
            break
        elif ms.type == "at":
            user_id = ms.data.qq
            break
    if not reply_id and not user_id and not imageName:
        log("未找到回复消息、艾特用户或图片消息")
        return
    if not url and not imageName:
        try:
            reply_msg = bot.get_msg(reply_id)
            log(f"{reply_msg.raw_data}")
            messages = reply_msg.data.message
            for ms in messages:
                log(f"正在检查消息: {ms}")
                if ms["type"] == "image":
                    log(f"图片size: {ms['data']['file_size']}")
                    if int(ms["data"]["file_size"]) >= size_limit:
                        log("图片过大，无法处理")
                        msg = MessageChain(["\n图片过大，无法处理"])
                        feedback(message, msg)
                        continue
                    imageName = ms["data"]["file"]
                    url = ms["data"]["url"]
                    break
                elif ms["type"] == "mface":
                    imageName = ms["data"]["summary"]
                    url = ms["data"]["url"]
                    break
        except Exception as e:
            pass
    if user_id != None:
        imageName = f"{user_id}.jpg"
        url = f"https://q1.qlogo.cn/g?b=qq&nk={user_id}&s=640"
    if not imageName or not url:
        imageName = f"{reply_msg.data.sender.user_id}.jpg"
        url = f"https://q1.qlogo.cn/g?b=qq&nk={reply_msg.data.sender.user_id}&s=640"
    #获取图片
    image = None
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        image_data = BytesIO(response.content)
        image = Image.open(image_data)
    except Exception as e:
        tb = e.__traceback__
        formatted_tb = ''.join(traceback.format_tb(tb))
        log(f"[{type(e)}] {e}\n{formatted_tb}")
        return
    if not image:
        log("打开图片失败")
        return
    isGIF, image, gif_durations = get_img_frame(url)
    mask_color = 0
    temp_list = []
    for im in image:
        arr = np.array(im, dtype=np.uint8)
        h, w = arr.shape[:2]
        mask = np.ones((h, w), dtype=bool)
        # 根据目标方向设置遮罩
        if target_l == "left":
            t = w//2
            # 修正奇数宽度的镜像
            if w%2==1:
                t+=1
            mask[:, t:] = False
        elif target_l == "right":
            t = w//2
            # 修正奇数宽度的镜像
            if w%2==1:
                t+=1
            mask[:, :t] = False
        elif target_h == "up":
            t = h//2
            # 修正奇数宽度的镜像
            if h%2==1:
                t+=1
            mask[t:, :] = False
        elif target_h == "down":
            t = h//2
            # 修正奇数宽度的镜像
            if h%2==1:
                t+=1
            mask[:t, :] = False
        # 应用遮罩
        mask=np.repeat(mask[:, :, np.newaxis], 4, axis=2)
        masked = arr.copy()
        masked[~mask] = np.array(mask_color, dtype=np.uint8)
        half = Image.fromarray(masked)
        # 镜像并拼接
        if target_l != None: temp = half.transpose(Image.FLIP_LEFT_RIGHT)
        elif target_h != None: temp = half.transpose(Image.FLIP_TOP_BOTTOM)
        temp.paste(half, (0,0), mask=half)
        temp_list.append(temp)
    image = temp_list
    os.makedirs(os.path.join(img_output_path, "mirror"), exist_ok=True)
    if not isGIF:
        output_path = os.path.join(img_output_path, "mirror", f"{message.user_id}_mirror.png")
        image[0].save(output_path)
    else:
        output_path = os.path.join(img_output_path, "mirror", f"{message.user_id}_mirror.gif")
        save_gif(image, gif_durations, output_path)
    msg = ImageMessage(output_path)
    message.reply_message(msg)
    log(f"镜像已发送")
#变速
def change_speed(bot, message, raw_message):
    command = raw_message[raw_message.find("变速")+2:].strip()
    # 解析命令参数
    if len(command)>0:
        if command[0].lower() in ["x", "×"]:
            command = command[1:].strip()
    try: speed = float(command)
    except: speed = 2.0
    log(f"变速倍数: {speed}")
    # 获取目标图片URL
    image, url = get_img(bot, message, 7000000)
    if not url:
        message.reply_message(MessageChain(["图片获取失败"]))
        return
    # 变速处理
    #读取GIF的所有帧和时长
    isGIF, image, gif_durations = get_img_frame(url)
    if not image or not gif_durations:
        log(f"读取GIF帧失败")
        return
    if not isGIF:
        log(f"该图片不是GIF")
        return
    # 变速
    image, gif_durations, cuted = change_speed_frame(image, gif_durations, speed)
    # 保存新GIF
    os.makedirs(os.path.join(img_output_path, "speed"), exist_ok=True)
    output_path = os.path.join(img_output_path, "speed", f"{message.user_id}_mirror.gif")
    save_gif(image, gif_durations, output_path)
    msg = MessageChain([])
    if cuted: msg.add("\n该图速度过快")
    msg.add(ImageMessage(output_path))
    message.reply_message(msg)
#循环变速
def change_speed_gradient(bot, message, raw_message):
    speed = 1.5
    # 获取目标图片URL
    image, url = get_img(bot, message, size_limit=3000000)
    if not image and not url: return
    # 变速处理
    #读取GIF的所有帧和时长
    isGIF, image, gif_durations = get_img_frame(url)
    if not image or not gif_durations:
        log(f"读取GIF帧失败")
        return
    if not isGIF:
        log(f"该图片不是GIF")
        return
    # 变速
    temp, temp_durations = [], []
    changed_temp, changed_temp_durations = [image], [gif_durations]
    while len(image) > 2:
        image, gif_durations, cutted = change_speed_frame(image, gif_durations, speed)
        temp.extend(image)
        temp_durations.extend(gif_durations)
        changed_temp.append(image)
        changed_temp_durations.append(gif_durations)
    while len(changed_temp) > 0:
        temp.extend(changed_temp.pop())
        temp_durations.extend(changed_temp_durations.pop())
    # 保存新GIF
    image = temp
    gif_durations = temp_durations
    os.makedirs(os.path.join(img_output_path, "speed"), exist_ok=True)
    output_path = os.path.join(img_output_path, "speed", f"{message.user_id}_mirror.gif")
    non_background = False
    for frame in image:
        img= frame.convert("RGBA")
        alpha = img.getchannel("A")
        extrema = alpha.getextrema()
        if extrema[0]<255:
            non_background = True
            break
    save_gif(image, gif_durations, output_path, non_background)
    msg = ImageMessage(output_path)
    message.reply_message(msg)

# == Tools ==
#获取头像uri
def image_get_target(bot, message, raw_message, be_at):
    #获取发送者头像 => 参数1
    sender = message.user_id
    avatar_path = f"https://q1.qlogo.cn/g?b=qq&nk={sender}&s=640" #参数1
    #获取对像头像 => 参数2
    raw_message = raw_message[1:].strip()
    avatar_path_1 = None
    #艾特
    for ms in message.message:
        if ms.type == "at":
            if str(ms.data.qq) != str(bot.bot.user_id):
                avatar_path_1 = str(ms.data.qq)
            else:
                avatar_path_1 = str(bot.bot.user_id)
            break
    #昵称
    if avatar_path_1 == None:
        nickNameList = read_nick_names()
        try:
            avatar_path_1 = nickNameList[raw_message.lower()]
        except:
            #小生物
            if be_at and len(raw_message)==0:
                avatar_path_1 = str(bot.bot.user_id)
            #文字@艾特
            elif "@" in raw_message:
                raw_message = raw_message[raw_message.find("@")+1:].strip()
                if raw_message.isdigit():
                    avatar_path_1 = raw_message
            #直接发送qq号
            elif raw_message.isdigit():
                avatar_path_1 = raw_message
    #查空
    if avatar_path_1 == None:
        return [None, None]
    avatar_path_1 = f"https://q1.qlogo.cn/g?b=qq&nk={avatar_path_1}&s=640" #参数2
    #防止抽到bot管理员头像 => 反转参数
    if str(sender) not in [str(owner_id) for owner_id in bot.bot.owner]:
        #小生物
        if avatar_path_1 == f"https://q1.qlogo.cn/g?b=qq&nk={bot.bot.user_id}&s=640":
                avatar_path, avatar_path_1 = f"https://q1.qlogo.cn/g?b=qq&nk={bot.bot.owner[0]}&s=640", avatar_path
        #bot管理员
        else:
            for owner_id in bot.bot.owner:
                if avatar_path_1 == f"https://q1.qlogo.cn/g?b=qq&nk={owner_id}&s=640":
                    avatar_path, avatar_path_1 = f"https://q1.qlogo.cn/g?b=qq&nk={bot.bot.owner[0]}&s=640", avatar_path
                    break
    log(f"获取头像: [{avatar_path}, {avatar_path_1}]")
    return [avatar_path, avatar_path_1]
