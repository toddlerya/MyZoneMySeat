#!/usr/bin/env python
# coding: utf-8
# @Time     : 2018/10/16 21:12
# @Author   : guo qun
# @FileName : seat_tool.py
# @Project  : MyZoneMySeat

import requests
import sys
import datetime
import time
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

    def get_free_book_info(self, hour='null', startMin='null', endMin='null', offset=0, power='null', window='null', timeout=5.0):
        '''
        查询预定座位信息
        :param hour:
        :param startMin:
        :param endMin:
        :param offset:
        :param power:
        :param window:
        :param timeout:
        :return:
        '''
        # 查询预定明天的座位信息
        self.all_free_seat = dict()
        free_book_form = {
            'onDate': self.tomorrow_date,
            'building': '1',  # 1-老馆
            'room': '28',  # 三楼原电阅室-预约
            'hour': hour,  # 14h
            'startMin': startMin,
            'endMin': endMin,
            'power': power,
            'window': window,
            'offset': offset
        }

        print('[+] 开始查询空座...')
        resp = self.s.get(url=free_book_query_url, data=free_book_form, headers=self.headers, timeout=timeout)
        seat_json = resp.json()
        seat_num = seat_json['seatNum']
        seat_str = seat_json['seatStr']
        free_seat_reg = '''//ul[@class="item"]/li[@class="free"]'''
        # free_seat_reg = '''//ul[@class="item"]/li[@class="using"]'''
        root = etree.HTML(seat_str)
        seats_eles = root.xpath(free_seat_reg)
        print('[+] 当前可选座位共: %s个' % seat_num)
        for seat in seats_eles:
            raw_seat_id = seat.get('id')
            try:
                seat_id = raw_seat_id.split('_')[1]
            except Exception as err:
                print('[-] ERROR: 分割座位ID错误, MSG: %s', err)
                sys.exit()
            seat_title = seat.get('title')
            seat_num = seat.xpath('dl/dt')[0].text
            # print(seat_id, type(seat_id), seat_title, type(seat_title), seat_num, type(seat_num))
            self.all_free_seat[seat_id] = [seat_num, seat_title]
        free_seat_count = len(self.all_free_seat)
        print('[+] 当前空闲座位共: %d个' % free_seat_count)  # {'32362': ['005', '正在使用中'], '27512': ['016', '正在使用中']}
        if free_seat_count > 0:
            print('[+] 有可预约空座, 开始预约!')
            return True
        else:
            print('[!] 无可预约空座, 早起吧骚年!')
            return False

    def get_book_token(self):
        resp = self.s.get(booking_url_01)
        html = resp.content.decode('utf-8')
        root = etree.HTML(html)
        book_token_ele = root.xpath('//input[@name="SYNCHRONIZER_TOKEN"]')[0]
        self.book_token = book_token_ele.get('value')
        # self.system_time = root.xpath('''//span[@id="currentTime"]''')[0].text
        # print('system_time', self.system_time)
        if len(self.book_token) == 36:
            return True
        else:
            return False

    def book_seat(self, seat_id, start, end):
        post_data = {
            'SYNCHRONIZER_TOKEN': self.book_token,
            'SYNCHRONIZER_URI': '/',
            "seat": seat_id,
            "start": str(start),  # 480 ---> 8:00
            "end": str(end)  # 1320 ---> 22:00
        }
        # print(post_data)
        resp = self.s.post(url=book_seat_self_url, data=post_data, headers=self.headers, timeout=10.0)
        if resp.status_code != 200:
            print('[-] ERROR 预定失败, 请求错误! HTTP_CODE: %d', resp.status_code)
        html = resp.content.decode("utf-8")
        # print(html)
        root = etree.HTML(html)
        try:
            temp_book_status = root.xpath('''//div[@class="layoutSeat"]/dl''')
            book_status = temp_book_status[0][0].text
        except Exception as err:
            print('[-] ERROR 获取预定信息错误 ERROR_MSG: %s' % err)
        else:
            if book_status == '系统已经为您预定好了':
                print('预定成功, 请登录系统查看预约信息!')
                sys.exit()
            else:
                fail_msg = temp_book_status[0].xpath('//span/text()[last()]')[-1]
                if fail_msg == '已有1个有效预约，请在使用结束后再次进行选择':
                    print('[*] 预定失败: %s' % fail_msg)
                    sys.exit()
                else:
                    print('[-] ERROR 预定失败: %s, 继续尝试其他座位!' % fail_msg)


def wait_open(hour, minute):
    print('[+] 等待系统预定时间开放... 开放预定时间为 %d:%d' % (int(hour), int(minute)))
    while True:
        __temp_time = time.ctime()
        now_hour_min = "".join(__temp_time.split()[-2][0:-3].split(':'))
        now_time = int(now_hour_min)
        if now_time >= int(''.join([str(hour), str(minute)])):
            print('[+] 时间到我们开始抢座位!')
            break
        else:
            time.sleep(0.5)


if __name__ == '__main__':
    # ==================== 用户自定义配置 BEGIN =======================
    # 请根据需要修改时间配置
    # 开始结束时间，计算公式为24小时制时间乘以60，比如：
    #                8:00  转换为  8 x 60 = 480
    #                21:00 转换为 21 x 60 = 1260
    # 开始时间
    stat_time = 420  # 420  ---> 7:00
    # 结束时间
    end_time = 1260  # 1260 ---> 22:00
    # 预定房间名称
    goal_room = '三楼原电阅室-预约'
    # 系统开放时间
    system_open_time = (18, 30)  # 18:30
    # ==================== 用户自定义配置 END ==========================

    #  直接从数据库读取目标房间的座位信息, 按照ID从大到小排列, 暴力抢座
    sd = SeatDB()
    goal_seats = sd.query_sql("SELECT seat_id, seat_number FROM seat_info WHERE seat_room = ? ORDER BY seat_id DESC", goal_room)

    h = HljuLibrarySeat()
    if h.download_captcha():
        login_status, login_msg = h.login(username=username, password=password)
        if login_status:
            print('[+] 登录成功!')
            if not h.get_book_token():
                print('[-] ERROR: 获取预定token失败!')
                sys.exit()
            wait_open(hour=system_open_time[0], minute=system_open_time[1])
            # if h.get_free_book_info():
            #     for each_seat_id, each_seat_info in h.all_free_seat.items():
            #         h.book_seat(seat_id=each_seat_id, start=stat_time, end=end_time)
            for seat in goal_seats:  # 直接从数据库读取, 暴力抢座
                seat_id = seat[0]
                h.book_seat(seat_id=seat_id, start=stat_time, end=end_time)
            # 调试代码
            # h.book_seat('26631', '1260', '1320')
        else:
            print('[-] ERROR: 请检查是否可以正常访问登录页面, 以及验证是否输入正确!')
    else:
        print("[-] ERROR: 下载验证码失败, 请检查系统是否可以正常访问!")
