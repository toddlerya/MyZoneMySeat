#!/usr/bin/env python
# coding: utf-8
# @Time     : 2018/10/16 21:31
# @Author   : guo qun
# @FileName : hlju_lib_config.py
# @Project  : MyZoneMySeat

index_url = "http://seat1.lib.hlju.edu.cn/login?targetUri=%2F"
login_url = "http://seat1.lib.hlju.edu.cn/auth/signIn"
captcha_url = 'http://seat1.lib.hlju.edu.cn/simpleCaptcha/captcha'

# 查询空座
free_book_query_url = 'http://seat1.lib.hlju.edu.cn/freeBook/ajaxSearch'

# 预约座位
book_seat_self_url = 'http://seat1.lib.hlju.edu.cn/selfRes'

# 查看场馆座位信息
room_seat_map_url = 'http://seat1.lib.hlju.edu.cn/mapBook/getSeatsByRoom'

booking_url_01 = "http://seat1.lib.hlju.edu.cn"
# 布局选座模式
booking_url_02 = "http://seat1.lib.hlju.edu.cn/map"
# 常用座位模式
booking_url_03 = "http://seat1.lib.hlju.edu.cn/freeBook/fav"

building_room_dict = {
    # 新馆
    '1': {'16', '21', '22'},
    # 老馆
    '2': {'26', '27', '28', '29', '30', '31', '32'}
}

room_desc_dict = {
    # 新馆
    '16': '二楼大厅-预约',
    '21': '三楼三角区-预约',
    '22': '四楼三角区-预约',
    # 老馆
    '26': '一楼自习室-预约',
    '27': '三楼小自习室-预约',
    '28': '三楼原电阅室-预约',
    '29': '三楼自习室-预约',
    '30': '三楼走廊-预约',
    '31': '四层自习室-预约',
    '32': '四楼走廊-预约'
}
