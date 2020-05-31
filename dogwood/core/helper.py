# -*- coding: UTF-8 -*-

import random
import time
import datetime
import inspect
import ctypes
import hashlib
import requests

from requests_toolbelt import MultipartEncoder
from flask import make_response
from dogwood.core.meta_class import NoInstance

class Helper(metaclass=NoInstance):
    @staticmethod
    def quit_signal():
        return 'quit'
    
    @staticmethod
    def get_program_milli_second():
        '''获取程序启动后的毫秒数'''
        current_milli_time = int(round(time.perf_counter() * 1000))
        return current_milli_time
    
    @staticmethod
    def get_program_second():
        '''获取程序启动后的秒数'''
        return int(round(time.perf_counter()))
    
    @staticmethod
    def get_time_stamp_milli_second():
        '''获取毫秒时间戳'''
        milli_time = int(round(time.time() * 1000))
        return milli_time
    
    @staticmethod
    def get_time_stamp_second():
        '''获取秒时间戳'''
        sec_time = int(round(time.time()))
        return sec_time
    
    @staticmethod
    def get_current_date():
        return time.strftime('%Y-%m-%d')
    
    @staticmethod
    def interval_now_seconds(str_ori_time):
        tm_now_obj = datetime.datetime.now()
        tm_ori_obj = datetime.datetime.strptime(str_ori_time, '%Y-%m-%d %H:%M:%S')
        d = tm_now_obj - tm_ori_obj
        return d.days*24*3600 + d.seconds # d.total_seconds() total_seconds会是小数
    
    @staticmethod
    def interval_tow_time_seconds(str_time1, str_time2):
        tm_time1 = datetime.datetime.strptime(str_time1, '%Y-%m-%d %H:%M:%S')
        tm_time2 = datetime.datetime.strptime(str_time2, '%Y-%m-%d %H:%M:%S')
        d = tm_time2 - tm_time1
        return d.days*24*3600 + d.seconds # d.total_seconds()
    
    @staticmethod
    def get_now_timer_str(fmt_str='%Y-%m-%d %H:%M:%S'):
        tm_now_obj = datetime.datetime.now()
        str_ret = tm_now_obj.strftime(fmt_str)
        return str_ret
    
    @staticmethod
    def weight_random(arr_wgt):
        if len(arr_wgt) <= 0:
            return -1
        sum_weight = 0
        for val in arr_wgt:
            sum_weight += val
        rd = random.randint(0, sum_weight)
        sum_weight = 0
        index = 0
        for i in range (0, len(arr_wgt)):
            sum_weight += arr_wgt[i]
            if rd <= sum_weight:
                index = i 
                break
        return index
    
    @staticmethod
    def __async_raise(tid, exc_type):
        tid = ctypes.c_long(tid)
        if not inspect.isclass(exc_type):
            exc_type = type(exc_type)
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exc_type))
        if res == 0:
            raise ValueError('invalid thread id')
        elif res != 1:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
            raise SystemError('PyThreadState_SetAsyncExc failed')
    
    @staticmethod
    def stop_thread(thread):
        cls.__async_raise(thread.ident, SystemExit)
        
    @staticmethod
    def create_uuid():
        m = hashlib.md5()
        m.update(bytes(str(time.perf_counter()),encoding='UTF-8'))
        return m.hexdigest()    
        
    @staticmethod
    def json_response(json_data):
        # 解决跨域请求问题
        response = make_response(json_data)
        response.headers['Access-Control-Allow-Origin']  = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST'
        response.headers['Access-Control-Max-Age']       = '1000'
    
        return response
    
    '''
            注意,data_dict的所有key和value都要字符串型
    return: json 字符串
    '''
    @staticmethod
    def post_form_data_no_file(url, data_dict):
        multipart_encoder = MultipartEncoder(fields=data_dict)
        r = requests.post(url, data=multipart_encoder, headers={'Content-Type': multipart_encoder.content_type})
        return r.text