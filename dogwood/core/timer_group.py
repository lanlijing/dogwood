# -*- coding: UTF-8 -*-

from dogwood.core.helper import Helper
from dogwood.core.logger import Logger
from dogwood.core.meta_class import Singleton
from dogwood.core.lock import MyLock

class TimerEvent:
    '''Timer事件类,可指定执行次数'''
    __slots__ = ('event_name', 'ticker', 'func', 'last_trigger_time', 'exe_num', 'is_end', 'exe_count')
    def __init__(self, event_name, ticker, func, exe_num):
        self.event_name = event_name        # 事件名称，唯一性
        self.ticker = ticker                # 间隔时间，单位毫秒
        self.func = func                    # timer 函数
        self.last_trigger_time = Helper.get_program_milli_second()      # 最后触发时间
        self.exe_num = exe_num                 # 执行次数, 0表示无限次数
        self.is_end = False                # 可否删除
        self.exe_count = 0                  # 执行计数
    
    def run_timer(self, now_milli):
        if self.is_end:
            return
        if (now_milli - self.last_trigger_time) >= self.ticker:
            try:
                self.func()
            except Exception as e:
                Logger().error('%s:%s:%s' % (self.event_name, repr(self.func), e))
            self.last_trigger_time = now_milli
            self.exe_count += 1
            if self.exe_num != 0 and self.exe_count >= self.exe_num:
                self.is_end = True
      
      
class TimerGroup:
    '''无做线程安全'''
    __slots__ = ('__run_dict', '__add_dict')
    def __init__(self):
        self.__run_dict = {}                  # 事件字典,以event_name为key
        self.__add_dict = {}                    # 准备排队加的字典，以event_name为key
    
    def add_timer_event(self, event_name, ticker, func, exe_num=0):
        '''添加timer事件, 返回是否成功'''
        n_exist = False
        if event_name in self.__run_dict.keys():
            n_exist = True
        if event_name in self.__add_dict.keys():
            n_exist = True
        if n_exist:
            Logger().error('event_name exist. {}'.format(event_name))
            return False
        
        timer_event = TimerEvent(event_name, ticker, func, exe_num)
        self.__add_dict[event_name] = timer_event
        return True
        
    def remove_timer_event(self, event_name):
        if event_name in self.__run_dict.keys():
            del self.__run_dict[event_name]
        if event_name in self.__add_dict.keys():
            del self.__add_dict[event_name]
        
    def run_timer(self, now_milli):
        run_arr = []
        add_arr =[]
        del_arr = []
        for v in self.__run_dict.values():
            run_arr.append(v)
        for v in self.__add_dict.values():
            add_arr.append(v)
        self.__add_dict.clear()
        
        for it in run_arr:
            it.run_timer(now_milli)
            if it.is_end:
                del_arr.append(it.event_name)
                
        for d in del_arr:
            del self.__run_dict[d]
        for a in add_arr:
            self.__run_dict[a.event_name] = a
        
        
class TimerGroupS:
    '''有做线程安全'''
    __slots__ = ('__run_dict', '__add_dict', '__run_lock', '__add_lock')
    def __init__(self):
        self.__run_dict = {}                  # 事件字典,以event_name为key
        self.__add_dict = {}                    # 准备排队加的字典，以event_name为key
        self.__run_lock = MyLock()              # 为变量__run_dict准备的锁
        self.__add_lock = MyLock()              # 为变量__add_lock准备的锁
    
    def add_timer_event(self, event_name, ticker, func, exe_num=0):
        '''添加timer事件, 返回是否成功'''
        n_exist = False
        self.__run_lock.lock()
        if event_name in self.__run_dict.keys():
            n_exist = True
        self.__run_lock.unlock()
        self.__add_lock.lock()
        if event_name in self.__add_dict.keys():
            n_exist = True
        self.__add_lock.unlock()
        if n_exist:
            Logger().error('event_name exist. {}'.format(event_name))
            return False
        
        timer_event = TimerEvent(event_name, ticker, func, exe_num)
        self.__add_lock.lock()
        self.__add_dict[event_name] = timer_event
        self.__add_lock.unlock()
        return True
        
    def remove_timer_event(self, event_name):
        self.__run_lock.lock()
        if event_name in self.__run_dict.keys():
            del self.__run_dict[event_name]
        self.__run_lock.unlock()
        
        self.__add_lock.lock()
        if event_name in self.__add_dict.keys():
            del self.__add_dict[event_name]
        self.__add_lock.unlock()
        
    def run_timer(self, now_milli):
        run_arr = []
        add_arr =[]
        del_arr = []
        self.__run_lock.lock()
        for v in self.__run_dict.values():
            run_arr.append(v)
        self.__run_lock.unlock()
        self.__add_lock.lock()
        for v in self.__add_dict.values():
            add_arr.append(v)
        self.__add_dict.clear()
        self.__add_lock.unlock()
        
        for it in run_arr:
            it.run_timer(now_milli)
            if it.is_end:
                del_arr.append(it.event_name)
                
        self.__run_lock.lock()
        for d in del_arr:
            del self.__run_dict[d]
        for a in add_arr:
            self.__run_dict[a.event_name] = a
        self.__run_lock.unlock()
        