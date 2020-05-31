# -*- coding: UTF-8 -*-

import os

from dogwood.core.base_process import BaseProcess
from dogwood.core.logger import Logger
from dogwood.core.helper import Helper
from dogwood.core.timer_group import TimerGroup
from dogwood.core.mysql.mysql_operate import MySqlOperate, MySqlOpeDef
from dogwood.core.mysql.mysql_notify import MNTDef, MySqlNotify

class MySqlProcess(BaseProcess):
    __slots__ = ('__alias', 'mysql_op', '__time_group', '__mysql_host', '__mysql_port', '__mysql_user', '__mysql_pwd', '__mysql_db', '__charset', '__last_reconn')
    def __init__(self, log_name, event, alias, mysql_host, mysql_port, mysql_user, mysql_pwd, mysql_db, charset='utf8mb4'):
        super().__init__(log_name, event)
        self.__alias = alias
        self.__time_group = TimerGroup()
        self.__mysql_host = mysql_host
        self.__mysql_port = mysql_port
        self.__mysql_user = mysql_user
        self.__mysql_pwd = mysql_pwd
        self.__mysql_db = mysql_db
        self.__charset = charset
        self.__last_reconn = 0
        
    def process_init(self):
        self.mysql_op = MySqlOperate(self.__alias, self.__mysql_host, self.__mysql_port, self.__mysql_user, 
                                      self.__mysql_pwd, self.__mysql_db, self.__charset)        # 在另一个进程里创建,否则就属于调用者进程了
        self.mysql_op.open_mysql()
        if self.mysql_op.is_open:
            self.__time_group.add_timer_event('keep_alive', MySqlOpeDef.KEEP_ALIVE_INTERVAL.value, self.keep_alive)
            
    def process_end(self):                      
        if self.mysql_op.is_open:
            self.mysql_op.close_mysql()
        
    def run_frame(self, now_milli):
        if self.mysql_op.is_open is not True:           # 中途数据库断开连接
            if (now_milli - self.__last_reconn) > 60000:         # 每60秒重连一次
                self.mysql_op.open_mysql()
                self.__last_reconn = now_milli
        notify_list = []
        while not self._in_queue.empty():
            nf = self._in_queue.get_nowait()
            notify_list.append(nf)
        for nf in notify_list:
            if type(nf) is str and nf.lower() == Helper.quit_signal():
                self._run_flag = False
                continue
            if not type(nf) is MySqlNotify:
                Logger().warning('{}:MySqlProcess.not mysqlnotify:{} pid:{}'.format(self.__alias, nf, os.getpid()))
                continue
            if nf.status != MNTDef.REQ.value:
                Logger().warning('{}:MySqlProcess.mysqlnotify status error:{} pid:{}'.format(self.__alias, nf, os.getpid()))
                continue
            if nf.ope == MNTDef.SELECT_ONE.value:
                sql = nf.sqls[0]
                nf.result = self.mysql_op.select_one(sql)
                nf.success = (nf.result != None)
            elif nf.ope == MNTDef.SELECT_LIST.value:
                sql = nf.sqls[0]
                nf.result = self.mysql_op.select_list(sql)
                nf.success = (nf.result != None)
            elif nf.ope == MNTDef.INSERT_LID.value:
                sql = nf.sqls[0]
                nf.success, nf.result = self.mysql_op.insert_last_id(sql)
            elif nf.ope == MNTDef.EXE_SINGLE.value:
                sql = nf.sqls[0]
                nf.success, nf.result = self.mysql_op.execute_single_sql(sql)
            elif nf.ope == MNTDef.EXE_MULTI.value:
                sql_list = nf.sqls
                nf.success = self.mysql_op.execute_multi_sql(sql_list)
            nf.status = MNTDef.RET.value
            self._out_queue.put(nf)
        
        self.__time_group.run_timer(Helper.get_program_milli_second())
            
    def keep_alive(self):
        self.mysql_op.keep_alive()
        
    def quit(self):
        self._in_queue.put(Helper.quit_signal())
                
    @property
    def alias(self):
        return self.__alias
                
            
         
        
