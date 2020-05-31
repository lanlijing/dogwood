# -*- coding: UTF-8 -*-

import copy

from dogwood.core.logger import Logger
from dogwood.core.network.sock_id import SockId
from dogwood.core.base_packet import BasePacket, PacketSplit

class NetSplitError(Exception):
    def __init__(self, msg):
        self.msg = msg
        
    def __str__(self):
        return 'NetSplitError: {}'.format(self.msg)

class NetSplitMgr:
    __slots__ = ('split_dict')
    def __init__(self):
        self.split_dict = {}
        
    def add_split(self, sock_id, split):
        if sock_id in self.split_dict.keys():
            raise NetSplitError('error, sock_id exist.{}'.format(sock_id))
            return
        
        self.split_dict[sock_id] = split
    
    def remove_split(self, sid):
        if not sid in self.split_dict.keys():
            Logger().warning('remove_split:sid not exist.{}'.format(sid))
            return
        del self.split_dict[sid]
        
    def deal_with_bytes(self, sid, bys):
        if not sid in self.split_dict.keys():
            Logger().warning('deal_with_bytes:sid not exist.{}'.format(sid))
            return sid, []
        ret_list = []
        try:
            split = self.split_dict[sid]
            ret_list = split.deal_with_bytes(bys)
        except Exception as e:
            raise e                                         #留给调用者处理
        return sid, ret_list
    
    
class NetPacketSplit:
    __slots__ = ('sock_id', 'pack_split')
    def __init__(self, sock_id):
        self.sock_id = copy.deepcopy(sock_id)
        self.pack_split = PacketSplit()
        
    def deal_with_bytes(self, bys):
        ret_list = []
        if self.pack_split.push_data(bys):
            try:
                ret_list = self.pack_split.split()
            except Exception as e:
                raise e                                         #留给调用者处理
        return ret_list
            
        
    