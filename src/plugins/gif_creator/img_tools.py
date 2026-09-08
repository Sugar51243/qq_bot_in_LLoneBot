
# == GifCreator图片工具模块 ==

# GIF帧读取/合成/保存/变速等图像处理工具函数

import traceback, imageio, requests
from io import BytesIO
from PIL import Image, ImageDraw
from OneBotConnecter.types import MessageChain
from OneBotConnecter.loger.log_info import log
from src.tools.reply_message import feedback

#获取头像图片
def get_target_img(avatar_path, avatar_path_1=None, resize_x=None, resize_y=None):
    # 发送请求获取图片二进制数据
    response = requests.get(avatar_path, timeout=10)
    response.raise_for_status()  # 若请求失败（如404/500），抛出异常
    # 将二进制数据转为PIL可读取的数据流，再打开图片
    image_data = BytesIO(response.content)
    avatar = Image.open(image_data)
    #
    avatar_1 = None
    if avatar_path_1 != None:
        # 发送请求获取图片二进制数据
        response = requests.get(avatar_path_1, timeout=10)
        response.raise_for_status()  # 若请求失败（如404/500），抛出异常
        # 将二进制数据转为PIL可读取的数据流，再打开图片
        image_data = BytesIO(response.content)
        avatar_1 = Image.open(image_data)
    if resize_x!=None and resize_y!=None:
        try:
            avatar = avatar.resize((resize_x, resize_y), Image.Resampling.LANCZOS)
            avatar_1 = avatar_1.resize((resize_x, resize_y), Image.Resampling.LANCZOS)
        except: pass
    return [avatar, avatar_1]
# 头像图片 -> 圆形头像
def image_to_c(image):
    width, height = image.size
    # 取宽高中的最小值作为圆形直径，保证正圆
    diameter = min(width, height)
    # 创建圆形遮罩
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    # 绘制正圆（圆心为图片中心，半径为直径/2）
    draw.ellipse(
        [(width - diameter) // 2, (height - diameter) // 2,
         (width + diameter) // 2, (height + diameter) // 2],
        fill=255
    )
    # 应用遮罩，生成圆形图片
    result = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    result.paste(image, mask=mask)
    # 裁剪掉透明边缘（可选，得到仅圆形的图片）
    bbox = result.getbbox()
    if bbox:
        image = result.crop(bbox)
    return image
# paste img to gif
def make_up_gif(gif_frames, img, img_1, positions, positions_1):
    if len(positions)!=len(gif_frames) or len(positions_1)!=len(gif_frames):
        log(f"position len({len(positions)}) or position_1 len({len(positions_1)}) is not fit to gif_frame len({len(gif_frames)})")
        return None
    new_frames = []
    for i in range(0,len(gif_frames)):
        frame = gif_frames[i]
        # 转换帧为RGBA，避免透明通道丢失
        frame = frame.convert("RGBA")
        # 粘贴头像到指定位置（mask保留头像透明）
        frame.paste(img, positions[i], mask=img)
        frame.paste(img_1, positions_1[i], mask=img_1)
        # 转回RGB（GIF不支持全通道RGBA，避免报错）
        frame = frame.convert("RGB")
        new_frames.append(frame)
    return new_frames
#获取目标图片
def get_img_from_msg(message, size_limit=5000000):
    reply_id, imageName, url = None, None, None
    #查找图片消息和回复消息
    log("正在查找消息")
    messages = message.message
    for ms in messages:
        log(f"正在检查消息: {ms.__dict__}")
        if ms.type == "reply":
            reply_id = ms.data.id
        if ms.type == "image":
            log(f"图片size: {ms.data.file_size}")
            if int(ms.data.file_size) >= size_limit:
                log("图片过大，无法处理")
                msg = MessageChain(["\n图片过大，无法处理"])
                feedback(message, msg)
                continue
            imageName = ms.data.file
            url = ms.data.url
            break
        if ms.type == "mface":
            imageName = ms.data.summary
            url = ms.data.url
            break
    return reply_id, imageName, url
#获取目标图片（包括回复消息中的图片）
def get_img(bot, message, size_limit=5000000):
    reply_id, imageName, url = get_img_from_msg(message, size_limit)
    if reply_id == None and url == None:
        log(f"未找到回复消息")
        msg = MessageChain(["\n图片识别失败(可能是接口问题，可以重发一下图片)"])
        feedback(message, msg)
        return None, None
    #如果未找到图片消息但找到了回复消息，则获取回复消息中的图片
    if url == None and imageName == None:
        try:
            reply_msg = bot.get_msg(reply_id)
            reply_msg = reply_msg.data
            log(f"{reply_msg.raw_data}")
            reply_message = type("TmpMsg", (), {})()
            reply_message.message = []
            for raw_msg in reply_msg.message:
                item = type("TmpItem", (), {})()
                item.type = raw_msg.get("type")
                item.data = type("TmpData", (), {})()
                for k, v in raw_msg.get("data", {}).items():
                    setattr(item.data, k, v)
                reply_message.message.append(item)
            reply_id, imageName, url = get_img_from_msg(reply_message, size_limit)
        except Exception as e:
            log(f"获取回复消息失败: {e}")
            log(f"{traceback.format_exc()}")
    if imageName == None or url == None:
        log(f"未找到图片消息")
        return None, None
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
        return None, None
    if image == None:
        log(f"打开图片失败")
        return None, None
    return image, url
#gif -> frame_list and duration_list
def get_img_frame(gif_path):
    gif_frames, gif_durations = [], []
    reader = imageio.get_reader(gif_path)
    for frame in reader:
        img = Image.fromarray(frame).convert("RGBA")
        background = Image.new("RGBA", img.size, (0, 0, 0, 0))
        composed = Image.alpha_composite(background, img)
        gif_frames.append(composed)
        try:
            gif_durations.append(reader.get_meta_data()['duration'])
        except: pass
    if len(gif_frames) <= 1: return False, gif_frames, None
    return True, gif_frames, gif_durations
#储存GIF图
def save_gif(frames, durations, output_path, del_back=False):
    if not frames or not durations: return
    if del_back: #强制去除(目前没有触发这段)
        frames[-1].save(
            output_path,
            save_all=True,
            disposal=2,  # 帧刷新方式，避免残影
            append_images=frames[1:],
            duration=durations,
            loop=0,  # 0表示无限循环
            transparency=0,  # 设置透明色索引为0
            optimize=False  # 禁用优化，保留所有帧的完整信息
        )
    else: #自动去背(还原原图)
        frames[-1].save(
            output_path,
            save_all=True,
            disposal=2,  # 帧刷新方式，避免残影
            append_images=frames[1:],
            duration=durations,
            loop=0,  # 0表示无限循环
            optimize=False  # 禁用优化，保留所有帧的完整信息
        )
#取得方向参数
def get_command_direction(command):
    target_l, target_h = None, None
    if len(command) > 0:
        if command[0] == "左":
            target_l = "left"
        elif command[0] == "右":
            target_l = "right"
        elif command[0] == "上":
            target_h = "up"
        elif command[0] == "下":
            target_h = "down"
    if not target_l and not target_h: target_l = "left"
    return target_l, target_h
#处理变速 frames, durations -> [handler] -> frames, durations
def change_speed_frame(frame, duration, speed):
    # 变速
    temp = []
    temp_durations = []
    need_counter = 0
    need = True
    cuted = False
    for i in range(len(frame)):
        if need: # 如果该帧需要
            need_counter = 0
            # 转换帧为RGBA，避免透明通道丢失
            temp.append(frame[i])
            # 如果帧时长过短
            # 下帧按倍速被抽取
            if duration[i] // speed < 20:
                temp_durations.append(20)
                try:
                    if duration[i+1] // speed < 20:
                        need = False
                except IndexError:
                    pass
            # 否则正常变速
            else: temp_durations.append(int(duration[i] // speed))
        else: # 如果该帧不需要
            cuted = True
            # 按倍速抽帧
            need_counter += 1
            # 最后一帧保留
            if need_counter >= (speed-1) or i == len(frame)-1:
                need = True
                continue
            if duration[i+1] // speed > 20:
                need = True
    return temp, temp_durations, cuted
