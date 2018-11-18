#!/usr/bin/env python
# coding: utf-8
# @Time     : 2018/11/14 11:09  
# @Author   : toddlerya
# @FileName : run.py
# @Project  : test

from __future__ import unicode_literals

import matplotlib.pyplot as plt
from PIL import Image
from collections import defaultdict


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


image = Image.open('demo.png')

w, h = image.size

print(w, h)

imgry = image.convert('L')  # 转为灰度图
max_pixel = get_threshold(imgry)
