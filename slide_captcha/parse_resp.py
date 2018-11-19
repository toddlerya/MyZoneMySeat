#!/usr/bin/env python
# coding: utf-8
# @Time     : 2018/11/15 9:16  
# @Author   : toddlerya
# @FileName : parse_resp.py
# @Project  : test

import json
import base64
import codecs
import numpy as np
from random import randint

np.set_printoptions(threshold=3000)
from PIL import Image
from collections import defaultdict

from base_lib import re_joint_dir_by_os


def mock_resp():
    all_resp = list()
    with codecs.open('verify_code_resp.txt', mode='r', encoding='utf-8') as f:
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


def cut_noise(image, threshold):
    """
    去掉二值化处理后的图片中的噪声点
    :param image:
    :param threshold:
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

            # 如果该位置的九宫内的黑色数量小于等于threshold，则判断为噪声
            if len(pixel_set) <= threshold:
                change_pos.append((i, j))

    # 对相应位置进行像素修改，将噪声处的像素置为1（白色）
    for pos in change_pos:
        image.putpixel(pos, 1)

    return image  # 返回修改后的图片


def get_feature(target_img, target_size):
    target_image = target_img.resize(target_size)  # 尺寸归一化
    target_image_gray = target_image.convert('L')

    # 计算出sheild_bin_table.txt
    # bin_table = target_imgry.point(lambda x: 1 if x > 120 else 0)
    # target_imgry_array = np.asarray(bin_table)
    # print(target_imgry_array)

    # 自适应计算阈值
    threshold = OTSU_enhance(np.array(target_image_gray))
    bin_table = target_image_gray.point(lambda x: 1 if x > threshold else 0)
    target_image_gray_array = np.asarray(bin_table)
    return target_image_gray_array


def OTSU_enhance(img_gray, th_begin=0, th_end=256, th_step=1):
    """
    大津法求阈值
    http://www.labbookpages.co.uk/software/imgProc/otsuThreshold.html
    http://www.ruanyifeng.com/blog/2013/03/similar_image_search_part_ii.html
    https://blog.csdn.net/u012771236/article/details/44975831
    :param img_gray:
    :param th_begin:
    :param th_end:
    :param th_step:
    :return:
    """
    assert img_gray.ndim == 2, "must input a gray img"

    max_g = 0
    suitable_th = 0
    for threshold in range(th_begin, th_end, th_step):
        bin_img = img_gray > threshold
        bin_img_inv = img_gray <= threshold
        fore_pix = np.sum(bin_img)
        back_pix = np.sum(bin_img_inv)
        if 0 == fore_pix:
            break
        if 0 == back_pix:
            continue

        w0 = float(fore_pix) / img_gray.size
        u0 = float(np.sum(img_gray * bin_img)) / fore_pix
        w1 = float(back_pix) / img_gray.size
        u1 = float(np.sum(img_gray * bin_img_inv)) / back_pix
        # intra-class variance
        g = w0 * w1 * (u0 - u1) * (u0 - u1)
        if g > max_g:
            max_g = g
            suitable_th = threshold
    return suitable_th


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
                    k = list(each_crop.keys())[0]
                    v = list(each_crop.values())[0]
                    sp_k = [int(s) for s in k.split('_')]
                    if _x == sp_k[0] and _y == sp_k[1]:
                        real_whole_img.paste(v, (_x, _y))
        real_whole_img.save('real_whole_img.jpg')

    def calc_x_distance_by_histogram(self):
        target_image = Image.open('target.jpg')
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

    def calc_x_distance_by_vector(self):
        # 计算出sheild_bin_table.txt
        # target_image = Image.open('target.jpg')
        # target_imgry = target_image.convert('L')
        # target_sheild_vector = get_feature(target_imgry, (50, 50), 5)
        # print(target_sheild_vector)

        # 加载sheild_bin_table模型
        sheild_matrix = np.loadtxt('sheild_bin_table.txt', dtype=int)
        sheild_matrix_size = sheild_matrix.size

        bg_image = Image.open('real_whole_img.jpg')

        # all_diff_list = defaultdict(list)
        similar_dict = dict()
        max_similar_value = 0
        count = 0
        for h in range(0, self.height, 1):
            for w in range(0, self.width, 1):
                if w > self.width - 50 or h > self.height - 50:  # 此处有bug，无法扫描的最后一行
                    continue
                box = w, h, (w + 50), (h + 50)
                each_region = bg_image.crop(box)
                _target_matrix = get_feature(each_region, (50, 50))
                similar_value = ((sheild_matrix == _target_matrix).sum())
                if similar_value >= max_similar_value:
                    max_similar_value = similar_value
                    similar_dict = dict()
                    similar_dict[max_similar_value] = [each_region, w, h]
                # all_diff_list[similar_value].append(each_region)
                # all_diff_list[similar_value].append([w, h])
                count += 1
        # similar_score = max(list(all_diff_list.keys()))
        # similar_value = all_diff_list[similar_score]
        similar_score = list(similar_dict.keys())[0]
        similar_data = list(similar_dict.values())
        # goal_img, goal_w, goal_h = similar_value[0], similar_value[1][0], similar_value[1][1]
        goal_img, goal_w, goal_h = similar_data[0][0], similar_data[0][1], similar_data[0][2]
        temp_image_name = re_joint_dir_by_os('temp|{0}_{1}_{2}_{3}.jpg'.format(similar_score, self.img_name, goal_w, goal_h))
        goal_img.save(temp_image_name)
        print(
            '图片编号: {} 相似得分: {} 横坐标偏移像素: {} 纵坐标偏移像素: {} 共计扫描次数: {}'.format(self.img_name, similar_score, goal_w, goal_h,
                                                                          count))


if __name__ == '__main__':
    for num, each in enumerate(mock_resp()):
        print(num)
        csv = CalcSlideValue()
        csv.handle_resp(each)
        csv.crop_img()
        csv.rebuild_img()
        # csv.calc_x_distance_by_histogram()
        csv.calc_x_distance_by_vector()
        # break

    # http://www.ruanyifeng.com/blog/2013/03/similar_image_search_part_ii.html
