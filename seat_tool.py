#!/usr/bin/env python
# coding: utf-8
# @Time     : 2018/10/16 21:12
# @Author   : guo qun
# @FileName : seat_tool.py
# @Project  : MyZoneMySeat

import requests
import sys
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
        self.token = root.xpath(xpath_reg)[0].text

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
            'Cookie': 'JSESSIONID=6205E7A25777643C6E3955A2173B37BA',
            'DNT': '1',
            'Origin': 'http://seat1.lib.hlju.edu.cn',
            'Referer': 'http://seat1.lib.hlju.edu.cn/login?targetUri=%2F',
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36",
            # "Cookie": self.ck
        }


    def downloadCaptcha(self):
        isDownOk = False
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
                isDownOk = True
            else:
                print('ERROR: captcha_url is NULL')
        except Exception as err:
            print("[-] ERROR: save captcha error: %s", err)
            isDownOk = False
        return isDownOk

    def login(self, username, password):
        post_data = {
            'SYNCHRONIZER_TOKEN': self.token,
            'SYNCHRONIZER_URI': '/login',
            'username': username,
            'password': password,
            'captcha': input("请输入验证码\n")
        }
        resp = self.s.get(url=login_url, data=post_data, headers=self.headers, allow_redirects=False)
        # resp = self.s.post(url=login_url, data=post_data, headers=self.headers)
        print(resp.headers)
        print(resp.url)
        print(resp.status_code)
        result = resp.content.decode('utf-8')
        print("result--->", result)
        root = etree.HTML(result)
        title = root.xpath("//title")[0].text
        # soup = BeautifulSoup(result, "html.parser")
        # title = soup.title.text
        # print("title", title)
        if (title == "自选座位 :: 图书馆预约系统"):
            return True
        else:
            return False

if __name__ == '__main__':

    ###自定义信息
    h = HljuLibrarySeat()
    print(h.downloadCaptcha())
    print(h.login(username=username, password=password))