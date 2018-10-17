#!/usr/bin/env python
# coding: utf-8
# @Time     : 2018/10/17 22:59
# @Author   : guo qun
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

    def query_sql(self, sql):
        try:
            self.cur.execute(sql)
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
    pass
