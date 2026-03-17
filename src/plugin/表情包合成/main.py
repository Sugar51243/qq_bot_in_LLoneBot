
# == 图片合成插件文件 ==

#此文件为OneBot11-小生物的Tsugu插件涵数文件
#应用环境为LL-Bot v2.4.4

#如果不清楚具体作用，除配置外，请不要修改任何参数代码


#引用库
#  ==> pip自动下载缺失的库
# type: ignore
import os, re, traceback, imageio, requests
from src.importer import import_package
from src.loger import log
from src.plugin.功能注册器.main import get_places_id, help
from src.tools.image_cuter import split_image
from src.tools.reply_message import feedback
from io import BytesIO
exec(import_package("reloading", package_from= "reloading", package_pip_Name= "reloading"))
exec(import_package(
    "MessageChain, ImageMessage, RecordMessage, AtMessage, EmojiMessage, ReplyMessage", 
    package_from= "OneBotConnecter.MessageType", 
    package_pip_Name= "OneBotConnecter")
)
exec(import_package("Image, ImageDraw, ImageSequence", package_from= "PIL", package_pip_Name= "pillow"))
exec(import_package("numpy", name_as="np"))
exec(import_package("load_config", name_as="load", package_from= "Config_reader", package_pip_Name= "Python-json-config-reader"))

# 昵称
nickName_path = "data/plugin/gifcreater/image_user_nickName.json"
img_output_path = "data/plugin/gifcreater/output"
bit_path = ""
fuck_path = ""


@reloading
async def onMessage(bot, message, raw_message, be_at, msgType):
    if msgType not in ["Group_message", "Private_message"]:
        return
    if msgType == "Group_message":
        # 抽
        if raw_message[0] in ["抽"]:
            log(f"图片合成 - 抽", needPrint=(bot.testMode))
            sender = message["sender"]["user_id"]
            #获取头像
            [avatar_path, avatar_path_1] = image_get_target(bot, message, raw_message, be_at)
            if [avatar_path, avatar_path_1] == [None, None]: return
            global bit_path
            bit_path = f"file://{bot.localtion}/data/plugin/gifcreater/bit.gif"
            outputGIF = f"{img_output_path}/bit/{sender}_bit.gif"
            #合成
            try:
                await bit(
                    user_1 = avatar_path,
                    user_2 = avatar_path_1,
                    output_path = outputGIF
                    )
                msg = ImageMessage(f"file://{bot.localtion}/{outputGIF}")
                callback = await bot.send_group_msg(message["group_id"],msg)
                log(f"{callback}", needPrint=(bot.testMode))
            except Exception as e: 
                tb = e.__traceback__
                formatted_tb = ''.join(traceback.format_tb(tb))
                log(formatted_tb)
        # 撅
        elif raw_message[0] in ["撅", "艹"]:
            log(f"图片合成 - 撅", needPrint=(bot.testMode))
            sender = message["sender"]["user_id"]
            #获取头像
            [avatar_path, avatar_path_1] = image_get_target(bot, message, raw_message, be_at)
            if [avatar_path, avatar_path_1] == [None, None]: return
            global fuck_path
            fuck_path = f"file://{bot.localtion}/data/plugin/gifcreater/fuc.gif"
            outputGIF = f"{img_output_path}/fuck/{sender}_fuc.gif"
            #合成
            try:
                await fuck(
                    user_1 = avatar_path,
                    user_2 = avatar_path_1,
                    output_path = outputGIF)
                msg = ImageMessage(f"file://{bot.localtion}/{outputGIF}")
                callback = await bot.send_group_msg(message["group_id"],msg)
                log(f"{callback}", needPrint=(bot.testMode))
            except Exception as e: 
                tb = e.__traceback__
                formatted_tb = ''.join(traceback.format_tb(tb))
                log(formatted_tb)
    #镜像
    if  "镜像" in raw_message:
        log(f"图片合成 - 镜像", needPrint=(bot.testMode))
        await mirror(bot, message, raw_message)
    #变速
    elif "渐变速" in raw_message:
        log(f"图片合成 - 渐变速", needPrint=(bot.testMode))
        await change_speed_gradient(bot, message, raw_message)
    elif "变速" in raw_message:
        log(f"图片合成 - 变速", needPrint=(bot.testMode))
        await change_speed(bot, message, raw_message)
    #help
    elif raw_message == "表情包合成":
        places_id = get_places_id(message)
        await help(bot, message, "表情包合成", places_id)
#抽
async def bit(user_1, user_2, output_path):
    avatar_path = user_1
    avatar_path_1 = user_2
    gif_path = bit_path
    # 读取原GIF的所有帧和时长
    isGIF, gif_frames, gif_durations = await get_img_frame(gif_path)
    # 获取图片二进制数据
    try:
        avatar, avatar_1 = await get_target_img(avatar_path, avatar_path_1, 22, 22)
    except Exception as e:
        tb = e.__traceback__
        formatted_tb = ''.join(traceback.format_tb(tb))
        log(formatted_tb)
        return
    # 头像图片 -> 圆形头像
    avatar = image_to_c(avatar)
    avatar_1 = image_to_c(avatar_1)
    # 逐帧替换头像
    new_frames = []
    positions = [(84, 25), (87, 24), (87, 28), (86, 28), (62, 26), (59, 28), (76, 20), (85, 25), (80, 23)]
    positions_1 = [(12, 69), (15, 66), (14, 67), (15, 66), (17, 67), (14, 63), (21, 56), (15, 62), (17, 69)]
    new_frames = make_up_gif(gif_frames, avatar, avatar_1, positions, positions_1)
    # 保存新GIF
    save_gif(new_frames, output_path, gif_durations)
#撅
async def fuck(user_1, user_2, output_path):
    avatar_path = user_1
    avatar_path_1 = user_2
    gif_path = fuck_path
    # 读取原GIF的所有帧和时长
    isGIF, gif_frames, gif_durations = await get_img_frame(gif_path)
    # 获取图片二进制数据
    try:
        avatar, avatar_1 = await get_target_img(avatar_path, avatar_path_1, 120, 120)
    except Exception as e:
        tb = e.__traceback__
        formatted_tb = ''.join(traceback.format_tb(tb))
        log(formatted_tb)
        return
    # 头像图片 -> 圆形头像
    avatar = image_to_c(avatar)
    avatar_1 = image_to_c(avatar_1)
    avatar = avatar.rotate(30, expand=True)
    avatar_1 = avatar_1.rotate(100, expand=True)
    # 逐帧替换头像
    positions = [(95, -30), (90, -15), (110, -30)]
    positions_1 = [(-10, 165), (0, 160), (-10, 140)]
    new_frames = new_frames = make_up_gif(gif_frames, avatar, avatar_1, positions, positions_1)
    # 保存新GIF
    save_gif(new_frames, output_path, gif_durations)

#镜像
async def mirror(bot, message, raw_message):
    command = raw_message[raw_message.find("镜像")+2:].strip()
    target_l, target_h = get_command_direction(command)
    if not target_l and not target_h: target_l = "left"
    reply_id, user_id = None, None
    imageName, url = None, None
    messages = message["message"]
    log("正在查找回复消息", needPrint=(bot.testMode))
    #查找图片消息、回复消息和艾特消息
    for ms in messages:
        log(f"正在检查消息: {ms}", needPrint=(bot.testMode))
        if ms["type"] == "reply":
            reply_id = ms["data"]["id"]
            break
        elif ms["type"] == "at":
            user_id = ms["data"]["qq"]
            break
        elif ms["type"] == "image":
            log(f"图片size: {ms["data"]["file_size"]}", needPrint=(bot.testMode))
            if int(ms["data"]["file_size"]) >= 5000000:
                log("图片过大，无法处理", needPrint=(bot.testMode))
                msg = MessageChain(["\n图片过大，无法处理"])
                await feedback(bot, message, msg)
                continue
            imageName = ms["data"]["file"]
            url = ms["data"]["url"]
            break
    if not reply_id and not user_id and not imageName: 
        log("未找到回复消息、艾特用户或图片消息", needPrint=(bot.testMode))
    if not url and not imageName:
        try:
            reply_msg = await bot.get_msg(reply_id)
            log(f"{reply_msg}", needPrint=(bot.testMode))
            messages = reply_msg["data"]["message"]
            for ms in messages:
                log(f"正在检查消息: {ms}", needPrint=(bot.testMode))
                if ms["type"] == "image":
                    log(f"图片size: {ms["data"]["file_size"]}", needPrint=(bot.testMode))
                    if int(ms["data"]["file_size"]) >= 5000000:
                        log("图片过大，无法处理", needPrint=(bot.testMode))
                        msg = MessageChain(["\n图片过大，无法处理"])
                        await feedback(bot, message, msg)
                        continue
                    imageName = ms["data"]["file"]
                    url = ms["data"]["url"]
                    break
        except Exception as e:
            pass
    if user_id != None:
        imageName = f"{user_id}.jpg"
        url = f"https://q1.qlogo.cn/g?b=qq&nk={imageName}&s=640"
    if not imageName or not url:
        imageName = f"{reply_msg["data"]["sender"]["user_id"]}.jpg"
        url = f"https://q1.qlogo.cn/g?b=qq&nk={reply_msg["data"]["sender"]["user_id"]}&s=640"
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
        log(formatted_tb)
        return
    if not image:
        log("打开图片失败", needPrint=(bot.testMode))
        return
    isGIF, image, gif_durations = await get_img_frame(url)
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
    if not isGIF:
        output_path = f"{img_output_path}/mirror/{message['sender']['user_id']}_mirror.gif"
        save_gif(image, gif_durations, output_path)
    else:
        output_path = f"{img_output_path}/mirror/{message['sender']['user_id']}_mirror.png"
        image[0].save(output_path)
    msg = ImageMessage(f"file://{bot.localtion}/{output_path}")
    callback = await bot.reply_to_message(message,msg)
    log(f"{callback}", needPrint=(bot.testMode))
#变速
async def change_speed(bot, message, raw_message):
    command = raw_message[raw_message.find("变速")+2:].strip()
    # 解析命令参数
    if len(command)>0:
        if command[0].lower() in ["x", "×"]: 
            command = command[1:].strip()
    try: speed = float(command)
    except: speed = 2.0
    log(f"变速倍数: {speed}", needPrint=(bot.testMode))
    # 获取目标图片URL
    image, url = await get_img(bot, message)
    # 变速处理
    #读取GIF的所有帧和时长
    isGIF, image, gif_durations = get_img_frame(url)
    if not image or not gif_durations:
        log(f"读取GIF帧失败", needPrint=(bot.testMode))
        return
    if not isGIF:
        log(f"该图片不是GIF", needPrint=(bot.testMode))
        return
    # 变速
    temp = []
    temp_durations = []
    need_counter = 0
    need = True
    cuted = False
    for i in range(len(image)):
        # 如果该帧需要
        if need:
            need_counter = 0
            # 转换帧为RGBA，避免透明通道丢失
            temp.append(image[i])
            # 如果帧时长过短
            # 下帧可按变速被抽取
            if gif_durations[i] // speed < 20:
                temp_durations.append(20)
                try:
                    if gif_durations[i+1] // speed < 20:
                        need = False
                except IndexError:
                    pass
            # 否则正常变速
            else:
                temp_durations.append(int(gif_durations[i] // speed))
        # 如果该帧不需要
        else:
            cuted = True
            # 按倍速抽帧
            need_counter += 1
            # 最后一帧保留
            if need_counter >= (speed-1) or i == len(image)-1:
                need = True
                continue
            if gif_durations[i+1] // speed > 20:
                need = True
    # 保存新GIF
    image = temp
    gif_durations = temp_durations
    output_path = f"{img_output_path}/speed/{message['sender']['user_id']}_mirror.gif"
    save_gif(image, gif_durations, output_path)
    msg = MessageChain([])
    if cuted: msg.add("\n该图速度过快")
    msg.add(ImageMessage(f"file://{bot.localtion}/{output_path}"))
    callback = await bot.reply_to_message(message,msg)
    log(f"{callback}", needPrint=(bot.testMode))
#渐变速
async def change_speed_gradient(bot, message, raw_message):
    speed = 1.5
    # 获取目标图片URL
    image, url = await get_img(bot, message, size_limit=3000000)
    # 变速处理
    #读取GIF的所有帧和时长
    isGIF, image, gif_durations = get_img_frame(url)
    if not image or not gif_durations:
        log(f"读取GIF帧失败", needPrint=(bot.testMode))
        return
    if not isGIF:
        log(f"该图片不是GIF", needPrint=(bot.testMode))
        return
    # 变速
    temp, temp_durations = [], []
    changed_temp, changed_temp_durations = [image], [gif_durations]
    need_counter = 0
    need = True
    while len(image) > 2:
        temp_1 = []
        temp_durations_1 = []
        for i in range(len(image)):
            # 如果该帧需要
            if need:
                need_counter = 0
                # 转换帧为RGBA，避免透明通道丢失
                temp_1.append(image[i])
                # 如果帧时长过短
                # 下帧可按变速被抽取
                if gif_durations[i] // speed < 20:
                    temp_durations_1.append(20)
                    try:
                        if gif_durations[i+1] // speed < 20:
                            need = False
                    except IndexError:
                        pass
                # 否则正常变速
                else:
                    temp_durations_1.append(int(gif_durations[i] // speed))
            # 如果该帧不需要
            else:
                cuted = True
                # 按倍速抽帧
                need_counter += 1
                # 最后一帧保留
                if need_counter >= (speed-1) or i == len(image)-1:
                    need = True
                    continue
                if gif_durations[i+1] // speed > 20:
                    need = True
        image = temp_1
        gif_durations = temp_durations_1
        temp.extend(temp_1)
        temp_durations.extend(temp_durations_1)
        changed_temp.append(temp_1)
        changed_temp_durations.append(temp_durations_1)
    while len(changed_temp) > 0:
        temp.extend(changed_temp.pop())
        temp_durations.extend(changed_temp_durations.pop())
    # 保存新GIF
    image = temp
    gif_durations = temp_durations
    output_path = f"{img_output_path}/speed/{message['sender']['user_id']}_mirror.gif"
    save_gif(image, gif_durations, output_path)
    msg = ImageMessage(f"file://{bot.localtion}/{output_path}")
    callback = await bot.reply_to_message(message,msg)
    log(f"{callback}", needPrint=(bot.testMode))


# == Tools ==
#获取头像uri
def image_get_target(bot, message, raw_message, be_at):
    #获取发送者头像 => 参数1
    sender = message["sender"]["user_id"]
    avatar_path = f"https://q1.qlogo.cn/g?b=qq&nk={sender}&s=640" #参数1
    #获取对像头像 => 参数2
    raw_message = raw_message[1:].strip()
    avatar_path_1 = None
    #昵称
    nickNameList = load(nickName_path)
    try:
        avatar_path_1 = nickNameList[raw_message.lower()]
    #其他 => 信息参数
    except:
        #小生物
        if be_at and len(raw_message)==0:
            avatar_path_1 = str(bot.botAcc)
        #@艾特
        elif "[CQ:at,qq=" in raw_message and "]" in raw_message:
            idx = raw_message.find(f"[CQ:at,qq=")
            raw_message = raw_message[idx+len("[CQ:at,qq="):]
            idx = raw_message.find(",")
            raw_message = raw_message[:idx]
            if raw_message.isdigit():
                avatar_path_1 = raw_message
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
    if str(sender) not in bot.owner:
        #小生物
        if avatar_path_1 == f"https://q1.qlogo.cn/g?b=qq&nk={bot.botAcc}&s=640":
                avatar_path, avatar_path_1 = f"https://q1.qlogo.cn/g?b=qq&nk={bot.owner[0]}&s=640", avatar_path
        #bot管理员
        else:
            for owner_id in bot.owner:
                if avatar_path_1 == f"https://q1.qlogo.cn/g?b=qq&nk={owner_id}&s=640":
                    avatar_path, avatar_path_1 = f"https://q1.qlogo.cn/g?b=qq&nk={bot.owner[0]}&s=640", avatar_path
                    break
    log(f"获取头像: [{avatar_path}, {avatar_path_1}]", needPrint=bot.testMode)
    return [avatar_path, avatar_path_1]
#获取头像图片
async def get_target_img(avatar_path, avatar_path_1=None, resize_x=None, resize_y=None):
    # 发送请求获取图片二进制数据
    response = requests.get(avatar_path, timeout=10)
    response.raise_for_status()  # 若请求失败（如404/500），抛出异常
    # 将二进制数据转为PIL可读取的数据流，再打开图片
    image_data = BytesIO(response.content)
    avatar = Image.open(image_data)
    #
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
        log(f"position len({len(positions)}) or position_1 len({len(positions_1)}) is not fit to gif_frame len({len(gif_frame)})")
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
async def get_img_from_msg(bot, messages, size_limit=5000000):
    reply_id, imageName, url = None, None, None
    #查找图片消息和回复消息
    log("正在查找消息", needPrint=(bot.testMode))
    for ms in messages:
        log(f"正在检查消息: {ms}", needPrint=(bot.testMode))
        if ms["type"] == "reply":
            reply_id = ms["data"]["id"]
            break
        if ms["type"] == "image":
            log(f"图片size: {ms["data"]["file_size"]}", needPrint=(bot.testMode))
            if int(ms["data"]["file_size"]) >= size_limit:
                log("图片过大，无法处理", needPrint=(bot.testMode))
                msg = MessageChain(["\n图片过大，无法处理"])
                await feedback(bot, message, msg)
                continue
            imageName = ms["data"]["file"]
            url = ms["data"]["url"]
            break
    return reply_id, imageName, url
#获取目标图片（包括回复消息中的图片）
async def get_img(bot, message, size_limit=5000000):
    messages = message["message"]
    reply_id, imageName, url = await get_img_from_msg(bot, messages, size_limit)
    if reply_id == None and url == None: 
        log(f"未找到回复消息", needPrint=(bot.testMode))
        return
    #如果未找到图片消息但找到了回复消息，则获取回复消息中的图片
    if url == None and imageName == None:
        try:
            reply_msg = await bot.get_msg(reply_id)
            reply_msg = reply_msg["data"]["message"]
            log(f"{reply_msg}", needPrint=(bot.testMode))
            reply_id, imageName, url = await get_img_from_msg(bot, reply_msg, size_limit)
        except Exception as e:
            log(f"获取回复消息失败: {e}", needPrint=(bot.testMode))
            log(f"{traceback.format_exc()}", needPrint=(bot.testMode))
    if imageName == None or url == None:
        log(f"未找到图片消息", needPrint=(bot.testMode))
        return
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
        log(formatted_tb)
        return
    if image == None:
        log(f"打开图片失败", needPrint=(bot.testMode))
        return
    return image, url
#gif -> frame_list and duration_list
@reloading
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
    if len(gif_frames) == 0: return False, gif_frames, None
    return True, gif_frames, gif_durations
#
@reloading
def save_gif(frames, durations, output_path, del_back=False):
    if del_back:
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
    else:
        frames[-1].save(
            output_path,
            save_all=True,
            disposal=2,  # 帧刷新方式，避免残影
            append_images=frames[1:],
            duration=durations,
            loop=0  # 0表示无限循环
        )
#
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
