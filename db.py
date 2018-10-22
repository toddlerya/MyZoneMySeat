#!/usr/bin/env python
# coding: utf-8
# @Time     : 2018/10/17 22:59
# @Author   : toddlerya
# @FileName : db.py.py
# @Project  : MyZoneMySeat

import sqlite3

class SeatDB(object):
    def __init__(self):
        self.db_name = "seat.db"
        self.conn = sqlite3.connect(self.db_name)
        self.cur = self.conn.cursor()

    def __del__(self):
        self.cur.close()
        self.conn.close()

    def init_seat_info_tb(self):
        init_sql = ('\n'
                    '        CREATE TABLE IF NOT EXISTS seat_info (\n'
                    '          id INTEGER PRIMARY KEY AUTOINCREMENT,\n'
                    '          seat_id VARCHAR NOT NULL,\n'
                    '          seat_number VARCHAR NOT NULL,\n'
                    '          seat_room VARCHAR NOT NULL\n'
                    '        )\n'
                    '        ')
        create_index_sql = "CREATE UNIQUE INDEX [seat_index] ON [seat_info] ([seat_id], [seat_number], [seat_room]);"
        self.cur.execute(init_sql)
        try:
            self.cur.execute(create_index_sql)
        except Exception as err:
            print(err)
        self.conn.commit()

    def init_building_room_map(self):
        '''
        场馆和房间对应关系
        :return:
        '''
        pass

    def query_sql(self, sql, *args):
        try:
            self.cur.execute(sql, args)
        except Exception as err:
            print("[-] 执行查询SQL失败: {}".format(err))
        else:
            return self.cur.fetchall()

    def load_seat_info(self, load_data):
        load_sql = "INSERT OR REPLACE INTO seat_info (seat_id, seat_number, seat_room) VALUES (?, ?, ?)"
        try:
            self.cur.executemany(load_sql, load_data)
        except Exception as err:
            print("[-] 采集数据库入库失败: {}".format(err))
        else:
            self.conn.commit()


if __name__ == '__main__':
    sd = SeatDB()
    print('总计爬取%d座位' % sd.query_sql("SELECT count(1) FROM seat_info")[0][0])
    # print('三楼原电阅室-预约', sd.query_sql("SELECT count(1) FROM seat_info WHERE seat_room = '三楼原电阅室-预约'"))
    ss = sd.query_sql("SELECT count(seat_id) as sn, seat_room FROM seat_info GROUP BY seat_room ORDER BY sn DESC")
    for s in ss:
        print(s)

    # where_condition = "seat_room IN ('三楼自习室-预约', '三楼原电阅室-预约')"
    # goal_seats = sd.query_sql(
    #     "SELECT seat_id, seat_number, seat_room FROM seat_info WHERE {W_C} ORDER BY seat_id DESC".format(W_C=where_condition))

    goal_room = ['三楼自习室-预约', '三楼原电阅室-预约']
    goal_room = []
    if goal_room:
        where_condition = "WHERE seat_room IN ({C})".format(C=",".join([repr(ele) for ele in goal_room]))
        goal_seats = sd.query_sql(
            "SELECT seat_id, seat_number, seat_room FROM seat_info {W_C} ORDER BY seat_number DESC".format(
                W_C=where_condition))
    else:
        goal_seats = sd.query_sql("SELECT seat_id, seat_number, seat_room FROM seat_info ORDER BY seat_number DESC")
    for seat in goal_seats:
        print(seat)
        break