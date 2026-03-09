


# type: ignore
import os, traceback, random
from src.importer import import_package
exec(import_package("requests"))
exec(import_package("BytesIO", package_from= "io", package_pip_Name="io"))
exec(import_package("Image, ImageDraw", package_from= "PIL", package_pip_Name= "pillow"))

#图片切割函数
async def split_image(image_path = None, image_data = None, image_uri = None, num = 0, cut_left = False, vertical_segment = None, piece = 4):
    if image_path is not None:
        # 打开原始图片
        img = Image.open(image_path)
    elif image_uri is not None:
        response = None
        # 发送请求获取图片二进制数据
        response = requests.get(image_uri, timeout=10)
        response.raise_for_status()  # 若请求失败（如404/500），抛出异常
        # 将二进制数据转为PIL可读取的数据流，再打开图片
        img = BytesIO(response.content)
        img = Image.open(img)
    else: img = image_data
    width, height = img.size
    image_list = []

    # 1. 删除最左侧一栏（封面）：裁剪掉左侧一列区域，这里假设左侧栏宽度为图片宽度的1/总列数，也可手动指定宽度
    # 若知道左侧栏具体像素宽度，直接替换crop的第一个参数即可，例如left_crop_width = 80
    if cut_left:
        if num == 0:
            left_crop_width = 250  # 按比例估算左侧栏宽度，可根据实际图片调整
        else:
            left_crop_width = 250 + (735/2)  # 按比例估算左侧栏宽度，可根据实际图片调整
        img_cropped = img.crop((left_crop_width, 0, width, height))  # 裁剪左侧栏后的新图
    else: img_cropped = img

    if num > 0:
        # img_cropped.show()
        crop_w, crop_h = img_cropped.size

        # 2. 纵向分为4段：计算每段的宽度
        if vertical_segment == None:
            vertical_segment = int(crop_w / piece)

        row_height = int(crop_h / piece)

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
                sub_img = img_cropped.crop((v_left, h_top, v_right, h_bottom))
                image_list.append(sub_img)
                h += 1
        temp = []
        for i in range(num):
            try:
                idx = random.randint(0, len(image_list)-1)
                img = image_list.pop(idx)
                temp.append(img)
            except IndexError:
                break
        image_list = temp
    else:
        image_list.append(img_cropped)
    return image_list