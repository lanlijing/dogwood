# -*- coding: UTF-8 -*-

import logging
from logging import handlers
import os
import sys

'''
四个日志等级,debug,info,waring,error.四种都会在console窗口上显示
只有waring, error会写入日志文件
log_init在一个进程里只能全局执行一次
'''
def LogInit(app_name):
    #logging config
    global __LOGGER
    real_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
    file_name = real_dir + (r'/log/%s.log' % app_name)
    log_path = os.path.dirname(file_name)
    if os.path.exists(log_path) == False:
        os.makedirs(log_path)
    format_obj = logging.Formatter('%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')
    sh = logging.StreamHandler()
    sh.setFormatter(format_obj)
    th = handlers.TimedRotatingFileHandler(filename=file_name, when='D', backupCount=3,encoding='utf-8')
    th.setFormatter(format_obj)
    th.setLevel(logging.WARNING)
    __LOGGER = logging.getLogger(file_name)
    __LOGGER.setLevel(logging.INFO)
    __LOGGER.addHandler(sh)
    __LOGGER.addHandler(th)

def Logger():
    return __LOGGER