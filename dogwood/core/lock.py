# -*- coding: UTF-8 -*-

from threading import Lock

class MyLock:
    __slots__ = ('__lock')
    def __init__(self):
        self.__lock = Lock()
        
    def lock(self):
        self.__lock.acquire()
        
    def unlock(self):
        self.__lock.release()