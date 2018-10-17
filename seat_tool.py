#!/usr/bin/env python
# coding: utf-8
# @Time     : 2018/10/16 21:12
# @Author   : guo qun
# @FileName : seat_tool.py
# @Project  : MyZoneMySeat

import requests
import sys
import datetime
# from bs4 import BeautifulSoup
from lxml import etree
from hlju_lib_urls import *
from sec import username, password


class HljuLibrarySeat(object):

    def __init__(self):
        self.s = requests.session()
        index_resp = self.s.get(index_url)
        if index_resp.status_code != 200:
            print("[-] ERROR: 读取首页失败, HTTP_STATUS_CODE: %d", index_resp.status_code)
        index_html = index_resp.content
        if index_html.decode("utf-8") == '系统维护中，请稍候访问':
            print('[-] WARN: 图书馆预约系统维护中, 暂时无法使用!')
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

    def download_captcha(self):
        is_down_ok = False
        try:
            if captcha_url:
                out_img = open("captcha.jpg", "wb")
                img_resp = self.s.get(captcha_url, headers=self.headers)
                if img_resp.status_code != 200:
                    print("ERROR: captcha_url http_code is %d" % img_resp.status_code)
                img = img_resp.content
                out_img.write(img)
                out_img.flush()
                out_img.close()
                print("[+] 验证码保存成功, 请自行查看记录.")
                is_down_ok = True
            else:
                print('ERROR: captcha_url is NULL')
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
            'captcha': input('请输入验证码\n')
        }
        resp = self.s.post(url=login_url, data=post_data, headers=self.headers)
        result = resp.content.decode('utf-8')
        root = etree.HTML(result)
        title = root.xpath("//title")[0].text
        if (title == '自选座位 :: 图书馆空间预约系统'):
            return True, '登录成功'
        else:
            return False, '登录失败'

    def get_free_book_info(self):
        # 查询预定明天的座位信息
        self.all_free_seat = dict()
        tomorrow_date = str(datetime.date.today() + datetime.timedelta(days=1))
        free_book_form = {
            'onDate': tomorrow_date,
            'building': '1',  # 1-老馆
            'room': '28',  # 三楼原电阅室-预约
            'hour': '14',  # 14h
            'startMin': 'null',
            'endMin': 'null',
            'power': 'null',
            'window': 'null'
        }
        resp = self.s.post(url=free_book_query_url, data=free_book_form, headers=self.headers)
        seat_json = resp.json()
        seat_num = seat_json['seatNum']
        seat_str = seat_json['seatStr']
        # free_seat_reg = '''//ul[@class="item"]/li[@class="free"]'''
        free_seat_reg = '''//ul[@class="item"]/li[@class="using"]'''
        root = etree.HTML(seat_str)
        seats_eles = root.xpath(free_seat_reg)
        print('当前可选座位共: %s个\n' % seat_num)
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
        print('当前空闲座位共: %d个' % len(
            self.all_free_seat))  # {'seat_32362': ['正在使用中', '005'], 'seat_27512': ['正在使用中', '016']}

    def book_seat(self):
        for each_seat in self.all_free_seat:
            pass
        # post_data = {
        #     "seat": seat_id,
        #     "date": date,
        #     "start": start_time,
        #     "end": end_time
        # }

        # '''
        # 布局选座 直接使用room_id唯一标注一个场馆某个楼层的某个房间,如信部分馆二楼东区,关于参数building(场馆)和floor(楼层)可以暂时不考虑
        # '''
        # def map_book(self,username,password,room_id,date,start_seat_id,end_seat_id,start_time,end_time):
        #     #isLogin = self.login(username,password)
        #     #if(isLogin):
        #     #get请求 发送room_id和date
        #     url1 = "http://seat.lib.whu.edu.cn/mapBook/getSeatsByRoom?room="+room_id+"&date="+date
        #     response= urllib.request.urlopen(url1)
        #     result = response.read().decode("utf-8")
        #     soup = BeautifulSoup(result, "html.parser")
        #     lis = soup.find_all("li")
        #     isBooked = False
        #     for li in lis:
        #         if(li.a):
        #             #座位id范围
        #             seat_num = li.a.text
        #             if(start_seat_id <= int(seat_num) <= end_seat_id):
        #                 #这里获得到每一个座位id
        #                 seat_id = li["id"].split("_")[1]
        #                 post_data = {
        #                     "seat":seat_id,
        #                     "date":date,
        #                     "start":start_time,
        #                     "end":end_time
        #                 }
        #                 headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:50.0) Gecko/20100101 Firefox/50.0"}
        #                 #post请求 请求内容为date和座位id
        #                 url2 = "http://seat.lib.whu.edu.cn/selfRes"
        #                 post_data = urllib.parse.urlencode(post_data).encode("utf-8")
        #                 request = urllib.request.Request(url2, post_data, headers)
        #                 response = urllib.request.urlopen(request)
        #                 result = response.read().decode("utf-8")
        #                 if("预约失败" in result):
        #                     print("Booking Failed. Date "+date+", Seat No."+seat_num+", room "+room_id+".")
        #                     isBooked = False
        #                 else:
        #                     isBooked = True
        #                     print("Booking Success! Date "+date+", Seat No."+seat_num+", room "+room_id+".\n")
        #                     os._exit()
        #                     break
        #     return isBooked
        #
        #
        # def randomSeatNum(self,start,end):
        #     return random.randint(start,end)
        #
        # #根据room_id获得当前room中seat_no的边界
        # def getSeatIdBoundary(self,room_id):
        #     url_get_seats_by_room = "http://seat.lib.whu.edu.cn/mapBook/getSeatsByRoom?room=" + room_id
        #     response = urllib.request.urlopen(url_get_seats_by_room)
        #     result = response.read().decode("utf-8")
        #     soup = BeautifulSoup(result, "html.parser")
        #     lis = soup.find_all("li")
        #     count = 0
        #     for li in lis:
        #         if (li.a):
        #             count += 1
        #     return count


if __name__ == '__main__':
    h = HljuLibrarySeat()
    if h.download_captcha():
        login_status, login_msg = h.login(username=username, password=password)
        if login_status:
            print('[+] 登录成功!')
            h.get_free_book_info()
        else:
            print('[-] ERROR: 请检查是否可以正常访问登录页面, 以及验证是否输入正确!')
    else:
        print("[-] ERROR: 下载验证码失败, 请检查系统是否可以正常访问!")
