# -*- coding: UTF-8 -*-

import queue
from multiprocessing import Event as PeEvent

from dogwood.core.mysql.mysql_process import MySqlProcess

class MySqlMonitor:
    __slots__ = ('_game_main_thread', '_proc_dict', '_index_dict', '_result_queue')
    def __init__(self, game_main_thread):
        self._game_main_thread = game_main_thread   # 游戏主线程,用于调用协程
        self._proc_dict = {}                        #key为alias,value是mysql进程数组
        self._index_dict = {}                       # 执行的索引数组
        self._result_queue = queue.Queue()          # 返回结果的队列
    
    def add_mysql_process(self, alias, num, mysql_host, mysql_port, mysql_user, mysql_pwd, mysql_db, charset='utf8mb4'):
        proc_list = []
        for i in range(num):
            event = PeEvent()
            proc = MySqlProcess('{}_{}'.format(alias, i), event, alias, mysql_host, mysql_port, mysql_user, mysql_pwd, mysql_db, charset)
            proc_list.append(proc)
            proc.start()
        self._proc_dict[alias] = proc_list
        self._index_dict[alias] = 0
        
    def remove_mysql_process(self, alias):
        if alias in self._proc_dict.keys():
            proc_list = self._proc_dict[alias]
            for proc in proc_list:
                proc.quit()
                proc.join()
            del self._proc_dict[alias]
        if alias in self._index_dict.keys():
            del self._index_dict[alias]
            
    def close_all(self):
        for k, proc_list in self._proc_dict.items():
            for proc in proc_list:
                proc.quit()
                proc.join()
        self._proc_dict.clear()
        self._index_dict.clear()
        
    def push_notify(self, notify):
        if notify.alias in self._proc_dict.keys():
            proc_list = self._proc_dict[notify.alias]
            if self._index_dict[notify.alias] >= len(proc_list):
                self._index_dict[notify.alias] = 0
            proc = proc_list[self._index_dict[notify.alias]]
            proc.push_msg(notify)
            self._index_dict[notify.alias] += 1
            
    def run_timer(self, now_milli):
        for k, proc_list in self._proc_dict.items():
            for proc in proc_list:
                while not proc.pull_msg_empty():
                    msg_obj = proc.pull_msg()
                    self._result_queue.put(msg_obj)
        while not self._result_queue.empty():
            msg_obj = self._result_queue.get_nowait()
            self.process_result(msg_obj)

    def process_result(self, notify):
        self._game_main_thread.push_corou_msg(notify.call_id, notify)
        