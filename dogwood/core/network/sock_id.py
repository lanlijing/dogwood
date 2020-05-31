# -*- coding: UTF-8 -*-

import random

class SockId:
    __slots__ = ('net_id', 'addr', 'port', 'rnd_int')
    '''用于表示来自客户端连接的类'''
    def __init__(self, net_id):
        self.net_id = net_id        # 可能同一个程序里，有不同的网络监控
        self.addr = ''
        self.port = 0
        self.rnd_int = random.randint(100000, 10000000)     #四个属性都相等，就是同一个socket，随机数可能重复，但四个属性需要都相等的情况下，重复概率几乎不可能
        
    def set_data(self, net_addr):
        self.addr = net_addr[0]
        self.port = net_addr[1]
        
    def __eq__(self, other):                                    # 要作为字典的key, 必须__eq__和__hash__同时实现
        return self.net_id == other.net_id and self.addr == other.addr and self.port == other.port and self.rnd_int == other.rnd_int
    
    def __hash__(self):
        return hash(self.net_id) ^ hash(self.addr) ^ hash(self.port) ^ hash(self.rnd_int)
    
    def __str__(self):
        return ('{}:{}:{}:{}'.format(self.net_id, self.addr, self.port, self.rnd_int))