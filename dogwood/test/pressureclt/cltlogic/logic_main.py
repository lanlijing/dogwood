# -*- coding: UTF-8 -*-

from dogwood.core.gameframe.base_game_main import BaseGameMain
from dogwood.core.network.net_def import NeTDef
from dogwood.core.network.net_notify import NetNotify
from dogwood.core.network.sock_id import SockId

from cltlogic.terminate.terminate import Terminate
from cltlogic.game_define import GameDefine

class LogicMain(BaseGameMain):
    __slots__ = ('max_clt')
    def __init__(self, event, max_clt):
        super().__init__(event)
        self.max_clt = max_clt
        self._timer_group.add_timer_event('connect_clt', 1000, self.connect_clt)
    
    def create_client(self, sock_id):               # 重载父类,替换自己客户端类
        '''子类要重载，返回自己的客户端类'''
        client = Terminate(self._client_mgr, sock_id)
        return client
        
    def connect_clt(self):
        if self._client_mgr.sid_num() >= self.max_clt:     # 已经达到最大连接数
            return 
        
        nf = NetNotify(SockId(GameDefine.NET_ID.value), NeTDef.CLIENT_CREATE.value)
        self._net_dict[GameDefine.NET_ID.value].push_msg(nf)
        
    