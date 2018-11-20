#!/usr/bin/env python
# coding: utf-8
# @Time     : 2018/10/21 19:46
# @Author   : toddlerya
# @FileName : verify_captcha.py
# @Project  : MyZoneMySeat

import sys
import requests
import pytesseract
from PIL import Image
from collections import defaultdict
# import matplotlib.pyplot as plt

# https://blog.csdn.net/gzlaiyonghao/article/details/1852726
# https://blog.csdn.net/akak714/article/details/50324505

#   -c VAR=VALUE          Set value for config variables.
#                         Multiple -c arguments are allowed.
#   -psm NUM              Specify page segmentation mode.
# NOTE: These options must occur before any configfile.
#
# Page segmentation modes:
#   0    Orientation and script detection (OSD) only.
#   1    Automatic page segmentation with OSD.
#   2    Automatic page segmentation, but no OSD, or OCR.
#   3    Fully automatic page segmentation, but no OSD. (Default)
#   4    Assume a single column of text of variable sizes.
#   5    Assume a single uniform block of vertically aligned text.
#   6    Assume a single uniform block of text.
#   7    Treat the image as a single text line.
#   8    Treat the image as a single word.
#   9    Treat the image as a single word in a circle.
#  10    Treat the image as a single character.


captcha_url = 'http://seat1.lib.hlju.edu.cn/simpleCaptcha/captcha'


# tesseract.exe所在的文件路径
# pytesseract.pytesseract.tesseract_cmd = 'C://Program Files (x86)/Tesseract-OCR/tesseract.exe'


def get_threshold(image):
    """
    获取图片中像素点数量最多的像素
    :param image:
    :return:
    """
    pixel_dict = defaultdict(int)

    # 像素及该像素出现次数的字典
    rows, cols = image.size
    for i in range(rows):
        for j in range(cols):
            pixel = image.getpixel((i, j))
            pixel_dict[pixel] += 1

    count_max = max(pixel_dict.values())  # 获取像素出现出多的次数
    pixel_dict_reverse = {v: k for k, v in pixel_dict.items()}
    threshold = pixel_dict_reverse[count_max]  # 获取出现次数最多的像素点

    return threshold


def get_bin_table(threshold):
    """
    按照阈值进行二值化处理
    threshold: 像素阈值
    :param threshold:
    :return:
    """
    # 图像的二值化处理就是讲图像上的点的灰度置为0或255，也就是讲整个图像呈现出明显的黑白效果。
    # 获取灰度转二值的映射table
    table = []
    for i in range(256):
        rate = 0.1  # 在threshold的适当范围内进行处理
        if threshold * (1 - rate) <= i <= threshold * (1 + rate):
            table.append(1)
        else:
            table.append(0)
    return table


def cut_noise(image):
    """
    去掉二值化处理后的图片中的噪声点
    :param image:
    :return:
    """
    rows, cols = image.size  # 图片的宽度和高度
    change_pos = []  # 记录噪声点位置

    # 遍历图片中的每个点，除掉边缘
    for i in range(1, rows - 1):
        for j in range(1, cols - 1):
            # pixel_set用来记录该店附近的黑色像素的数量
            pixel_set = []
            # 取该点的邻域为以该点为中心的九宫格
            for m in range(i - 1, i + 2):
                for n in range(j - 1, j + 2):
                    if image.getpixel((m, n)) != 1:  # 1为白色,0位黑色
                        pixel_set.append(image.getpixel((m, n)))

            # 如果该位置的九宫内的黑色数量小于等于4，则判断为噪声
            if len(pixel_set) <= 4:
                change_pos.append((i, j))

    # 对相应位置进行像素修改，将噪声处的像素置为1（白色）
    for pos in change_pos:
        image.putpixel(pos, 1)

    return image  # 返回修改后的图片


def rectify(_text):
    # 由于都是数字
    # 对于识别成字母的 采用该表进行修正
    rep = {
        'D': '0',
        'O': '0',
        'o': '0',
        'G': '0',
        'I': '1',
        'L': '1',
        'Z': '2',
        'S': '5'
    }
    for r in rep:
        _text = _text.replace(r, rep[r])
    return _text


def verify(img_name):
    """
   识别图片中的数字加字母
   传入参数为图片路径，返回结果为：识别结果
   :param img_name:
   :return:
   """
    image = Image.open(img_name)  # 打开图片文件
    imgry = image.convert('L')  # 转化为灰度图

    # imgry.save('grey_level.jpg')
    # plt.imshow(image)
    # plt.show()

    # 获取图片中的出现次数最多的像素，即为该图片的背景
    max_pixel = get_threshold(imgry)
    # 将图片进行二值化处理
    table = get_bin_table(threshold=max_pixel)
    out = imgry.point(table, '1')

    # out.save('bin_level.jpg')

    # 去掉图片中的噪声（孤立点）
    out = cut_noise(out)

    # 保存图片
    # out.save('cut_level.jpg')

    # 仅识别图片中的数字
    # text = pytesseract.image_to_string(out, config='digits')
    text = pytesseract.image_to_string(out, config='--psm 6  -c tessedit_char_whitelist="0123456789"')
    # 识别图片中的数字和字母
    # text = pytesseract.image_to_string(out)

    # 去掉识别结果中的特殊字符
    # exclude_char_list = ' .:\\|\'\"?![],()~@#$%^&*_+-={};<>/¥'
    # text = ''.join([x for x in text if x not in exclude_char_list])

    # print('raw_text', text)
    text = rectify(text)

    # 判断是否处理正确
    if len(text) == 4 and text.isdecimal():  # 只有4位纯数字才可能对
        return True, text
    else:
        return False, text


def download_captcha():
    try:
        if captcha_url:
            out_img = open("captcha.jpg", "wb")
            img_resp = requests.get(captcha_url)
            if img_resp.status_code != 200:
                print("[-] ERROR: captcha_url http_code is %d" % img_resp.status_code)
            img = img_resp.content
            if img.decode('utf-8') == '系统维护中，请稍候访问':
                print('[-] 系统维护中，请稍候访问!')
                sys.exit()
            out_img.write(img)
            out_img.flush()
            out_img.close()
            print("[+] 验证码保存成功, 请自行查看记录.")
        else:
            print('[-] ERROR: captcha_url is NULL')
    except Exception as err:
        print("[-] ERROR: save captcha error: %s", err)


if __name__ == '__main__':
    # download_captcha()
    img = 'captcha.jpg'
    print(verify(img))
