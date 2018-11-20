#!/usr/bin/env python
# coding: utf-8
# @Time     : 2018/10/16 21:12
# @Author   : toddlerya
# @FileName : seat_tool.py
# @Project  : MyZoneMySeat

import math
import requests
import sys
import datetime
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from random import choice
from lxml import etree
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from hlju_lib_config import *
from sec import username, password
from verify_captcha import verify
from slide_verify_captcha import do_slide_verify_captcha
from db import SeatDB
from base_lib import Logger, my_log_file
from send_mail import mail


class HljuLibrarySeat(object):

    def __init__(self, retries=10, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504]):
        self.log = Logger(log_name=my_log_file(__file__), level=log_level,
                          fmt='%(asctime)s - [line:%(lineno)d] - %(levelname)s: %(message)s')
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
            self.log.logger.error("读取首页失败, HTTP_STATUS_CODE: %d", index_resp.status_code)
        index_html = index_resp.content
        if index_html.decode("utf-8") == '系统维护中，请稍候访问':
            self.log.logger.warning("图书馆预约系统维护中, 暂时无法使用!")
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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/69.0.3497.100 Safari/537.36",
            "Cookie": self.ck
        }
        self.tomorrow_date = str(datetime.date.today() + datetime.timedelta(days=1))

    def download_captcha(self):
        is_down_ok = False
        json_data = dict()
        try:
            if slide_captcha_url:
                img_resp = self.s.get(slide_captcha_url, headers=self.headers)
                if img_resp.status_code != 200:
                    self.log.logger.error("slide_captcha_url http_code is %d" % img_resp.status_code)
                try:
                    json_data = img_resp.json()
                except Exception as err:
                    self.log.logger.error('获取slide_captcha_url的json数据失败: {}'.format(err))
                    text_data = img_resp.content
                    if text_data == '系统维护中，请稍候访问':
                        self.log.logger.warning("系统维护中，请稍候访问!")
                        sys.exit()
                else:
                    self.log.logger.info("验证码数据获取成功.")
                    is_down_ok = True
            else:
                self.log.logger.error("slide_captcha_url is NULL")
        except Exception as err:
            self.log.logger.error("get slide_captcha error: %s", err)
            is_down_ok = False
        return is_down_ok, json_data


    def get_book_token(self):
        try:
            resp = self.s.get(url=booking_url_01, headers=self.headers, timeout=10.0)
        except Exception as err:
            self.log.logger.error('获取预定token失败: {}'.format(err))
            return False
        else:
            html = resp.content.decode('utf-8')
            root = etree.HTML(html)
            book_token_ele = root.xpath('//input[@name="SYNCHRONIZER_TOKEN"]')[0]
            self.book_token = book_token_ele.get('value')
            if len(self.book_token) == 36:
                return True
            else:
                return False

    def book_seat(self, seat_id: str, room, number, start, end, date=str(datetime.date.today())):
        """
        提交预定座位表单
        :param seat_id: 座位ID
        :param room: 房间名称
        :param number: 座位编号
        :param start: 使用开始时间
        :param end:  使用结束时间
        :param date: 预定日期, 默认为当日
        :return: 预定到座位或已经有预约导致无法下单返回False其他情况返回True
        """
        post_data = {
            'SYNCHRONIZER_TOKEN': self.book_token,
            'SYNCHRONIZER_URI': '/',
            'date': date,
            "seat": seat_id,
            "start": str(start),  # 480 ---> 8:00
            "end": str(end)  # 1320 ---> 22:00
        }
        try:
            resp = self.s.post(url=book_seat_self_url, data=post_data, headers=self.headers, timeout=30.0)
        except Exception as err:
            self.log.logger.critical('预定座位请求发送失败 ERROR_MSG: {}'.format(err))
            return True
        else:
            if resp.status_code != 200:
                self.log.logger.error('预定失败, 请求错误! HTTP_CODE: {}'.format(resp.status_code))
            html = resp.content.decode("utf-8")
            root = etree.HTML(html)
            try:
                temp_book_status = root.xpath('''//div[@class="layoutSeat"]/dl''')
                book_status = temp_book_status[0][0].text
            except Exception as err:
                self.log.logger.error('获取预定信息错误 ERROR_MSG: {}'.format(err))
                return True
            else:
                if book_status == '系统已经为您预定好了':
                    self.log.logger.info('预定成功, 请登录系统查看预约信息!')
                    mail(subject='预定成功', content='座位信息: {R} - {N} 请登陆系统核查确认!'.format(R=room, N=number))
                    return False
                else:
                    fail_msg = temp_book_status[0].xpath('//span/text()[last()]')[-1]
                    if fail_msg == '已有1个有效预约，请在使用结束后再次进行选择':
                        self.log.logger.error('预定失败: < {} >'.format(fail_msg))
                        mail(subject='预定失败', content=fail_msg)
                        return False
                    else:
                        self.log.logger.error('预定失败: < {} >, 继续尝试其他座位!'.format(fail_msg))
                        return True

    def wait_open(self, hour, minute):
        self.log.logger.info('等待系统预定时间开放... 开放预定时间为 %d:%d' % (int(hour), int(minute)))
        open_time_int = int(''.join([str(hour), str(minute)]))
        while True:
            __temp_time = time.ctime()
            now_hour_min = "".join(__temp_time.split()[-2][0:-3].split(':'))
            now_time = int(now_hour_min)
            if now_time >= open_time_int:
                self.log.logger.info('时间到我们开始抢座位!')
                break
            elif now_time <= open_time_int - 3:
                try:
                    resp = self.s.get(url=booking_url_01, headers=self.headers, timeout=10.0)
                except Exception as err:
                    self.log.logger.error('等待中, 查询主页失败: {}'.format(err))
                else:
                    if resp.status_code == 200:
                        self.log.logger.info('等待中, 确认存活...')
                    time.sleep(20)
            else:
                time.sleep(0.5)


def captcha_verify(session_obj, threshold: int = 100):
    """
    下载识别验证码, 直到获得合法验证码为止
    :param session_obj:
    :param threshold: 失败阈值, 默认500次
    :return:
    """
    for i in range(threshold):
        # # 获取新cookie
        index_resp = session_obj.s.get(index_url)
        if index_resp.status_code != 200:
            session_obj.log.logger.error('读取首页失败, HTTP_STATUS_CODE: %d', index_resp.status_code)
        index_html = index_resp.content
        if index_html.decode("utf-8") == '系统维护中，请稍候访问':
            session_obj.log.logger.warning('图书馆预约系统维护中, 暂时无法使用!')
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
            "User-Agent": choice(agents),
            "Cookie": session_obj.ck
        }

        download_status, captcha_json = session_obj.download_captcha()
        if download_status:
            code, _, x_value, _ = do_slide_verify_captcha(captcha_json)
            session_obj.log.logger.info('识别滑动验证码结果: {}, {}'.format(code, x_value))
            payload = {
                'code': code,
                'xvalue': x_value,
                'yvalue': 0,
                'appId': app_id_of_slide_captcha
            }
            resp = session_obj.s.post(verify_slide_captcha_url, headers=session_obj.headers, data=payload)
            if resp.status_code != 200:
                session_obj.log.logger.error("POST slide_captcha_url http_code is %d" % resp.status_code)
            resp_json = resp.json()
            slide_status = resp_json['status']
            auth_id = resp_json['data']['authId']
            if slide_status == 1:
                return True, auth_id
            else:
                # 清空cookies, 下载新验证码
                session_obj.s.cookies.clear()
        else:
            session_obj.log.logger.error('ERROR: 下载验证码失败, 请检查系统是否可以正常访问!')
    return False, '', ''


def auto_login(session_obj, username, password, threshold: int = 100):
    """
    自动识别验证码登陆, 目前验证码识别率低, 容易失败, 所以多试几次, 总有成功的机会
    :param session_obj
    :param username:
    :param password:
    :param threshold:
    :return:
    """
    captcha_verify_threshold = 500
    status_verify, auth_id = captcha_verify(session_obj, captcha_verify_threshold)
    if not status_verify:
        h.log.logger.warning('识别验证码{}次未获得合法验证码, 退出程序!'.format(captcha_verify_threshold))
        sys.exit()
    else:
        h.log.logger.info('识别到合法验证码: {}'.format(auth_id))
    for i in range(threshold):
        h.log.logger.warning('尝试登陆中, 第{}次...'.format(i + 1))
        post_data = {
            'appId': app_id_of_slide_captcha,
            'appAuthKey': app_auth_key_of_slide_captcha,
            'authid': auth_id,
            'username': username,
            'password': password,
            'SYNCHRONIZER_TOKEN': session_obj.token,
            'SYNCHRONIZER_URI': '/login'

        }
        try:
            resp = session_obj.s.post(url=login_url, data=post_data, headers=session_obj.headers)
            result = resp.content.decode('utf-8')
        except Exception as err:
            h.log.logger.error('发送请求失败: {}'.format(err))
            if str(err) == 'Exceeded 30 redirects.':
                h.log.logger.critical('Exceeded 30 redirects.')
                sys.exit()
        else:
            root = etree.HTML(result)
            title = root.xpath("//title")[0].text
            if title == '自选座位 :: 图书馆空间预约系统':
                return True, session_obj
            else:
                # 换个验证码继续干...
                h.log.logger.warning('验证码校验不通过, 重新获取验证码!')
                status_verify, res_verify = captcha_verify(session_obj, captcha_verify_threshold)
                if not status_verify:
                    h.log.logger.error('识别验证码{}次未获得合法验证码, 退出程序!'.format(captcha_verify_threshold))
                    sys.exit()
                else:
                    h.log.logger.info('识别到合法验证码: {}'.format(res_verify))
    h.log.logger.error('尝试登陆{}次后未遇到正确的验证码, 退出程序'.format(threshold))
    sys.exit()


def do_book(session_obj, seat_room, seat_num, seat_id, start, end, date):
    """
    执行预定动作
    :param session_obj:
    :param seat_room:
    :param seat_num:
    :param seat_id:
    :param start:
    :param end:
    :param date:
    :return:
    """
    # 每次提交预定信息前要先访问一次"自助选座"获取"预定token", 否则会出现非法Invalid CSRF token错误
    session_obj.log.logger.info('当前线程ID: {}'.format(threading.current_thread().name))
    if not session_obj.get_book_token():
        session_obj.log.logger.error('获取预定token失败!')
    session_obj.log.logger.info("当前预定目标为: {0}-->{1}".format(seat_room, seat_num))
    return session_obj.book_seat(seat_id=seat_id, room=seat_room, number=seat_num, start=start, end=end, date=date)


if __name__ == '__main__':
    # ==================== 用户自定义配置 BEGIN =======================
    # 请根据需要修改时间配置
    # 开始结束时间，计算公式为24小时制时间乘以60，比如：
    #                8:00  转换为  8 x 60 = 480
    #                21:00 转换为 21 x 60 = 1260
    # 开始时间
    start_time = 480  # 480  ---> 8:00
    # 结束时间
    end_time = 1320  # 1320 ---> 22:00
    # 预定房间名称
    # goal_room = ['三楼自习室-预约', '三楼原电阅室-预约']
    goal_room = ['三楼自习室-预约']
    # goal_room = []
    # 系统开放时间
    system_open_time = (18, 30)  # 18:30
    # 网络访问失败重试次数, 应对渣服务器
    # urllib3 will sleep for:
    # {backoff factor} * (2 ^ ({number of total retries} - 1)) seconds.
    # If the backoff_factor is 0.1, then sleep() will sleep for [0.0s, 0.2s, 0.4s, …] between retries.
    # It will never be longer than Retry.BACKOFF_MAX
    max_retries = 6
    backoff_factor_value = 0.1
    # 0.1 * 2 ** (6-1) = 3.2 sec
    # ==================== 用户自定义配置 END ==========================
    # 多线程
    thread_num = 5
    # https://www.cnblogs.com/zhang293/p/7954353.html

    #  直接从数据库读取目标房间的座位信息, 按照ID从大到小排列, 暴力抢座
    sd = SeatDB()
    if goal_room:
        where_condition = "WHERE seat_room IN ({C})".format(C=",".join([repr(ele) for ele in goal_room]))
        goal_seats = sd.query_sql(
            "SELECT seat_id, seat_number, seat_room FROM seat_info {W_C} ORDER BY seat_number DESC".format(
                W_C=where_condition))
    else:
        goal_seats = sd.query_sql("SELECT seat_id, seat_number, seat_room FROM seat_info ORDER BY seat_number DESC")

    h = HljuLibrarySeat(retries=max_retries, backoff_factor=backoff_factor_value, status_forcelist=[500, 502, 503, 504])
    login_status, h = auto_login(session_obj=h, username=username, password=password)
    if login_status:
        h.log.logger.info('登陆成功!')
        h.wait_open(hour=system_open_time[0], minute=system_open_time[1])
        # ======================= 查询空座, 然后订座, 会卡爆 =========================
        # get_free_flag, free_seats = h.get_free_book_info()
        # if get_free_flag:
        #     for each_seat_id, each_seat_info in free_seats.items():
        #         h.book_seat(seat_id=each_seat_id, start=stat_time, end=end_time)
        # ======================= 根据数据库的座位, 直接下单, 直到成功为止 ==========================
        # 从起始时间开始, 每间隔15分钟尝试一次任务, 直到两个小时为止
        offset_num = 15
        for _ in range(0, 60 * 4 + 15, offset_num):
            start_time_tuple = math.modf(float(format((start_time / 60), '.2f')))
            start_hour = str(int(start_time_tuple[1])).zfill(2)
            start_min = str(int(start_time_tuple[0] * 60)).zfill(2)
            h.log.logger.info('当前预定起始时间为: {H}:{M}'.format(H=start_hour, M=start_min))
            book_form = list()
            for seat in goal_seats:
                seat_id_code: str = seat[0]
                seat_num: str = seat[1]
                seat_room: str = seat[2]
                book_form.append([h, seat_room, seat_num, seat_id_code, start_time, end_time, h.tomorrow_date])
            start_time += offset_num
            # book_form.append([h, 'sssssssss', '255', '29899', 1020, 1080, '2018-10-27'])
            # 多线程抢座
            with ThreadPoolExecutor(thread_num) as executor:
                for each in book_form:
                    f = executor.submit(do_book, *each)
                    thread_err = f.exception()
                    if thread_err:
                        h.log.logger.error('thread_err: {}'.format(thread_err))
                        sys.exit()
                    thread_res = f.result()
                    if thread_res is False:
                        sys.exit()

        # ====================== 调试代码 ==============================
        # 每次提交预定信息前要先访问一次"自助选座"获取"预定token", 否则会出现非法Invalid CSRF token错误
        # if not h.get_book_token():
        # h.book_seat('21409', '1260', '1320')
    else:
        h.log.logger.error('请检查是否可以正常访问登录页面, 以及验证是否输入正确!')
