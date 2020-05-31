# -*- coding: UTF-8 -*-

import os
import json
import sys

from dogwood.core.meta_class import Singleton

class JsonConfig(metaclass=Singleton):
    
    def __init__(self):
        self.config_dict = {}

    def load_json_config(self, cfg_fl):
        real_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
        json_file = real_dir + r'/' + cfg_fl
        fl = open(json_file, encoding='UTF-8')
        cont = fl.read()
        fl.close()
        self.config_dict = json.loads(cont)
    
    def __setitem__(self, key, value):
        self.config_dict[key] = value
    
    def __getitem__(self, key):
        return self.config_dict[key]