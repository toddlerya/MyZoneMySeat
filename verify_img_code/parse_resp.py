#!/usr/bin/env python
# coding: utf-8
# @Time     : 2018/11/15 9:16  
# @Author   : toddlerya
# @FileName : parse_resp.py
# @Project  : test

from __future__ import unicode_literals

import json
import base64
import numpy as np
from PIL import Image
from collections import defaultdict
import matplotlib.pyplot as plt


def mock_resp():
    all_resp = list()
    with open('verify_code_resp.txt') as f:
        content = f.readlines()
        for line in content:
            resp = json.loads(line)
            all_resp.append(resp)
    return all_resp


def base64_2_img(base64_string, img_name):
    img_data = base64.b64decode(base64_string)
    with open(img_name, 'wb') as f:
        f.write(img_data)
        f.flush()


def get_feature(target_img, target_size, division_value):
    target_image = target_img.resize((50, 50))  # 尺寸归一化
    # target_imgry = target_image.convert('L')
    # target_imgry.show()
    bin_table = target_image.point(lambda x: 1 if x > 90 else 0)
    target_imgry_array = np.asarray(bin_table)
    # target_imgry_array = np.asarray(target_imgry)
    # print target_imgry_array

    # 将二维矩阵转为以为特征向量
    h, w = target_imgry_array.shape
    data = list()
    for x in range(0, w/division_value):
        offset_y = x * division_value
        temp = list()
        for y in range(0, h/division_value):
            offset_x = y * division_value
            temp.append(sum(sum(target_imgry_array[0+offset_y:division_value+offset_y, 0+offset_x:division_value+offset_x])))
        data.append(temp)
    futures_array = np.asarray(data)
    # print futures_array
    futures_vector = futures_array.reshape(futures_array.shape[0]*futures_array.shape[1])
    # print futures_vector
    return futures_vector


def hist_similar(target_h, test_h):

    # assert len(target_h) == test_h
    if len(target_h) == test_h:
        return sum(1-(0 if target == test else float(abs(target-test)/max(target, test)) for target, test in zip(target_h, test_h))/len(target_h))
    else:
        return 0


def calc_similar(target_img, test_img):
    """

    :param target_img:
    :param test_img:
    :return:
    """
    return hist_similar(target_img.histogram(), test_img.histogram())


def difference(hist1,hist2):
    sum1 = 0
    for i in range(len(hist1)):
       if (hist1[i] == hist2[i]):
          sum1 += 1
       else:
           sum1 += 1 - float(abs(hist1[i] - hist2[i]))/ max(hist1[i], hist2[i])
    return sum1/len(hist1)


def is_pixel_equal(target_img, background_img, x, y):
    """
    判断像素是否相同
    :param target_img:
    :param background_img:
    :param x:
    :param y:
    :return:
    """
    bg_pixel = background_img.load()[x, y]
    target_pixel = target_img.load()[x, y]
    threshold = 60
    if (abs(target_pixel[0] - bg_pixel[0]) < threshold) and (abs(target_pixel[1] - bg_pixel[1]) < threshold) and (
            abs(target_pixel[2] - bg_pixel[2]) < threshold):
        return True
    else:
        return False


class CalcSlideValue(object):
    def __init__(self):
        self.img_name = 'default'
        self.repair_height = 0
        self.repair_width = 0
        self.width = 0
        self.height = 0
        self.item_width = 0
        self.item_height = 0
        self.offset = 0
        self.point = dict()
        self.crop_array = list()

    def handle_resp(self, resp_json):
        data = resp_json['data']
        repair_img = data['repairImg']
        whole_img = data['wholeImg']
        self.img_name = data['verifyCode']
        self.repair_height = data['repairHeight']
        self.repair_width = data['repairWidth']
        self.point = eval(data['point'])  # unicode to dict
        self.offset = data['offset']

        whole_img_base64 = whole_img.split(',')[1]
        base64_2_img(whole_img_base64, 'whole_img.jpg')

        repair_img_base64 = repair_img.split(',')[1]
        base64_2_img(repair_img_base64, 'repair_img.jpg')

    def crop_img(self):
        self.crop_array = list()
        _img = Image.open('whole_img.jpg')
        self.item_width = self.point['itemWidth']  # 10
        self.item_height = self.point['itemHeight']  # 10
        self.width = self.point['width']  # 300
        self.height = self.point['height']  # 150
        point_array = self.point['point']
        # 以item_width为宽度, item_height为高度, 切分为小块
        # region = _img.crop((290,140,300,150))  # 最后一块
        # region.save('test.jpg')
        count = 0
        for h in range(0, self.height, self.item_height):
            for w in range(0, self.width, self.item_width):
                box = w, h, (w + 10), (h + 10)
                # print '{0}, {1}, {2}, {3}'.format(*box)
                # corp((left, upper, right, lower))
                each_region = _img.crop(box)
                each_dict = dict()
                _point = point_array[count]
                each_region_key = '_'.join([str(_point['x']), str(_point['y'])])
                each_dict[each_region_key] = each_region
                # each_dict==> {290_140: img_obj}
                self.crop_array.append(each_dict)
                count += 1

    def rebuild_img(self):
        real_whole_img = Image.new('RGB', (self.width, self.height))
        for _y in range(0, self.height, self.offset):
            for _x in range(0, self.width, self.offset):
                for each_crop in self.crop_array:
                    k = each_crop.keys()[0]
                    v = each_crop.values()[0]
                    sp_k = [int(s) for s in k.split('_')]
                    if _x == sp_k[0] and _y == sp_k[1]:
                        real_whole_img.paste(v, (_x, _y))
        real_whole_img.save('real_whole_img.jpg')

    def calc_x_distance(self):
        target_image = Image.open('target.png')
        # target_sheild_vector = get_feature(target_imgry, (50, 50), 5)
        # print target_sheild_vector
        bg_image = Image.open('real_whole_img.jpg')

        all_diff_list = defaultdict(list)
        for h in range(0, self.height, 1):
            for w in range(0, self.width, 1):
                if w > self.width - 50 or h > self.height - 50:  # 此处有bug，无法扫描的最后一行
                    continue
                box = w, h, (w + 50), (h + 50)
                each_region = bg_image.crop(box)
                diff_value = difference(target_image.convert('RGB').histogram(), each_region.convert('RGB').histogram())
                all_diff_list[diff_value].append(each_region)
                all_diff_list[diff_value].append([w, h])
        similar_score = max(all_diff_list.keys())
        similar_value = all_diff_list[similar_score]
        goal_img, goal_w, goal_h = similar_value[0], similar_value[1][0], similar_value[1][1]
        goal_img.save('temp/{0}_{1}_{2}_{3}.jpg'.format(similar_score, self.img_name, goal_w, goal_h))
        print('图片编号: {} 相似得分: {} 横坐标偏移像素: {} 纵坐标偏移像素: {} 共计扫描次数: {}'.format(self.img_name, similar_score, goal_w, goal_h, len(all_diff_list)))



if __name__ == '__main__':
    for num, each in enumerate(mock_resp()):
        print(num)
        csv = CalcSlideValue()
        csv.handle_resp(each)
        csv.crop_img()
        csv.rebuild_img()
        csv.calc_x_distance()
