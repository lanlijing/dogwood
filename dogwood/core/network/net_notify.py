# -*- coding: UTF-8 -*-

from enum import Enum
from dogwood.core.network.sock_id import SockId
import copy
  
class NetNotify:
    __slots__ = ('sid', 'ope', 'buf')
    def __init__(self, sid, ope, buf=None):
        self.sid = copy.deepcopy(sid)
        self.ope = ope
        self.buf = buf