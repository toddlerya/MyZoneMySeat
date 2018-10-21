#!/usr/bin/env python
# coding: utf-8
# @Time     : 2018/10/16 21:12
# @Author   : toddlerya
# @FileName : seat_tool.py
# @Project  : MyZoneMySeat

import requests
import sys
import datetime
import time
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

        self.book_token = ''

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
                if img == '系统维护中，请稍候访问':
                    print('[-] 系统维护中，请稍候访问!')
                    sys.exit()
                out_img.write(img)
                out_img.flush()
                out_img.close()
                # print("[+] 验证码保存成功, 请自行查看记录.")
                print("[+] 验证码保存成功.")
                is_down_ok = True
            else:
                print('[-] ERROR: captcha_url is NULL')
        except Exception as err:
            print("[-] ERROR: save captcha error: %s", err)
            is_down_ok = False
        return is_down_ok

    def get_free_book_info(self, hour='null', start_min='null', end_min='null', offset=0, power='null', window='null',
                           timeout=5.0):
        """
        查询预定座位信息
        :param hour:
        :param start_min:
        :param end_min:
        :param offset:
        :param power:
        :param window:
        :param timeout:
        :return:
        """
        # 查询预定明天的座位信息
        all_free_seat = dict()
        free_book_form = {
            'onDate': self.tomorrow_date,
            'building': '1',  # 1-老馆
            'room': '28',  # 三楼原电阅室-预约
            'hour': hour,  # 14h
            'startMin': start_min,
            'endMin': end_min,
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
        for __seat in seats_eles:
            raw_seat_id = __seat.get('id')
            try:
                _seat_id = raw_seat_id.split('_')[1]
            except Exception as err:
                print('[-] ERROR: 分割座位ID错误, MSG: %s', err)
                sys.exit()
            seat_title = __seat.get('title')
            seat_num = __seat.xpath('dl/dt')[0].text
            all_free_seat[_seat_id] = [seat_num, seat_title]
        free_seat_count = len(all_free_seat)
        print('[+] 当前空闲座位共: %d个' % free_seat_count)  # {'32362': ['005', '正在使用中'], '27512': ['016', '正在使用中']}
        if free_seat_count > 0:
            print('[+] 有可预约空座, 开始预约!')
            return True, all_free_seat
        else:
            print('[!] 无可预约空座, 早起吧骚年!')
            return False, all_free_seat

    def get_book_token(self):
        resp = self.s.get(url=booking_url_01, headers=self.headers, timeout=10.0)
        html = resp.content.decode('utf-8')
        root = etree.HTML(html)
        book_token_ele = root.xpath('//input[@name="SYNCHRONIZER_TOKEN"]')[0]
        self.book_token = book_token_ele.get('value')
        if len(self.book_token) == 36:
            return True
        else:
            return False

    def book_seat(self, seat_id: str, start, end, date=str(datetime.date.today())):
        """
        提交预定座位表单
        :param seat_id: 座位ID
        :param start: 使用开始时间
        :param end:  使用结束时间
        :param date: 预定日期, 默认为当日
        :return: 无返回值, 预定成功则终止程序
        """
        post_data = {
            'SYNCHRONIZER_TOKEN': self.book_token,
            'SYNCHRONIZER_URI': '/',
            'date': date,
            "seat": seat_id,
            "start": str(start),  # 480 ---> 8:00
            "end": str(end)  # 1320 ---> 22:00
        }
        resp = self.s.post(url=book_seat_self_url, data=post_data, headers=self.headers, timeout=30.0)
        if resp.status_code != 200:
            print('[-] ERROR 预定失败, 请求错误! HTTP_CODE: %d', resp.status_code)
        html = resp.content.decode("utf-8")
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
                    print('[*] 预定失败: {{ %s }}' % fail_msg)
                else:
                    print('[-] ERROR 预定失败: {{ %s }}, 继续尝试其他座位!' % fail_msg)

    def wait_open(self, hour, minute):
        print('[+] 等待系统预定时间开放... 开放预定时间为 %d:%d' % (int(hour), int(minute)))
        open_time_int = int(''.join([str(hour), str(minute)]))
        while True:
            __temp_time = time.ctime()
            now_hour_min = "".join(__temp_time.split()[-2][0:-3].split(':'))
            now_time = int(now_hour_min)
            if now_time >= open_time_int:
                print('[+] 时间到我们开始抢座位!')
                break
            elif now_time <= open_time_int - 3:
                resp = self.s.get(url=booking_url_01, headers=self.headers, timeout=10.0)
                if resp.status_code == 200:
                    print("[+] 等待中, 确认存活...")
                time.sleep(20)
            else:
                time.sleep(0.5)


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
    # ==================== 用户自定义配置 BEGIN =======================
    # 请根据需要修改时间配置
    # 开始结束时间，计算公式为24小时制时间乘以60，比如：
    #                8:00  转换为  8 x 60 = 480
    #                21:00 转换为 21 x 60 = 1260
    # 开始时间
    start_time = 420  # 420  ---> 7:00
    # 结束时间
    end_time = 1320  # 1320 ---> 22:00
    # 预定房间名称
    goal_room = '三楼原电阅室-预约'
    # 系统开放时间
    system_open_time = (18, 30)  # 18:30
    # 网络访问失败重试次数, 应对渣服务器
    # urllib3 will sleep for:
    # {backoff factor} * (2 ^ ({number of total retries} - 1)) seconds.
    # If the backoff_factor is 0.1, then sleep() will sleep for [0.0s, 0.2s, 0.4s, …] between retries.
    # It will never be longer than Retry.BACKOFF_MAX
    max_retries = 11
    backoff_factor = 1
    # 1 * 2 ** 10 / 60 = 17 min
    # ==================== 用户自定义配置 END ==========================

    #  直接从数据库读取目标房间的座位信息, 按照ID从大到小排列, 暴力抢座
    sd = SeatDB()
    # goal_seats = sd.query_sql("SELECT seat_id, seat_number FROM seat_info WHERE seat_room = ? ORDER BY seat_id DESC", goal_room)
    goal_seats = sd.query_sql("SELECT seat_id, seat_number, seat_room FROM seat_info ORDER BY seat_id DESC")

    h = HljuLibrarySeat(retries=max_retries, backoff_factor=backoff_factor, status_forcelist=[500, 502, 503, 504])
    login_status, login_msg, h = auto_login(session_obj=h, username=username, password=password)
    if login_status:
        print('[+] 登录成功!')
        h.wait_open(hour=system_open_time[0], minute=system_open_time[1])
        # ======================= 查询空座, 然后订座, 会卡爆 =========================
        # get_free_flag, free_seats = h.get_free_book_info()
        # if get_free_flag:
        #     for each_seat_id, each_seat_info in free_seats.items():
        #         h.book_seat(seat_id=each_seat_id, start=stat_time, end=end_time)
        # ======================= 根据数据库的座位, 直接下单, 直到成功为止 ==========================
        for offset_num in range(0, 120, 15):  # 从起始时间开始, 每间隔15分钟尝试一次任务, 直到两个小时为止
            for seat in goal_seats:
                start_time += offset_num
                print('[+] 当前预定起始时间为: %d' % (start_time / 60))
                seat_id_code: str = seat[0]
                seat_num: str = seat[1]
                seat_room: str = seat[2]
                # 每次提交预定信息前要先访问一次"自助选座"获取"预定token", 否则会出现非法Invalid CSRF token错误
                if not h.get_book_token():
                    print('[-] ERROR: 获取预定token失败!')
                print("[+] 当前预定目标为: {0}-->{1}".format(seat_room, seat_num))
                h.book_seat(seat_id=seat_id_code, start=start_time, end=end_time, date=h.tomorrow_date)
        # ====================== 调试代码 ==============================
        # 每次提交预定信息前要先访问一次"自助选座"获取"预定token", 否则会出现非法Invalid CSRF token错误
        # if not h.get_book_token():
        #     print('[-] ERROR: 获取预定token失败!')
        # h.book_seat('21409', '1260', '1320')
    else:
        print('[-] ERROR: 请检查是否可以正常访问登录页面, 以及验证是否输入正确!')
