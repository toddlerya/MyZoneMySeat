#!/usr/bin/env python
# coding: utf-8
# @Time     : 2018/10/24 21:28
# @Author   : toddlerya
# @FileName : send_mail.py
# @Project  : MyZoneMySeat

# from __future__ import unicode_literals


import socket
import smtplib
from email.mime.text import MIMEText
from base_lib import Logger, my_log_file
from hlju_lib_config import log_level
from sec import mail_host, mail_port, mail_user, mail_password, receivers


def get_host_ip():
    """
    查询本机ip地址
    :return: ip
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip


def mail(subject='', content=''):
    host_ip = get_host_ip()
    log = Logger(log_name=my_log_file(__file__), level=log_level,
                 fmt='%(asctime)s - [line:%(lineno)d] - %(levelname)s: %(message)s')
    message = MIMEText(content, 'plain', 'utf-8')
    message['Subject'] = 'MyZoneMySeat-{S}-来自<={H}=>哨兵的情报'.format(H=host_ip, S=subject)
    message['From'] = mail_user
    message['To'] = "; ".join(receivers)
    try:
        smtp_cli = smtplib.SMTP_SSL(host=mail_host, port=mail_port)
        smtp_cli.login(mail_user, mail_password)
        smtp_cli.sendmail(mail_user, receivers, message.as_string())
        smtp_cli.quit()
        log.logger.info('发送邮件成功! {S}: {C}'.format(S=subject, C=content))
    except Exception as err:
        log.logger.error('发送邮件失败! 报错信息: {E}'.format(E=err))


if __name__ == '__main__':
    print(get_host_ip())
    mail('test', 'just a test')
