
# == 通用类插件库 ==

#此文件为OneBot11-小生物的通用类涵数插件文件
#应用环境为LL-Bot v2.4.4

#如果不清楚具体作用，除配置外，请不要修改任何参数代码


#引用库
#  ==> pip自动下载缺失的库
import os
try: #OneBotConnecter
    from OneBotConnecter.MessageType import MessageChain, ImageMessage, RecordMessage, AtMessage, EmojiMessage, ReplyMessage
except:
    os.system("pip install OneBotConnecter")
    exec("from OneBotConnecter.MessageType import MessageChain, ImageMessage, RecordMessage, AtMessage")
lib_list = ["random", "re", "traceback", "imageio", "requests", "time"]
for lib in lib_list:
    try:
        exec(f"import {lib}")
    except:
        os.system(f"pip install {lib}")
        exec(f"import {lib}")
try: #datetime
    from datetime import date
except:
    os.system(f"pip install datetime")
    exec(f"from datetime import date")
try: #config_io
    from config_io import Config
except:
    os.system(f"pip install config-io")
    exec(f"from config_io import Config")
try: #Config_reader
    from Config_reader import load_config as load
except:
    os.system("pip install Python-json-config-reader")
    exec("from Config_reader import load_config as load, dump_config as dump")
try: #io
    from io import BytesIO
except:
    os.system(f"pip install io")
    exec(f"from io import BytesIO")
try: #PIL
    from PIL import Image, ImageDraw
except:
    os.system(f"pip install pillow")
    exec(f"from PIL import Image, ImageDraw")
try: #numpy
    import numpy as np
except:
    os.system(f"pip install numpy")
    exec(f"import numpy as np")
from src.loger import log
#信息参数
guess_users = {} #猜群友
last_message = {} #复读


# == 涵数 ==

#主涵数
async def generalMode(bot, message, raw_message, be_at):

    # == 复读 ==
    group_id = str(message["group_id"]) #预制参数
    #计算发言次数
    #相同 => 计算物 + 1
    try:
        if raw_message == last_message[group_id]["raw_message"]:
            last_message[group_id]["counter"] += 1
        else: raise Exception()
    #不同 => 更新记录
    except: 
        data = {
            "raw_message": raw_message,
            "counter": 1,
            "repeated": False
        }
        last_message[group_id] = data
    #复读
    if last_message[group_id]["counter"] == 3 and not last_message[group_id]["repeated"]:
        #更新复读状态
        last_message[group_id]["repeated"] = True
        log("内容已达3次，复读", needPrint=(bot.testMode))
        msg = MessageChain([])
        send = True
        #填充内容
        for p in message["message"]:
            if p["type"] == "at": msg.add(AtMessage(p["data"]["qq"]))
            elif p["type"] == "text": msg.add(p["data"]["text"])
            elif p["type"] == "face": msg.add(EmojiMessage(p["data"]["id"]))
            elif p["type"] == "reply": msg.add(ReplyMessage(p["data"]["id"]))
            else: send = False #未定义内容则不复读
        #复读
        if send: 
            log(f"复读内容: [{msg.data}]", needPrint=(bot.testMode))
            callback = await bot.send_group_msg(group_id,msg)
            log(f"{callback}", needPrint=(bot.testMode))

    # == 猜群友 ==
    #猜群友 - 回答
    if str(message["group_id"]) in list(guess_users.keys()):
        await answer_guess_user(bot, message)
    #猜群友
    if raw_message in ["猜头像", "猜群友"]:
        await guess_user(bot, message)
        
    # == 权限系统 ==
    #注册功能
    if raw_message[:4] == "注册权限" or raw_message[:2] == "注册":
        await registrate(bot, message, raw_message)
        return
    #查询
    if raw_message[:2] == "查询":
        await functionCheck(bot, message, raw_message)
        return
    #功能列表
    if raw_message[:4] == "功能列表" or raw_message[:2] == "权限列表":
        #从文件中获取权限内容
        permissions = Config.load_from_file("data/permissions.yaml")
        permissions = permissions[str(message["group_id"])]
        log(f"已获取群[{message["group_id"]}]权限: {permissions}", needPrint=(bot.testMode))
        #信息构造
        msg = MessageChain(["\n功能列表如下: "])
        n = 1
        for permission in permissions:
            msg.add(MessageChain([f"\n{n}. {permission}"]))
            n+=1
        msg.add(MessageChain([f"\n查询对应功能指令请用\n'查询 对应功能名称'"]))
        msg.add(MessageChain([f"\n注册新功能权限请用\n'注册 对应功能名称'"]))
        msg.add(MessageChain([f"\n删除对应功能权限请用\n'停用 对应功能名称'"]))
        #发送
        callback = await bot.reply_to_message(message, msg)
        log(f"{callback}", needPrint=(bot.testMode))
        return
    #删除权限  
    if (raw_message[:4] == "删除权限" or raw_message[:2] == "停用") and be_at:
        await deletePermission(bot, message, raw_message)
        return
    #退群
    if raw_message == "退群" and be_at:
        #返馈
        callback = await bot.send_group_msg(message["group_id"],MessageChain(["bye~"]))
        log(f"{callback}", needPrint=(bot.testMode))
        #退群
        callback = await bot.set_group_leave(message["group_id"])
        log(f"{callback}", needPrint=(bot.testMode))
        return

    # == 图片合成 ==
    #镜像
    if  "镜像" in raw_message:
        log(f"图片合成 - 镜像", needPrint=(bot.testMode))
        await mirror(bot, message, raw_message)
        return
    #变速
    if "变速" in raw_message:
        log(f"图片合成 - 变速", needPrint=(bot.testMode))
        await change_speed(bot, message, raw_message)
        return
    # 抽
    if raw_message[0] == "抽":
        log(f"图片合成 - 抽", needPrint=(bot.testMode))
        sender = message["sender"]["user_id"]
        #获取头像
        [avatar_path, avatar_path_1] = image_get_target(bot, message, raw_message, be_at)
        if [avatar_path, avatar_path_1] == [None, None]: return
        #合成
        try:
            gif_path = f"file://{bot.localtion}/data/image/botStatus/bit.gif"
            outputGIF = f"data/image/bit/{sender}_bit.gif"
            bit(
                gif_path = gif_path,
                atk = avatar_path,
                output_path = outputGIF,
                defer = avatar_path_1)
            msg = ImageMessage(f"file://{bot.localtion}/{outputGIF}")
            callback = await bot.send_group_msg(message["group_id"],msg)
            log(f"{callback}", needPrint=(bot.testMode))
        except Exception as e: 
            tb = e.__traceback__
            formatted_tb = ''.join(traceback.format_tb(tb))
            log(formatted_tb)
        return
    # 撅
    if (raw_message[0] == "撅" or raw_message[0] == "艹"):
        log(f"图片合成 - 撅", needPrint=(bot.testMode))
        sender = message["sender"]["user_id"]
        #获取头像
        [avatar_path, avatar_path_1] = image_get_target(bot, message, raw_message, be_at)
        if [avatar_path, avatar_path_1] == [None, None]: return
        #合成
        try:
            gif_path = f"file://{bot.localtion}/data/image/botStatus/fuc.gif"
            outputGIF = f"data/image/fuc/{sender}_fuc.gif"
            fuck(
                gif_path = gif_path,
                atk = avatar_path,
                output_path = outputGIF,
                defer = avatar_path_1)
            msg = ImageMessage(f"file://{bot.localtion}/{outputGIF}")
            callback = await bot.send_group_msg(message["group_id"],msg)
            log(f"{callback}", needPrint=(bot.testMode))
        except Exception as e: 
            tb = e.__traceback__
            formatted_tb = ''.join(traceback.format_tb(tb))
            log(formatted_tb)
        return
    
    # == 互动 ==
    #发癫文案
    if (raw_message.lower() == "fd" or "发癫" in raw_message) and be_at:
        await fd(bot, message, raw_message)
        return
    #赞我
    if "赞我" in raw_message:
        callback = await bot.send_like(message["sender"]["user_id"], 1)
        log(f"{callback}", needPrint=(bot.testMode))
        callback = await bot.group_poke(message["group_id"], message["sender"]["user_id"])
        log(f"{callback}", needPrint=(bot.testMode))
        msg = MessageChain([" 赞了"])
        callback = await bot.reply_to_message(message, msg)
        log(f"{callback}", needPrint=(bot.testMode))
        return
    #戳我
    if "戳我" in raw_message:
        callback = await bot.group_poke(message["group_id"], message["sender"]["user_id"])
        log(f"{callback}", needPrint=(bot.testMode))
        return
    #唱歌
    if raw_message == "唱歌" and be_at:
        await sound(bot, message, raw_message)
        return
    #大东北
    if '大东北' in raw_message:
        await sound(bot, message, raw_message, "大东北.mp3")
        return
    #忠诚
    if "忠诚" in raw_message:
        await sound(bot, message, raw_message, "你若三冬.mp3")
        return
    #糖笑
    if "糖笑" in raw_message and be_at:
        await sound(bot, message, raw_message, "糖笑.mp3")
        return
    #糖哭
    if "糖哭" in raw_message and be_at:
        await sound(bot, message, raw_message, "爱音唐哭.mp3")
        return
    #牢大
    keyword = ["牢大", "man", "see you again"]
    for words in keyword:
        if words in raw_message and be_at:
            await sound(bot, message, raw_message, "see_you_again.mp3")
            return
    #复读
    if (raw_message[0] == "说" and be_at):
        await echo(bot, message, raw_message)
        return
    #告白
    if (raw_message == "我喜欢你" or raw_message == "喜欢") and be_at:
        if str(message["sender"]["user_id"]) not in bot.owner:
            msg = MessageChain(["唉，癔症..."])
        else:
            msg = MessageChain(["我也最喜欢你了"])
        callback = await bot.reply_to_message(message, msg)
        log(f"{callback}", needPrint=(bot.testMode))
        return
    
    # == 实用指令 ==
    #随机数
    if raw_message[:3].lower() == ".rd":
        try:
            await randNumber(bot, message, raw_message)
        except Exception as e:
            tb = e.__traceback__
            formatted_tb = ''.join(traceback.format_tb(tb))
            log(formatted_tb)
        return
    
    # == 今日老婆 ==
    #今日老婆
    if raw_message in ["jrlp", "今日老婆"]:
        await jrlp(bot, message, raw_message)
        return
    #美图
    if ("来点" in raw_message and "图" in raw_message and be_at) or ("ldt" in raw_message and be_at):
        await randomImage(bot, message, raw_message)
        return
    
    # == 积分系统 ==
    #排名
    if raw_message[0:2] == "排名":
        num = 10
        if raw_message[2:].strip().isdigit():
            num = int(raw_message[2:].strip())
        await get_guess_ranking(bot, message, num = num)
        return
    #查分
    if raw_message[0:2] == "查分":
        await checkScores(bot, message)
        return
    #笨蛋机
    if raw_message[0:1] in ["土", "赌"]:
        num = 10
        if raw_message[1:].strip().isdigit():
            if int(raw_message[1:].strip()) >= 10:
                num = int(raw_message[1:].strip())
            else:
                msg = MessageChain(["最低投注积分为10分 "])
                callback = await bot.reply_to_message(message, msg)
                log(f"{callback}", needPrint=(bot.testMode))
                return
        elif len(raw_message[1:]) > 0: return
        await randAddScroes(bot, message, input_score = num)
        return


# == 猜群友 ==

async def guess_user(bot, msg):
    if str(msg["group_id"]) in list(guess_users.keys()):
        message = MessageChain(["\n已有未完成的猜头像游戏，请先结束该游戏"])
        callback = await bot.reply_to_message(msg, message)
        log(f"{callback}", needPrint=(bot.testMode))
        return
    #更新群员名单
    member_list_data = await bot.get_group_member_list(group_id=msg["group_id"])
    log(f"{member_list_data}", needPrint=(bot.testMode))
    member_list: list = member_list_data['data']
    member_list = [member_list[i]['user_id'] for i in range(len(member_list)) if member_list[i]['user_id'] != msg["sender"]["user_id"]]
    #
    target_id = member_list[random.randint(0,len(member_list)-1)]
    #
    info = await bot.get_group_member_info(group_id=msg["group_id"], user_id=target_id, no_cache=True)
    log(f"{info}", needPrint=(bot.testMode))
    name = info['data']['nickname']
    card = info['data']['card']
    if not card.strip():
        card = None
    guess_users.update({str(msg["group_id"]): {"id": str(target_id), "nickName": name, "card": card}})
    #
    avatar = f"https://q1.qlogo.cn/g?b=qq&nk={target_id}&s=640"
    image_list = split_image(image_path = avatar)
    target = image_list[random.randint(0, len(image_list)-1)]
    #
    #保存图片
    imageURL: str = f"data/image/temp/guess.png"
    target.save(imageURL)
    message = MessageChain(["\n猜猜这是哪位群友？\n"])
    message.add(ImageMessage(f"file://{bot.localtion}/{imageURL}"))
    callback = await bot.reply_to_message(msg, message)
    log(f"{callback}", needPrint=(bot.testMode))

async def answer_guess_user(bot, msg):
    if str(msg["group_id"]) not in guess_users.keys():
        return
    for answer in msg["message"]:
        if answer["type"] == "at":
            answer = str(answer["data"]["qq"]).strip()
        elif answer["type"] == "text":
            answer = str(answer["data"]["text"]).strip()
        else: pass
        try:
            if answer.strip() in ["bzd", "不知道"]:
                user = guess_users.pop(str(msg["group_id"]))
                user_id = user["id"]
                nickName = user["nickName"]
                if user["card"] != None:
                    nickName = user["card"]
                message = MessageChain([f"\n正确答案为:\n{nickName}"])
                message.add(ImageMessage(f"https://q1.qlogo.cn/g?b=qq&nk={user_id}&s=640"))
                callback = await bot.reply_to_message(msg, message)
                log(f"{callback}", needPrint=(bot.testMode))
            elif answer.strip().isdigit():
                answer = str(answer.strip())
                target = str(guess_users[str(msg["group_id"])]["id"])
                if  answer == target:
                    user = guess_users.pop(str(msg["group_id"]))
                    nickName = user["nickName"]
                    if user["card"] != None:
                        nickName = user["card"]
                    message = MessageChain([f"\n正确! 答案为:\n{nickName}"])
                    message.add(ImageMessage(f"https://q1.qlogo.cn/g?b=qq&nk={user["id"]}&s=640"))
                    callback = await bot.reply_to_message(msg, message)
                    log(f"{callback}", needPrint=(bot.testMode))
                    await add_scroes(bot,msg, 1)
            else:
                nickName = guess_users[str(msg["group_id"])]["nickName"]
                card = guess_users[str(msg["group_id"])]["card"]
                if answer.strip() == nickName or answer.strip() == card:
                    user = guess_users.pop(str(msg["group_id"]))
                    if card != None:
                        nickName = user["card"]
                    message = MessageChain([f"\n正确! 答案为:\n{nickName}"])
                    message.add(ImageMessage(f"https://q1.qlogo.cn/g?b=qq&nk={user["id"]}&s=640"))
                    callback = await bot.reply_to_message(msg, message)
                    log(f"{callback}", needPrint=(bot.testMode))
                    await add_scroes(bot,msg, 1)
        except: pass

# == 图片合成 ==
#获取头像
def image_get_target(bot, message, raw_message, be_at):
    #获取发送者头像 => 参数1
    sender = message["sender"]["user_id"]
    avatar_path = f"https://q1.qlogo.cn/g?b=qq&nk={sender}&s=640" #参数1
    #获取对像头像 => 参数2
    raw_message = raw_message[1:].strip()
    avatar_path_1 = None
    #昵称
    nickNameList = load("data/classify/general/image_user_nickName.json")
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

def bit(gif_path, atk, output_path, defer = None):
    avatar_path = atk
    avatar_path_1 = defer
    # 读取原GIF的所有帧和时长
    gif_frames = []
    gif_durations = []
    reader = imageio.get_reader(gif_path)
    for frame in reader:
        gif_frames.append(Image.fromarray(frame))
        gif_durations.append(reader.get_meta_data()['duration'])

    # 读取并处理头像（缩放、转为RGBA支持透明）
    try:
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
    except Exception as e:
        tb = e.__traceback__
        formatted_tb = ''.join(traceback.format_tb(tb))
        log(formatted_tb)
        return
    avatar = avatar.resize((22, 22), Image.Resampling.LANCZOS)
    if avatar_path_1 != None:
        avatar_1 = avatar_1.resize((22, 22), Image.Resampling.LANCZOS)
    width, height = avatar.size
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
    result.paste(avatar, mask=mask)
    if avatar_path_1 != None:
        result_1 = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        result_1.paste(avatar_1, mask=mask)

    # 裁剪掉透明边缘（可选，得到仅圆形的图片）
    bbox = result.getbbox()
    if bbox:
        avatar = result.crop(bbox)
    if avatar_path_1 != None:
        bbox = result_1.getbbox()
        if bbox:
            avatar_1 = result_1.crop(bbox)

    # 逐帧替换头像
    new_frames = []
    positions = [(84, 25), (87, 24), (87, 28), (86, 28), (62, 26), (59, 28), (76, 20), (85, 25), (80, 23)]
    positions_1 = [(12, 69), (15, 66), (14, 67), (15, 66), (17, 67), (14, 63), (21, 56), (15, 62), (17, 69)]
    for i in range(0,len(gif_frames)):
        frame = gif_frames[i]
        # 转换帧为RGBA，避免透明通道丢失
        frame = frame.convert("RGBA")
        # 粘贴头像到指定位置（mask保留头像透明）
        frame.paste(avatar, positions[i], mask=avatar)
        if (avatar_path_1 != None):
            frame.paste(avatar_1, positions_1[i], mask=avatar_1)
        # 转回RGB（GIF不支持全通道RGBA，避免报错）
        frame = frame.convert("RGB")
        new_frames.append(frame)

    # 保存新GIF
    new_frames[0].save(
        output_path,
        save_all=True,
        append_images=new_frames[1:],
        duration=gif_durations,
        loop=0,  # 0表示无限循环
        disposal=2  # 帧刷新方式，避免残影
    )

def fuck(gif_path, atk, output_path, defer = None):
    avatar_path = atk
    avatar_path_1 = defer
    # 读取原GIF的所有帧和时长
    gif_frames = []
    gif_durations = []
    reader = imageio.get_reader(gif_path)
    for frame in reader:
        gif_frames.append(Image.fromarray(frame))
        gif_durations.append(reader.get_meta_data()['duration'])

    # 读取并处理头像（缩放、转为RGBA支持透明）
    try:
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
    except Exception as e:
        tb = e.__traceback__
        formatted_tb = ''.join(traceback.format_tb(tb))
        log(formatted_tb)
        return
    avatar = avatar.resize((120, 120), Image.Resampling.LANCZOS)
    if avatar_path_1 != None:
        avatar_1 = avatar_1.resize((120, 120), Image.Resampling.LANCZOS)
    width, height = avatar.size
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
    result = Image.new("RGBA", (120, 120), (0, 0, 0, 0))
    result.paste(avatar, mask=mask)
    if avatar_path_1 != None:
        result_1 = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        result_1.paste(avatar_1, mask=mask)

    # 裁剪掉透明边缘（可选，得到仅圆形的图片）
    bbox = result.getbbox()
    if bbox:
        avatar = result.crop(bbox)
    if avatar_path_1 != None:
        bbox = result_1.getbbox()
        if bbox:
            avatar_1 = result_1.crop(bbox)
    
    avatar = avatar.rotate(30, expand=True)
    if avatar_path_1 != None:
        avatar_1 = avatar_1.rotate(100, expand=True)

    # 逐帧替换头像
    new_frames = []
    positions = [(95, -30), (90, -15), (110, -30)]
    positions_1 = [(-10, 165), (0, 160), (-10, 140)]
    for i in range(0,len(gif_frames)):
        frame = gif_frames[i]
        # 转换帧为RGBA，避免透明通道丢失
        frame = frame.convert("RGBA")
        # 粘贴头像到指定位置（mask保留头像透明）
        frame.paste(avatar, positions[i], mask=avatar)
        if (avatar_path_1 != None):
            frame.paste(avatar_1, positions_1[i], mask=avatar_1)
        # 转回RGB（GIF不支持全通道RGBA，避免报错）
        frame = frame.convert("RGB")
        new_frames.append(frame)

    # 保存新GIF
    new_frames[0].save(
        output_path,
        save_all=True,
        append_images=new_frames[1:],
        duration=gif_durations,
        loop=0,  # 0表示无限循环
        disposal=2  # 帧刷新方式，避免残影
    )

async def mirror(bot, message, raw_message):
    command = raw_message[raw_message.find("镜像")+2:].strip()
    target_l = None
    target_h = None
    if len(command) > 0:
        if command[0] == "左":
            target_l = "left"
        elif command[0] == "右":
            target_l = "right"
        elif command[0] == "上":
            target_h = "up"
        elif command[0] == "下":
            target_h = "down"
    if target_l == None and target_h == None: target_l = "left"
    reply_id = None
    user_id = None
    messages = message["message"]
    for ms in messages:
        if ms["type"] == "reply":
            reply_id = ms["data"]["id"]
            break
        elif ms["type"] == "at":
            user_id = ms["data"]["qq"]
            break
    if reply_id == None and user_id == None: return
    imageName = None
    url = None
    try:
        reply_msg = await bot.get_msg(reply_id)
        log(f"{reply_msg}", needPrint=(bot.testMode))
        messages = reply_msg["data"]["message"]
        for ms in messages:
            if ms["type"] == "image":
                imageName = ms["data"]["file"]
                url = ms["data"]["url"]
                break
    except Exception as e:
        pass
    if user_id != None:
        imageName = f"{user_id}.jpg"
        url = f"https://q1.qlogo.cn/g?b=qq&nk={imageName}&s=640"
    if imageName == None or url == None:
        imageName = f"{reply_msg["data"]["sender"]["user_id"]}.jpg"
        url = f"https://q1.qlogo.cn/g?b=qq&nk={reply_msg["data"]["sender"]["user_id"]}&s=640"
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
        return
    temp = []
    gif_durations = []
    reader = imageio.get_reader(url)
    for frame in reader:
        temp.append(Image.fromarray(frame))
        try:
            gif_durations.append(reader.get_meta_data()['duration'])
        except: pass
        image = temp
    mask_color = 0
    for i in range(len(image)):
        im = image[i].convert("RGBA")
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
        if target_l != None:
            temp = half.transpose(Image.FLIP_LEFT_RIGHT)
        elif target_h != None:
            temp = half.transpose(Image.FLIP_TOP_BOTTOM)
        temp.paste(half, (0,0), mask=half)
        image[i] = temp
    if len(image) > 1:
        output_path = f"data/image/mirror/{message['sender']['user_id']}_mirror.gif"
        # 保存新GIF
        image[0].save(
            output_path,
            save_all=True,
            append_images=image[1:],
            duration=gif_durations,
            loop=0,  # 0表示无限循环
            disposal=2  # 帧刷新方式，避免残影
        )
    else:
        temp = image[0].transpose(Image.FLIP_LEFT_RIGHT)
        image[0] = temp
        output_path = f"data/image/mirror/{message['sender']['user_id']}_mirror.png"
        image[0].save(output_path)
    msg = ImageMessage(f"file://{bot.localtion}/{output_path}")
    callback = await bot.send_group_msg(message["group_id"],msg)
    log(f"{callback}", needPrint=(bot.testMode))

async def change_speed(bot, message, raw_message):
    command = raw_message[raw_message.find("变速")+2:].strip()
    if len(command)>0:
        if command[0].lower() == "x": 
            command = command[1:].strip()
    try: speed = float(command)
    except: speed = 2.0
    messages = message["message"]
    reply_id = None
    for ms in messages:
        if ms["type"] == "reply":
            reply_id = ms["data"]["id"]
            break
    if reply_id == None: return
    imageName = None
    url = None
    try:
        reply_msg = await bot.get_msg(reply_id)
        log(f"{reply_msg}", needPrint=(bot.testMode))
        messages = reply_msg["data"]["message"]
        for ms in messages:
            if ms["type"] == "image":
                imageName = ms["data"]["file"]
                url = ms["data"]["url"]
                break
    except Exception as e:
        pass
    if imageName == None or url == None:
        return
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
        return
    temp = []
    gif_durations = []
    reader = imageio.get_reader(url)
    if len(reader)<=1:
        return
    for frame in reader:
        temp.append(Image.fromarray(frame))
        gif_durations.append(reader.get_meta_data()['duration'])
    image = temp
    for i in range(len(image)):
        image[i] = image[i].convert("RGBA")
        img = Image.new("RGB", image[i].size, (255, 255, 255))
        img.paste(image[i], mask=image[i].split()[3])
        image[i] = img
        gif_durations[i] = gif_durations[i] // speed

    output_path = f"data/image/mirror/{message['sender']['user_id']}_mirror.gif"
    # 保存新GIF
    image[0].save(
        output_path,
        save_all=True,
        append_images=image[1:],
        duration=gif_durations,
        loop=0,  # 0表示无限循环
        disposal=2  # 帧刷新方式，避免残影
    )
    msg = ImageMessage(f"file://{bot.localtion}/{output_path}")
    callback = await bot.send_group_msg(message["group_id"],msg)
    log(f"{callback}", needPrint=(bot.testMode))

#图片切割函数
def split_image(image_path = None, image_data = None):
    if image_path is not None:
        response = None
        # 发送请求获取图片二进制数据
        response = requests.get(image_path, timeout=10)
        response.raise_for_status()  # 若请求失败（如404/500），抛出异常
        # 将二进制数据转为PIL可读取的数据流，再打开图片
        img = BytesIO(response.content)
        img = Image.open(img)
    else: img = image_data
    width, height = img.size
    image_list = []

    #img.show()
    crop_w, crop_h = img.size

    # 2. 纵向分为4段：计算每段的宽度
    vertical_segment = int(crop_w / 4)

    row_height = int(crop_h / 4)

    for v in range(int(crop_w/vertical_segment)):
        # 计算纵向裁剪的左右坐标
        v_left = v * vertical_segment
        v_right = (v + 1) * vertical_segment

        # 遍历横向每2行
        h = 0
        while h * row_height < crop_h and (crop_h - (h * row_height) >= row_height):
            # 计算横向裁剪的上下坐标
            h_top = h * row_height
            h_bottom = (h + 1) * row_height if (h + 1) * row_height < crop_h else crop_h

            # 裁剪小图
            sub_img = img.crop((v_left, h_top, v_right, h_bottom))
            image_list.append(sub_img)
            h += 1
    return image_list

# == 权限系统 ==

async def registrate(bot, msg, raw_message):
    command = raw_message.replace("注册权限","注册")[2:].strip()
    plugin_folders = os.listdir("src/classify")
    try:
        if command.lower() in plugin_folders:
            message = _registrateToFile(str(msg["group_id"]),command.lower())
        else:
            raise Exception()
    except:
        plugin_folders.remove("general")
        message = MessageChain([f"\n功能注册失败或参数错误\n"])
        message.add(MessageChain([f"可用参数:\n{plugin_folders}"]))
    callback = await bot.reply_to_message(msg, message)
    log(f"{callback}", needPrint=(bot.testMode))
    return

async def deletePermission(bot, msg, raw_message):
    command = raw_message.replace("停用","删除权限")[4:].strip()
    try:
        if command == "general":
            message = MessageChain(["通用功能权限不可删除"])
            callback = await bot.reply_to_message(msg, message)
            log(f"{callback}", needPrint=(bot.testMode))
            return
        permissions = Config.load_from_file("data/permissions.yaml")
        groupPermissions = permissions[str(msg["group_id"])]
        if command not in groupPermissions:
            message = MessageChain(["功能未注册\n输入'功能列表'查看已注册权限列表"])
            callback = await bot.reply_to_message(msg, message)
            log(f"{callback}", needPrint=(bot.testMode))
            return
        groupPermissions.remove(command)
        permissions[str(msg["group_id"])] = groupPermissions
        permissions.dump_to_file("data/permissions.yaml")
        message = MessageChain(["删除成功"])
    except:
        message = MessageChain(["\n查询后台或删除权限时出现问题，请联系管理员"])
    callback = await bot.reply_to_message(msg, message)
    log(f"{callback}", needPrint=(bot.testMode))
    return

def _registrateToFile(group_id: str, p: str):
    try:
        permissions = Config.load_from_file("data/permissions.yaml")
        groupPermissions = permissions[group_id]
        if p in groupPermissions:
            return MessageChain(["权限已存在\n请勿重复注册功能权限\n输入'功能列表'查看已注册权限列表\n使用'停用 功能名称'删除对应权限\n使用'查询 功能名称'查看功能帮助"])
        groupPermissions.append(p)
        permissions[group_id] = groupPermissions
        permissions.dump_to_file("data/permissions.yaml")
        return MessageChain(["权限注册成功\n输入'功能列表'查看已注册权限列表\n使用'停用 功能名称'删除对应权限\n使用'查询 功能名称'查看功能帮助"])
    except: return MessageChain(["查询后台或注册时出来问题，请联系管理员"])

async def functionCheck(bot, msg, raw_message):
    raw_message = raw_message[2:].strip()
    if not raw_message.strip(): raw_message="general"
    plugin_folders = os.listdir("src/classify")
    if raw_message.lower() not in plugin_folders:
        message = MessageChain(["本机器人无该功能"])
        callback = await bot.reply_to_message(msg, message)
        log(f"{callback}", needPrint=(bot.testMode))
        return
    permissions = Config.load_from_file("data/permissions.yaml")
    permissions = permissions[str(msg["group_id"])]
    if raw_message not in permissions:
        message = MessageChain(["未注册对应权限"])
        callback = await bot.reply_to_message(msg, message)
        log(f"{callback}", needPrint=(bot.testMode))
        return
    path = "data/help/"
    with open(path+f"{raw_message.lower()}.txt", 'r', encoding="utf-8") as f:
        text = f.read()
    message = MessageChain([f"\n{text}"])
    callback = await bot.reply_to_message(msg, message)
    log(f"{callback}", needPrint=(bot.testMode))

# == 互动 ==

async def fd(bot, message, raw_message):
    #彩蛋
    if random.randint(1,100)<=5:
        if random.randint(1,100)<=5:
            msg = MessageChain(["哈哈，我不发"])
            callback = await bot.reply_to_message(message, msg)
            log(f"{callback}", needPrint=(bot.testMode))
            return
    #获取文案
    adFiles = os.listdir("data/classify/general/ad")
    idx = random.randint(0,len(adFiles)-1)
    #发送
    path = "data/classify/general/ad/"+adFiles[idx]
    with open(path, 'r', encoding="utf-8") as f:
        text = f.read()
    msg = MessageChain([str(text)])
    callback = await bot.send_group_msg(message["group_id"],msg)
    log(f"{callback}", needPrint=(bot.testMode))
    return

async def randomImage(bot, message, raw_message):
        imagesList = os.listdir("data/classify/general/image")
        idx = random.randint(0,len(imagesList)-1)
        #发送
        path = f"file://{bot.localtion}/data/classify/general/image/"+imagesList[idx]
        msg = MessageChain([ImageMessage(path)])
        callback = await bot.send_group_msg(message["group_id"],msg)
        log(f"{callback}", needPrint=(bot.testMode))
        return

async def sound(bot, msg, raw_message, file=None):
    if file==None:
        soundList = os.listdir("data/classify/general/sound")
        idx = random.randint(0,len(soundList)-1)
        path = f"file://{bot.localtion}/data/classify/general/sound/"+soundList[idx]
    else:
        path = f"file://{bot.localtion}/data/classify/general/sound/"+file
    message = RecordMessage(path)
    callback = await bot.send_group_msg(msg["group_id"], message)
    log(f"{callback}", needPrint=(bot.testMode))
    return

async def echo(bot, msg, raw_message):
    text = raw_message[raw_message.find("说")+1:].strip()
    if ("妈" in text):
        message = MessageChain(["?"])
        callback = await bot.reply_to_message(msg, message)
        log(f"{callback}", needPrint=(bot.testMode))
        return
    if ("我喜欢" in text or "我爱" in text):
        if str(msg["sender"]["user_id"]) not in bot.owner:
            message = MessageChain(["唉，癔症..."])
        else:
            message = MessageChain([text])
        callback = await bot.reply_to_message(msg, message)
        log(f"{callback}", needPrint=(bot.testMode))
        return
    curse = False
    if "是" in text and "sb" in text:
        if text.find("是") < text.find("sb"): curse = True
    if "傻逼" in text or curse:
        if str(msg["sender"]["user_id"]) not in bot.owner:
            message = MessageChain(["你是傻逼"])
            callback = await bot.reply_to_message(msg, message)
            log(f"{callback}", needPrint=(bot.testMode))
        else:
            message = MessageChain([text])
            callback = await bot.send_group_msg(msg["group_id"], message)
            log(f"{callback}", needPrint=(bot.testMode))
        return
    if "咕咕嘎嘎" in text:
        path = ["gugugaga.mp3", "gugugaga1.mp3"]
        idx = random.randint(0,len(path)-1)
        await sound(bot, msg, raw_message, path[idx])
        return
    elif "灵感菇" in text:
        await sound(bot, msg, raw_message, "lingangulguli.mp3")
        return
    elif "tujitujidandandantujitujidan" in text:
        await sound(bot, msg, raw_message, "tujitujidandandantujitujidan.mp3")
        return
    elif len(text) <= 0:
        message = MessageChain(["你让我说什么？"])
        callback = await bot.reply_to_message(msg, message)
        log(f"{callback}", needPrint=(bot.testMode))
        return
    elif len(text) >= 50:
        message = MessageChain(["你说这么多我听不懂啦！"])
        callback = await bot.reply_to_message(msg, message)
        log(f"{callback}", needPrint=(bot.testMode))
        return
    else:
        texts = text.split(" ")
        message = MessageChain()
        for i in texts:
            if "[CQ:at" in i:
                target = i[i.find("qq=")+3:]
                target = target[:target.find(",")]
                message.add(AtMessage(target))
            else:
                message.add(MessageChain([i]))
            if i != texts[-1]:
                message.add(" ")
        callback = await bot.send_group_msg(msg["group_id"], message)
        log(f"{callback}", needPrint=(bot.testMode))
        return

# == 实用指令 ==

async def randNumber(bot, msg, raw_message):
        #获取参数
        command = raw_message.replace("D","d")
        command = command[3:].strip().lower().split("d")
        command = [command[0]] + re.findall(r'(\d+)', command[1])
        #次数
        times = int(command[0])
        max_num = int(command[1])
        #构造信息链并投随机数
        message = MessageChain([f""])
        success = 0
        total = 0
        for x in range(times):
            try:
                output = random.randint(1, max_num)
                total += output
                message.add(MessageChain([f"\n{x+1}. 1D{max_num}: {output}"]))
                #判定
                if len(command)>=3:
                    if max_num>int(float(command[2])):
                        message.add(MessageChain([f" ([>{int(float(command[2]))}]:{"成功" if output>int(float(command[2])) else "失败"})"]))
                        if output>int(float(command[2])): success += 1
            except:
                message = MessageChain([f"\n随机数出错"])
        message.add(MessageChain([f"\n总数为: {total}"]))
        if len(command)>=3:
            if max_num<int(float(command[2])):
                message.add(MessageChain([f" ([>{int(float(command[2]))}]:{"成功" if output>int(float(command[2])) else "失败"})"]))
                success = times
        #决定
        idx = raw_message.find("决定我")
        if idx != -1 and len(command) >= 3:
            needToDo = raw_message[idx+3:]
            if needToDo[:3] == "要不要" or needToDo[:2] == "是否": needToDo = needToDo[2:]
            message.add(MessageChain([f"\n如果让我决定你是否{needToDo}, 那答案将会是: {"做" if success>=(times/2) else "不做"}"]))
            callback = await bot.reply_to_message(msg, message)
            log(f"{callback}", needPrint=(bot.testMode))
            return
        idx = raw_message.find("决定")
        if idx != -1 and len(command) >= 2:
            needToDo = raw_message[idx+2:]
            if needToDo[:3] == "要不要" or needToDo[:2] == "是否": needToDo = needToDo[2:]
            message.add(MessageChain([f"\n如果让我决定{needToDo}, 那答案将会是: {"是" if success>=(times/2) else "否"}"]))
        callback = await bot.reply_to_message(msg, message)
        log(f"{callback}", needPrint=(bot.testMode))
        return

# == 今日老婆 ==

async def jrlp(bot, msg, raw_message):
        #获取今日日期并查询
        today = str(date.today())
        try:
            data = Config.load_from_file(path="data/classify/general/jrlp.json")
            todayData = data[today]
        except:
            todayData = Config()
        #从数据中获取该群数据记录
        try:
            groupData = todayData[str(msg["group_id"])]
        except:
            groupData = Config()
        #尝试查询该用户配对记录
        try:
            jrlp = groupData[str(msg["sender"]["user_id"])]
        except:
            member_list_data = await bot.get_group_member_list(group_id=msg["group_id"])
            log(f"{member_list_data}", needPrint=(bot.testMode))
            member_list: list = member_list_data['data']
            #更新可配对群员名单
            member_list = [member_list[i]['user_id'] for i in range(len(member_list)) if (member_list[i]['user_id'] != msg["sender"]["user_id"] and str(member_list[i]['user_id']) not in groupData)]
            #如果全员已配对 则 返回单身信息
            if len(member_list) <= 0:
                message = MessageChain(["今天你单身"])
                callback = await bot.reply_to_message(msg, message)
                log(f"{callback}", needPrint=(bot.testMode))
                return
            #开始配对
            idx = random.randint(0,len(member_list)-1)
            jrlp = member_list[idx]
            #双方同时更新目录
            groupData[str(msg["sender"]["user_id"])] = jrlp
            groupData[jrlp] = str(msg["sender"]["user_id"])
            #更新群数据记录
            todayData[str(msg["group_id"])] = groupData
            #更新当日记录
            data = Config({today:todayData})
            #储存
            data.dump_to_file('data/classify/general/jrlp.json')
        #发送
        try:
            info = await bot.get_group_member_info(group_id=msg["group_id"], user_id=jrlp, no_cache=True)
            log(f"{info}", needPrint=(bot.testMode))
            card = info['data']['card_or_nickname']
        except Exception as e: 
            tb = e.__traceback__
            formatted_tb = ''.join(traceback.format_tb(tb))
            log(formatted_tb)
            card = str(jrlp)
        avatar = f"https://q1.qlogo.cn/g?b=qq&nk={jrlp}&s=640"
        #发送
        message = MessageChain(["\n"])
        if str(jrlp) in bot.owner:
            message.add(MessageChain([f"你今天的老公是: {card}"]))
        else:
            message.add(MessageChain([f"你今天的老婆是: {card}"]))
        message.add(MessageChain([ImageMessage(avatar)]))
        callback = await bot.reply_to_message(msg,message)
        log(f"{callback}", needPrint=(bot.testMode))
        return

# == 积分系统 ==

async def get_guess_ranking(bot, msg, num = 10):
    message = MessageChain(["\n小生物总分排名:\n"])
    #读取文件
    users = Config.load_from_file("data/classify/general/guess_scores.json")
    #计算排名
    user_list = list(users.keys())
    user_list.sort(key=lambda uid: users[uid]["scores"], reverse=True)
    #输出排名
    rank = 1
    for uid in user_list:
        score = users[uid]["scores"]
        nickname = users[uid]["name"]
        message.add(MessageChain([f"{rank}. {nickname} - 总分: {int(score)} 分\n"]))
        rank += 1
        if rank > num:
            break
    callback = await bot.reply_to_message(msg, message)
    log(f"{callback}", needPrint=(bot.testMode))

async def randAddScroes(bot, msg, input_score: int = 10):
    #读取文件
    user_id = msg["sender"]["user_id"]
    if user_id is not str:
        user_id = str(user_id)
    users = Config.load_from_file("data/classify/general/guess_scores.json")
    #获取用户数据
    try:
        data = users[user_id]
    except:
        data = {"scores": 0, "chart": 0, "card": 0, "sp": 0, "name": msg["sender"]["nickname"], "cards": [], "use_card": True, "time": 0.0}
    #时间CD
    now_time = time.time()
    if (now_time - data["time"]) < 600.0:
        dif = data["time"]+600 - now_time
        message = MessageChain([f"\n每10分钟只能随机一次哦\n目前还差:{int(int(dif)/60)}分钟{int(int(dif)%60)}秒"])
        callback = await bot.reply_to_message(msg, message)
        log(f"{callback}", needPrint=(bot.testMode))
        return
    #检查积分是否足够
    if data["scores"] < input_score:
        message = MessageChain([f"你的总积分不足"])
        callback = await bot.reply_to_message(msg, message)
        log(f"{callback}", needPrint=(bot.testMode))
        users[user_id] = data
        users.dump_to_file("data/classify/general/guess_scores.json")
        return
    #随机倍率
    score = random.randint(1, 100)
    if score <= 5:
        score = 200
    elif score <= 20:
        score = 0
    elif score <= 60:
        score = random.randint(0, 100)
    else:
        score = random.randint(100, 200)
    add_score = int(input_score * (score/100))
    #输出信息
    message = MessageChain([f"\n投入积分:[{input_score}] * 随机倍率[{score/100}]\n获得随机积分: {add_score} 分"])
    callback = await bot.reply_to_message(msg, message)
    log(f"{callback}", needPrint=(bot.testMode))
    #更新数据
    data["time"] = time.time()
    data["scores"] -= input_score
    users[user_id] = data
    users.dump_to_file("data/classify/general/guess_scores.json")
    #更新积分
    await add_scroes(bot, msg, score=add_score, add_type="sp")

async def add_scroes(bot, msg, score = 0, add_type: str = "sp"):
    old_rank = -1
    user_id = msg["sender"]["user_id"]
    if user_id is not str:
        user_id = str(user_id)
    #读取文件
    users = Config.load_from_file("data/classify/general/guess_scores.json")
    try:
        data = users[user_id]
    except:
        data = {"scores": 0.0, "chart": 0, "card": 0, "sp": 0.0, "name": msg["sender"]["nickname"], "cards": [], "use_card": True, "time": 0}
    #计算排名
    try:
        user_list = list(users.keys())
        user_list.sort(key=lambda uid: users[uid]["scores"], reverse=True)
        old_rank = user_list.index(user_id)
    except: pass
    #更新数据
    if data["use_card"] and score > 0:
        card_bonus = 1
        if len(data["cards"]) > 0:
            card_bonus = 1 + data["cards"].pop(0)
        score = score * card_bonus
        if card_bonus > 1:
            message = MessageChain([f"\n使用卡牌加成 x{1+card_bonus}，本次获得积分提升至 {int(score)} 分！"])
            callback = await bot.reply_to_message(msg, message)
            log(f"{callback}", needPrint=(bot.testMode))
    data["scores"] += score
    if add_type == "sp":
        data["sp"] += score
    else:
        data[add_type] += 1
    users[user_id] = data
    #写入文件
    users.dump_to_file("data/classify/general/guess_scores.json")
    #
    if score > 0:
        message = MessageChain([f"获得积分 {int(score)} ！"])
    #计算排名
    user_list = list(users.keys())
    user_list.sort(key=lambda uid: users[uid]["scores"], reverse=True)
    rank = user_list.index(user_id)
    #输出信息
    if rank > (old_rank) or old_rank == -1:
        message = MessageChain([f"恭喜你！你的总分提升到第 {rank+1} 名！"])
        callback = await bot.reply_to_message(msg, message)
        log(f"{callback}", needPrint=(bot.testMode))

async def checkScores(bot, msg):
    user_id = msg["sender"]["user_id"]
    if user_id is not str:
        user_id = str(user_id)
    #读取文件
    users = Config.load_from_file("data/classify/general/guess_scores.json")
    try:
        data = users[user_id]
    except:
        data = {"scores": 0.0, "chart": 0, "card": 0, "sp": 0.0, "name": msg["sender"]["nickname"], "cards": [], "use_card": True, "time": 0}
    message = MessageChain([f"你的总积分为: {data["scores"]}"])
    callback = await bot.reply_to_message(msg, message)
    log(f"{callback}", needPrint=(bot.testMode))

