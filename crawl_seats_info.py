#!/usr/bin/env python
# coding: utf-8
# @Time     : 2018/10/16 21:12
# @Author   : guo qun
# @FileName : crawl_seats_info.py
# @Project  : MyZoneMySeat


import requests
import sys
import datetime
from lxml import etree
from hlju_lib_urls import *
from sec import username, password
from db import SeatDB


class HljuLibrarySeat(object):

    def __init__(self):
        self.s = requests.session()
        index_resp = self.s.get(index_url)
        if index_resp.status_code != 200:
            print("[-] ERROR: 读取首页失败, HTTP_STATUS_CODE: %d", index_resp.status_code)
        index_html = index_resp.content
        if index_html.decode("utf-8") == '系统维护中，请稍候访问':
            print('[*] WARN: 图书馆预约系统维护中, 暂时无法使用!')
            sys.exit()

        # 获取SYNCHRONIZER_TOKEN
        xpath_reg = '''//input[@id="SYNCHRONIZER_TOKEN"]/@value'''
        root = etree.HTML(index_html)
        self.token = root.xpath(xpath_reg)[0]

        # 获取cookie
        ck_dict = requests.utils.dict_from_cookiejar(self.s.cookies)  # 将jar格式转为dict
        self.ck = 'JSESSIONID=' + ck_dict['JSESSIONID']  # 重组cookies

        self.headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'DNT': '1',
            'Origin': 'http://seat1.lib.hlju.edu.cn',
            'Referer': 'http://seat1.lib.hlju.edu.cn/login?targetUri=%2F',
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36",
            "Cookie": self.ck
        }
        self.tomorrow_date = str(datetime.date.today() + datetime.timedelta(days=1))

    def download_captcha(self):
        is_down_ok = False
        try:
            if captcha_url:
                out_img = open("captcha.jpg", "wb")
                img_resp = self.s.get(captcha_url, headers=self.headers)
                if img_resp.status_code != 200:
                    print("[-] ERROR: captcha_url http_code is %d" % img_resp.status_code)
                img = img_resp.content
                out_img.write(img)
                out_img.flush()
                out_img.close()
                print("[+] 验证码保存成功, 请自行查看记录.")
                is_down_ok = True
            else:
                print('[-] ERROR: captcha_url is NULL')
        except Exception as err:
            print("[-] ERROR: save captcha error: %s", err)
            is_down_ok = False
        return is_down_ok

    def login(self, username, password):
        post_data = {
            'SYNCHRONIZER_TOKEN': self.token,
            'SYNCHRONIZER_URI': '/login',
            'username': username,
            'password': password,
            'captcha': input('[+] 请查看captcha.jpg, 输入验证码\n')
        }
        resp = self.s.post(url=login_url, data=post_data, headers=self.headers)
        result = resp.content.decode('utf-8')
        root = etree.HTML(result)
        title = root.xpath("//title")[0].text
        if (title == '自选座位 :: 图书馆空间预约系统'):
            return True, '登录成功'
        else:
            return False, '登录失败'

    # def get_seat_info(self, building='null', room='null', hour='null', startMin='null', endMin='null', offset=0, power='null', window='null', timeout=5.0):
    def get_seat_info(self, offset=0):
        seat_dict = dict()
        resp = self.s.get(url=free_book_query_url+'?offset={N}'.format(N=offset), headers=self.headers)
        seat_json = resp.json()
        seat_count = seat_json['seatNum']
        seat_str = seat_json['seatStr']
        seat_page = seat_json['offset']
        if seat_count == 0:
            return False, seat_dict
        free_seat_reg = '''//ul[@class="item"]/li[@class="free"]'''
        root = etree.HTML(seat_str)
        seats_eles = root.xpath(free_seat_reg)
        for seat in seats_eles:
            raw_seat_id = seat.get('id')
            try:
                seat_id = raw_seat_id.split('_')[1]
            except Exception as err:
                print('[-] ERROR: 分割座位ID错误, MSG: %s', err)
                sys.exit()
            # seat_title = seat.get('title')
            seat_num = seat.xpath('dl/dt')[0].text
            seat_desc = seat.xpath('dl/dd')[0].text
            # print(seat_id, type(seat_id), seat_title, type(seat_title), seat_num, type(seat_num))
            seat_dict[seat_id] = [seat_num, seat_desc]
        return True, seat_dict


if __name__ == '__main__':
    sd = SeatDB()
    sd.init_seat_info_tb()

    h = HljuLibrarySeat()
    if h.download_captcha():
        login_status, login_msg = h.login(username=username, password=password)
        if login_status:
            print('[+] 登录成功!')
            print('[+] 开始爬取所有座位信息...')
            flag = True
            all_seat_data = list()
            for offset in range(100):
                if flag:
                    flag, seat_info_dict = h.get_seat_info(offset=offset)
                    for seat_id, seat_info in seat_info_dict.items():
                        temp_data = [seat_id, seat_info[0], seat_info[1]]
                        all_seat_data.append(temp_data)
            sd.load_seat_info(all_seat_data)
        else:
            print('[-] ERROR: 请检查是否可以正常访问登录页面, 以及验证是否输入正确!')
    else:
        print("[-] ERROR: 下载验证码失败, 请检查系统是否可以正常访问!")
