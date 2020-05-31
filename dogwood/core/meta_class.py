# -*- coding: UTF-8 -*-

class Singleton(type):
    def __init__(cls, *args, **kwargs):
        cls.__instance = None
        type.__init__(cls, *args, **kwargs)
        
    def __call__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = type.__call__(cls, *args, **kwargs)
        return cls.__instance

    
class NoInstance(type):
    def __call__(cls, *args, **kwargs):
        raise TypeError('cannot instantiate directly')
    
    
class DeriveSingleton:
    __class_name = {}
    
    @classmethod
    def check_exist(cls, father_name, child_name):
        if not father_name in cls.__class_name.keys():
            cls.__class_name[father_name] = child_name
        else:
            exist_child = cls.__class_name[father_name]
            if exist_child != child_name:
                raise TypeError('father and all child only one')