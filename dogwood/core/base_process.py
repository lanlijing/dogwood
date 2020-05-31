# -*- coding: UTF-8 -*-

from multiprocessing import Process, Queue
import time
from dogwood.core.helper import Helper
from dogwood.core.logger import LogInit, Logger

class BaseProcess(Process):
    __slots__ = ('__event', '_run_flag', '__frame_min_time', '__frame_warn_time', '_log_name', '_in_queue', '_out_queue')
    def __init__(self, log_name, event):
        super().__init__()
        self.__event = event
        self.__frame_min_time = 2      # 最小间隔毫秒数,默认2毫秒.当一帧时间消耗不足这个数字时，会Sleep这个数字减去消耗
        self.__frame_warn_time = 1000         # 当一帧消耗时间大于这个数字时，会打印警告.默认为1000毫秒
        self._log_name = log_name
        self._in_queue = Queue()           # 进程间通信队列,入队列
        self._out_queue = Queue()          # 进程间通信队列,出队列
        self._run_flag = False
        
    def run(self):
        LogInit(self._log_name)                                # 不同进程,都要初始化一次
        self.process_init()
        self.__event.set()
        now_milli = Helper.get_program_milli_second()
        last_milli = now_milli
        tick_milli = 0
        self._run_flag = True
        while self._run_flag:
            now_milli = Helper.get_program_milli_second()
            self.run_frame(now_milli)
            tick_milli = now_milli - last_milli
            last_milli = now_milli
            if tick_milli > self.__frame_warn_time:
                Logger().warning('{}.Process主循环线程超期:帧耗时:{}.'.format(self._log_name, tick_milli))
            else:
                time.sleep(self.__frame_min_time / 1000)
        self.process_end()
               
    def process_init(self):                     
        '''子类需重载'''
        pass
    
    def run_frame(self, now_milli): 
        '''子类需重载'''                      
        pass
    
    def process_end(self):                      
        '''子类需重载'''
        pass
        
    def push_msg(self, msg):
        self._in_queue.put(msg)
    
    def pull_msg_empty(self):
        return self._out_queue.empty()
    
    def pull_msg(self):
        return self._out_queue.get_nowait()
