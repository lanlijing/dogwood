# -*- coding: UTF-8 -*-

from enum import Enum

class NeTDef(Enum):
    '''netnotify type'''
    SEND = 0
    RECV = 1
    CONNECT = 2         # 不管是作为服务端还是客户端,都发这个消息
    DISCONNECT = 3       # 不管是主动还是被动,都向逻辑线程使用这个定义
    
    SERVER_CLOSE = 4            # 服务端主动关闭一个客户端
    
    CLIENT_CREATE = 5          # 客户端创建一个连接
    CLIENT_CLOSE = 6            # 客户端关闭一个连接
    CLIENT_CONNECT_FAIL = 7     # 作为客户端,连远程服务器失败
    
    LISTEN_NUM = 100                  # 监听一次数量
    SELECT_TIME_OUT = 0.016           # select timeout. 16毫秒,每秒60帧
    MAX_TRANSMIT_ONE_FRAME = 1024       # 每一帧发送的最大数量包,发不了的下一帧
    
    WINDOWS_SELECT_MAX = 502            # python的selectors在windows下使用的是select,最大只支持509.
                                        # ValueError: too many file descriptors in select()