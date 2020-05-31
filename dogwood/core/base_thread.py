# -*- coding: UTF-8 -*-

import threading
import time
import queue
import traceback
import types
from enum import Enum

from dogwood.core.helper import Helper
from dogwood.core.logger import Logger
from dogwood.core.timer_group import TimerGroup

class CoroutineOpe(Enum):
    COROUTINE_ADD = 0               # 增加一个协程
    COROUTINE_PUSH_MSG = 1          # 往协程里写入消息
    

class CoroutineNotify:
    __slots__ = ('ope', 'cid', 'obj')
    def __init__(self, ope, cid, obj):
        self.ope = ope                  # 操作类型, 对应CoroutineOpe类
        self.cid = cid                  # 协程id
        self.obj = obj                  # add时，是迭代器函数,push时,是msg


class BaseThread(threading.Thread):
    __slots__ = ('__event', '__frame_min_time', '__frame_warn_time', '__frame_abort_time', '_msg_queue',  
                 '_timer_group', '_corou_notify_queue', '__corou_tick', '__corou_dict')
    def __init__(self, event):
        super().__init__()
        self.__event = event
        self.__frame_min_time = 2                   # 最小帧时间, 默认2毫秒.当一帧时间消耗不足这个数字时，会Sleep这个数字减去消耗
        self.__frame_warn_time = 1000               # 当一帧消耗时间大于这个数字时，会打印警告.默认为1000毫秒
        self.__frame_abort_time = 30000             # 当一帧消耗时间大于这个数字时，会放弃处理剩下的消息.默认为30秒
        self._msg_queue = queue.Queue()            # 消息队列,注意这里用了queue.Queue,不是multiprocessing.Queue,
                                                    #一是为了效率，二是有清空函数self.msg_queue.queue.clear(),线程安全
        self._timer_group = TimerGroup()            # 计时函数集合
        self._corou_notify_queue = queue.Queue()    # 协程相关的消息队列
        self.__corou_tick = 1000                    # 假定每天消耗500万个，消耗到50亿需要1000天，服务器不太可能连续运行1000天
        self.__corou_dict = {}                      # 字典，key为cid, value是迭代器函数
        
        
    def run(self):
        self.thread_init()
        self.__event.set()
        now_milli = Helper.get_program_milli_second()
        last_milli = now_milli
        tick_milli = 0
        cls_name = self.__class__.__name__
        while True:
            b_quit = False
            #填充消息队列 
            self.fill_msg_queue()
            temp_msg_list = []
            while not self._msg_queue.empty():
                msg_obj = self._msg_queue.get_nowait()
                temp_msg_list.append(msg_obj)
            queue_size = len(temp_msg_list)
            for msg_obj in temp_msg_list:
                if type(msg_obj) is str and msg_obj.lower() == Helper.quit_signal():        # 退出信号
                    b_quit = True
                    continue
                now_milli = Helper.get_program_milli_second()
                tick_milli = now_milli - last_milli
                if tick_milli > self.__frame_abort_time:
                    Logger().warning('{}.主循环超期严重.放弃部分消息:帧耗时:{}.消息队列大小:{}'.format(cls_name, tick_milli, queue_size))
                    break
                try:                        # 此处有了try,下级函数可以减少try
                    self.process_msg(msg_obj)
                except Exception as e:
                    traceback.print_exc()
            now_milli = Helper.get_program_milli_second()
            try:
                self.process_timer(now_milli)           # 此处有了try,下级函数可以减少try
            except Exception as e:
                traceback.print_exc()
            # 时间处理
            tick_milli = now_milli - last_milli
            last_milli = now_milli
            if tick_milli > self.__frame_warn_time:
                Logger().warning('{}.主循环线程超期:帧耗时:{}.消息队列大小:{}'.format(cls_name, tick_milli, queue_size))
            else:
                time.sleep(self.__frame_min_time / 1000)
            if b_quit:          # 退出
                break
        self.thread_quit()
                
    def thread_init(self):              # 子类选择重载
        pass
        
    def fill_msg_queue(self):           # 子类需要重载
        pass
        
    def process_msg(self, msg_obj):     # 子类需要重载,处理消息逻辑
        pass
    
    def process_timer(self, now_milli):            
        '''子类需重载,重载时需要调用super().process_timer(now_milli)'''
        self._timer_group.run_timer(now_milli)
        self._corou_timer(now_milli)
    
    def thread_quit(self):              # 子类选择继承
        pass
        
    def quit(self):
        self._msg_queue.put(Helper.quit_signal())

    ####################################################################
    # 以下是协程相关函数
    ####################################################################
    def add_corou(self, gene_func):
        if not type(gene_func) is types.GeneratorType:              # 判断类型
            Logger().warning('128099. gene_func not GeneratorType.{}'.format(type(gene_func)))
            return None
        cur_id = self.__corou_tick
        self.__corou_tick += 1
        it_obj = gene_func
        ntf = CoroutineNotify(CoroutineOpe.COROUTINE_ADD.value, cur_id, it_obj)
        self._corou_notify_queue.put(ntf)
        return cur_id
    
    def push_corou_msg(self, cid, msg):
        ntf = CoroutineNotify(CoroutineOpe.COROUTINE_PUSH_MSG.value, cid, msg)
        self._corou_notify_queue.put(ntf)
        
    def _corou_timer(self, now_milli):
        temp_ntf_list = []
        while not self._corou_notify_queue.empty():
            ntf_obj = self._corou_notify_queue.get_nowait()
            temp_ntf_list.append(ntf_obj)
        for ntf_obj in temp_ntf_list:
            if not type(ntf_obj) is CoroutineNotify:
                Logger().error('234223 ntf_obj type error.{}'.format(ntf_obj))
                continue
            if ntf_obj.ope == CoroutineOpe.COROUTINE_ADD.value:
                cid = ntf_obj.cid
                gene_obj = ntf_obj.obj
                self.__corou_dict[cid] = gene_obj
                try:
                    gene_obj.send(None)
                    gene_obj.send(cid)
                except StopIteration:
                    self._safe_del_corou_item(cid)
            elif ntf_obj.ope == CoroutineOpe.COROUTINE_PUSH_MSG.value:
                cid = ntf_obj.cid
                msg = ntf_obj.obj
                it_obj = self.__corou_dict.get(cid, None)
                if it_obj is None:
                    Logger().warning('434679 cid not in __corou_dict keys .{}'.format(cid))
                    continue
                try:
                    it_obj.send(msg)
                except StopIteration:
                    self._safe_del_corou_item(cid)
            else:
                Logger().error('531238 ntf_obj ope error.{}'.format(ntf_obj.ope))
                continue
            
    def _safe_del_corou_item(self, cid):
        if cid in self.__corou_dict.keys():
            del self.__corou_dict[cid]