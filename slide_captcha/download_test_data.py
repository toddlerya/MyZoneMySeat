#!/usr/bin/env python
# coding: utf-8

import requests
import codecs
import json
import time
import random

test_url = 'http://seat1.lib.hlju.edu.cn:28088/verifycode'

headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            "User-Agent": 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36',
        }


with codecs.open('test_data/verify_code_resp.txt', 'a+', 'utf-8') as f:
    all_json = list()
    for i in range(8):
        resp = requests.get(test_url, headers=headers)
        _json = resp.json()
        print(_json)
        json.dump(_json, f)
        f.write('\n')