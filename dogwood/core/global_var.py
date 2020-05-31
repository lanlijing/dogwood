# -*- coding: UTF-8 -*-

from dogwood.core.meta_class import NoInstance

class GlobalVar(metaclass=NoInstance):
    _global_dict ={}
    
    @classmethod
    def set_value(cls, name, value):
        cls._global_dict[name] = value
        
    @classmethod
    def get_value(cls, name, def_value=None):
        return cls._global_dict.get(name, def_value)
