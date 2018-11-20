#!/usr/bin/env python
# coding: utf-8
# @Time     : 2018/10/22 21:59
# @Author   : toddlerya
# @FileName : base_lib.py
# @Project  : MyZoneMySeat

# from __future__ import unicode_literals

import os
import logging
from logging import handlers


class Logger(object):
    level_map = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL
    }

    def __init__(self, log_name, level='info', when='D', back_count=3,
                 fmt='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s'):
        self.logger = logging.getLogger(log_name)
        format_str = logging.Formatter(fmt)
        self.logger.setLevel(self.level_map.get(level))
        sh = logging.StreamHandler()  # 输出到控制台
        sh.setFormatter(format_str)  # 设置控制台输出格式
        th = handlers.TimedRotatingFileHandler(filename=log_name, when=when, backupCount=back_count,
                                               encoding='utf-8')  # 按照时间自动分割日志文件
        # 实例化TimedRotatingFileHandler
        # interval是时间间隔，backupCount是备份文件的个数，如果超过这个个数，就会自动删除，when是间隔的时间单位，单位有以下几种：
        # S 秒
        # M 分
        # H 小时、
        # D 天、
        # W 每星期（interval==0时代表星期一）
        # midnight 每天凌晨
        th.setFormatter(format_str)
        self.logger.addHandler(sh)
        self.logger.addHandler(th)


def re_joint_dir_by_os(input_path):
    """
    根据系统来判断文件夹的分隔符来拼接目录的路径
    :param input_path 为需要拼接的目录参数；example: .|dir_a|dir_b|...|dir_n
    :return jointed_dir 根据系统判断后拼接后的目录
            example: linux: ./dir_a/dir_b/.../dir_n
                     windows: .\dir_a\dir_b\...\dir_n
    """
    try:
        splited_dir = input_path.split('|')
        jointed_dir = os.path.sep.join(splited_dir)
        return jointed_dir
    except BaseException as e:
        raise e


def my_log_file(_file_name):
    return re_joint_dir_by_os("logs|{}".format(os.path.basename(_file_name)[:-3] + '.log'))


if __name__ == '__main__':
    print(os.path.basename(__file__)[:-3] + '.log')
    print(my_log_file())