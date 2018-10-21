#!/usr/bin/env python
# coding: utf-8
# @Time     : 2018/10/16 21:12
# @Author   : toddlerya
# @FileName : crawl_seats_info.py
# @Project  : MyZoneMySeat


import requests
import sys
import datetime
from random import choice
from lxml import etree
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from hlju_lib_config import *
from sec import username, password
from verify_captcha import verify
from db import SeatDB



class HljuLibrarySeat(object):

    def __init__(self, retries=10, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504]):
        self.s = requests.session()
        # 重试访问, 应对服务器崩溃的情况
        # https://stackoverflow.com/questions/15431044/can-i-set-max-retries-for-requests-request
        # https://urllib3.readthedocs.io/en/latest/reference/urllib3.util.html
        # backoff_factor
        # A backoff factor to apply between attempts after the second try (most errors are resolved immediately
        # by a second try without a delay). urllib3 will sleep for:
        # {backoff factor} * (2 ^ ({number of total retries} - 1))
        # seconds. If the backoff_factor is 0.1, then sleep() will sleep for [0.0s, 0.2s, 0.4s, …] between retries.
        # It will never be longer than Retry.BACKOFF_MAX.
        # By default, backoff is disabled (set to 0).

        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.s.mount('http://', adapter=adapter)
        self.s.mount('https://', adapter=adapter)
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
        free_seat_reg = '''//ul[@class="item"]/li'''
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

    def get_seat_by_room(self, room_id):
        seat_dict = dict()
        resp = self.s.get(url=room_seat_map_url + '?room={N}'.format(N=room_id), headers=self.headers)
        html = resp.content
        root = etree.HTML(html)
        seat_eles = root.xpath('''//ul/li[starts-with(@id, "seat_")]''')
        for seat in seat_eles:
            raw_seat_id = seat.get('id')
            try:
                seat_id = raw_seat_id.split('_')[1]
            except Exception as err:
                print('[-] ERROR: 分割座位ID错误, MSG: %s', err)
                sys.exit()
            seat_num = seat.xpath('''a''')[0].text
            seat_desc = room_desc_dict[room_id]
            seat_dict[seat_id] = [seat_num, seat_desc]
        return True, seat_dict


def captcha_verify(session_obj, threshold: int=100):
    """
    下载识别验证码, 直到获得合法验证码为止
    :param threshold: 失败阈值, 默认500次
    :return:
    """
    for i in range(threshold):
        # # 获取新cookie
        index_resp = session_obj.s.get(index_url)
        if index_resp.status_code != 200:
            print("[-] ERROR: 读取首页失败, HTTP_STATUS_CODE: %d", index_resp.status_code)
        index_html = index_resp.content
        if index_html.decode("utf-8") == '系统维护中，请稍候访问':
            print('[*] WARN: 图书馆预约系统维护中, 暂时无法使用!')
            sys.exit()

        # 获取SYNCHRONIZER_TOKEN
        xpath_reg = '''//input[@id="SYNCHRONIZER_TOKEN"]/@value'''
        root = etree.HTML(index_html)
        session_obj.token = root.xpath(xpath_reg)[0]

        # 获取cookie
        ck_dict = requests.utils.dict_from_cookiejar(session_obj.s.cookies)  # 将jar格式转为dict
        session_obj.ck = 'JSESSIONID=' + ck_dict['JSESSIONID']  # 重组cookies

        session_obj.headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'DNT': '1',
            'Origin': 'http://seat1.lib.hlju.edu.cn',
            'Referer': 'http://seat1.lib.hlju.edu.cn/login?targetUri=%2F',
            # "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36",
            "User-Agent": choice(agents),
            "Cookie": session_obj.ck
        }

        if (session_obj.download_captcha()):
            # print("now cookies===>", session_obj.ck, 'now_agent==>', session_obj.headers["User-Agent"])
            flag, res_captcha = verify('captcha.jpg')
            if flag:
                return True, res_captcha
            else:
                # 清空cookies, 下载新验证码
                session_obj.s.cookies.clear()
        else:
            print("[-] ERROR: 下载验证码失败, 请检查系统是否可以正常访问!")
    return False, ''


def auto_login(session_obj, username, password, threshold: int=100):
    """
    自动识别验证码登陆, 目前验证码识别率低, 容易失败, 所以多试几次, 总有成功的机会
    :param username:
    :param password:
    :param threshold:
    :return:
    """
    captcha_verify_threshold = 500
    status_verify, res_verify = captcha_verify(session_obj, captcha_verify_threshold)
    if not status_verify:
        print('[-] 识别验证码{}次未获得合法验证码, 退出程序!'.format(captcha_verify_threshold))
        sys.exit()
    else:
        print('[+] 识别到合法验证码: {}'.format(res_verify))
    for i in range(threshold):
        print('[*] 尝试登陆中, 第{}次...'.format(i + 1))
        post_data = {
            'SYNCHRONIZER_TOKEN': session_obj.token,
            'SYNCHRONIZER_URI': '/login',
            'username': username,
            'password': password,
            'captcha': res_verify
        }
        try:
            resp = session_obj.s.post(url=login_url, data=post_data, headers=session_obj.headers)
            result = resp.content.decode('utf-8')
        except Exception as err:
            print('[*] 发送请求失败==> {}'.format(err))
            print('我看看有没有cookies===>', session_obj.s.cookies.get_dict())
            print('post===>', post_data)
            if str(err) == 'Exceeded 30 redirects.':
                sys.exit()
        else:
            root = etree.HTML(result)
            title = root.xpath("//title")[0].text
            if (title == '自选座位 :: 图书馆空间预约系统'):
                return True, '登录成功', session_obj
            else:
                # 换个验证码继续干...
                print('[*] 验证码校验不通过, 重新获取验证码!')
                status_verify, res_verify = captcha_verify(session_obj, captcha_verify_threshold)
                if not status_verify:
                    print('[-] 识别验证码{}次未获得合法验证码, 退出程序!'.format(captcha_verify_threshold))
                    sys.exit()
                else:
                    print('[+] 识别到合法验证码: {}'.format(res_verify))
    print('[-] 尝试登陆{}次后未遇到正确的验证码, 推出程序'.format(threshold))
    sys.exit()



if __name__ == '__main__':
    sd = SeatDB()
    sd.init_seat_info_tb()

    h = HljuLibrarySeat()
    # login_status, login_msg = h.login(username=username, password=password)
    login_status, login_msg, h = auto_login(session_obj=h, username=username, password=password)
    if login_status:
        print('[+] 登录成功!')
        print('[+] 开始爬取所有座位信息...')
        # flag = True
        # all_seat_data = list()
        # for offset in range(100):
        #     if flag:
        #         flag, seat_info_dict = h.get_seat_info(offset=offset)
        #         for seat_id, seat_info in seat_info_dict.items():
        #             temp_data = [seat_id, seat_info[0], seat_info[1]]
        #             all_seat_data.append(temp_data)
        # sd.load_seat_info(all_seat_data)
        # ============= 采用第二种办法获取所有座位信息 =================
        all_seat_data = list()
        for room in room_desc_dict:
            flag, seat_info_dict = h.get_seat_by_room(room_id=room)
            for seat_id, seat_info in seat_info_dict.items():
                    temp_data = [seat_id, seat_info[0], seat_info[1]]
                    all_seat_data.append(temp_data)
        sd.load_seat_info(all_seat_data)
    else:
        print('[-] ERROR: 请检查是否可以正常访问登录页面, 以及验证是否输入正确!')
