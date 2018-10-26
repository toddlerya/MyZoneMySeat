#!/usr/bin/env python
# coding: utf-8
# @Time     : 2018/10/24 21:28
# @Author   : toddlerya
# @FileName : send_mail.py
# @Project  : MyZoneMySeat

# from __future__ import unicode_literals

import smtplib
from email.mime.text import MIMEText
from base_lib import Logger, my_log_file
from hlju_lib_config import log_level
from sec import mail_host, mail_port, mail_user, mail_password, receivers

sender = 'toddlerya@sina.com'


def mail(subject='', content=''):
    log = Logger(log_name=my_log_file(__file__), level=log_level,
                 fmt='%(asctime)s - [line:%(lineno)d] - %(levelname)s: %(message)s')
    message = MIMEText(content, 'plain', 'utf-8')
    message['Subject'] = 'MyZoneMySeat-预定信息-{}'.format(subject)
    message['From'] = sender
    message['To'] = "; ".join(receivers)
    try:
        smtp_cli = smtplib.SMTP()
        smtp_cli.connect(host=mail_host, port=mail_port)
        smtp_cli.login(mail_user, mail_password)
        smtp_cli.sendmail(sender, receivers, message.as_string())
        smtp_cli.quit()
        log.logger.info('发送邮件成功! {S}: {C}'.format(S=subject, C=content))
    except Exception as err:
        log.logger.error('发送邮件失败! 报错信息: {E}'.format(E=err))


if __name__ == '__main__':
    mail('test', 'just a test')
