# -*- coding: UTF-8 -*-

import os
from enum import Enum

import pymysql
from dogwood.core.helper import Helper
from dogwood.core.logger import Logger

class MySqlOpeDef(Enum):
    KEEP_ALIVE_INTERVAL = 7200000           # 每2小时向mysql数据库发一次'select 1',因为mysql超过8小时没操作，会断开

class MySqlOperate:
    __slots__ = ('__alias', '__is_open', '__conn', '__cursor', '__mysql_host', '__mysql_port', '__mysql_user', '__mysql_pwd', '__mysql_db', '__charset')
    def __init__(self, alias, mysql_host, mysql_port, mysql_user, mysql_pwd, mysql_db, charset='utf8mb4'):
        self.__alias = alias           #用来标识每一个mysql的连接      
        self.__is_open = False       # 是否已经打开数据库连接
                
        self.__conn = None
        self.__cursor = None
        
        self.__mysql_host = mysql_host
        self.__mysql_port = mysql_port
        self.__mysql_user = mysql_user
        self.__mysql_pwd = mysql_pwd
        self.__mysql_db = mysql_db
        self.__charset = charset
        
    @property
    def is_open(self):
        return self.__is_open
        
    def open_mysql(self):       # 连接mysql        
        try:
            self.__conn = pymysql.connect(host=self.__mysql_host,port=self.__mysql_port,user=self.__mysql_user,passwd=self.__mysql_pwd,db=self.__mysql_db,charset=self.__charset)
            self.__is_open = True
            Logger().info('{}:mysql::conn_mysql: success. pid:{}'.format(self.__alias, os.getpid()))
        except pymysql.err.OperationalError as e:
            Logger().info('{}:mysql::conn_mysql:{} pid:{}'.format(self.__alias, e, os.getpid()))
            return False
        self.__cursor = self.__conn.cursor(pymysql.cursors.DictCursor)
        return True

    def close_mysql(self):
        if self.__is_open:
            self.__cursor.close()
            self.__conn.close()
        self.__is_open = False
    
    def keep_alive(self):       # 每2小时向mysql数据库发一次'select 1',因为mysql超过8小时没操作，会断开
        self.select_one('select 1')
        Logger().info('{}:mysql::keep_alive {} pid:{}'.format(self.__alias, Helper.get_program_milli_second(), os.getpid()))

    def select_list(self, str_sql):     # 输入一个select的sql语句，返回多个记录集
        try:
            self.__cursor.execute(str_sql)
            record_lst = self.__cursor.fetchall()
            self.__conn.commit()
            return record_lst
        except Exception as e:            
            Logger().info('{}:mysql::select_list:error:{},sql:{},pid:{}'.format(self.__alias, e, str_sql, os.getpid()))
            self.check_except_close(e)
            return None

    def select_one(self, str_sql):              # 输入一个select的sql语句，只返回一个记录
        try:
            self.__cursor.execute(str_sql)
            record = self.__cursor.fetchone()
            self.__conn.commit()
            return record
        except Exception as e:            
            Logger().info('{}:mysql::select_one:error:{},sql:{},pid:{}'.format(self.__alias, e, str_sql, os.getpid()))
            self.check_except_close(e)
            return None

    def execute_single_sql(self, sql_str):         # 执行单个sql语句(update或delete)
        try:
            self.__cursor.execute(sql_str)
            rowcount = self.__cursor.rowcount
            self.__conn.commit()
            return True, rowcount
        except Exception as e:            
            self.__conn.rollback()
            Logger().info('{}:mysql::execute_single_sql:error:{},sql:{},pid:{}'.format(self.__alias, e, sql_str, os.getpid()))
            self.check_except_close(e)
            return False, 0

    def execute_multi_sql(self, sql_str_list):         # 执行多个sql语句，只有都成功了才会提交
        try:
            if len(sql_str_list) == 0:
                Logger().info("{}:mysql::execute_multi_sql error sql_str_list is empty.pid:{}".format(self.__alias, os.getpid()))
                return False
            for sql_str in sql_str_list:
                self.__cursor.execute(sql_str)
            self.__conn.commit()
            return True
        except Exception as e:
            self.__conn.rollback()
            Logger().info('{}:mysql::execute_multi_sql:error:{},sql:{},pid:{}'.format(self.__alias, e, str(sql_str_list), os.getpid()))  
            self.check_except_close(e)            
            return False
        
    def insert_last_id(self, insert_sql):               # 执行insert的sql语句,并且取得最后的id
        try:
            self.__cursor.execute(insert_sql)
            last_id = self.__cursor.lastrowid
            self.__conn.commit()
            return True, last_id
        except Exception as e:            
            self.__conn.rollback()
            Logger().info('{}:mysql::execute_single_sql:error:{},sql:{},pid:{}'.format(self.__alias, e, insert_sql, os.getpid()))
            self.check_except_close(e)
            return False, None
        
    def check_except_close(self, e):    
        if type(e) is pymysql.err.OperationalError or type(e) is ConnectionResetError:
            self.close_mysql()
            Logger().warning('{}:mysql 关闭,pid:{}'.format(self.__alias, os.getpid()))