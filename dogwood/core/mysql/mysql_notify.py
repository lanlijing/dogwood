# -*- coding: UTF-8 -*-

from enum import Enum

class MNTDef(Enum):
    ''''mysql notify 类型'''
    SELECT_ONE = 0
    SELECT_LIST = 1
    EXE_SINGLE= 2
    EXE_MULTI = 3
    INSERT_LID = 4           #插入后,需要获取最新id的
    
    REQ = 101
    RET = 102
    
    
class MySqlNotify:
    __slots__ = ('alias', 'call_id', 'ope', 'sqls', 'success', 'status', 'result')
    def __init__(self, alias, cid, ope):
        self.alias = alias
        self.call_id = cid;
        self.ope = ope
        self.sqls = []
        self.success = False
        self.status = MNTDef.REQ.value
        self.result = None
        
    def add_sql(self, sql):
        self.sqls.append(sql)