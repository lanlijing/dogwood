# -*- coding: UTF-8 -*-

import configparser

from dogwood.core.meta_class import Singleton

# config_parser的config.options(section)方法得到小写的字符串所以重写方法optionxform

class NewConfigParser(configparser.ConfigParser):
    def optionxform(self, str_option):
        return str_option
    
class IniConfig(metaclass=Singleton):
    def __init__(self):
        self.cfg_dic = {}
        self.load_cfg()

    def load_cfg(self):
        config = NewConfigParser()
        config.read(r"./config/config.ini")
        for section in config.sections():
            self.cfg_dic[section] = {}
            for option in config.options(section):
                str_read = config.get(section, option)
                if str_read[0] == '"':
                    str_read = str_read[1:-1]
                self.cfg_dic[section][option] = str_read

    def get_value(self, section, option):
        if section in self.cfg_dic.keys() and option in self.cfg_dic[section].keys():
            return self.cfg_dic[section][option]
        return None