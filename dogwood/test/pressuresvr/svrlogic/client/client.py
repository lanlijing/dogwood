# -*- coding: UTF-8 -*-

import random

from dogwood.core.gameframe.base_client import BaseClient
from dogwood.core.global_var import GlobalVar

from dogwood.core.base_packet import BasePacket

from svrlogic.svr_define import SvrDefine

class PreClient(BaseClient):
    
    def __init__(self, mgr, sock_id):
        super().__init__(mgr, sock_id)
        
    def on_net(self, msg):
        super().on_net(msg)
        mid = msg.data['m']
        nid = msg.data['n']
        clt = msg.data['clt']
        print('recv:', clt)
        self.send_result(clt)
        
    def send_result(self, clt_msg):
        pack = BasePacket()
        pack['m'] = SvrDefine.SVR_MID.value
        pack['n'] = SvrDefine.SVR_NID.value
        pack['clt'] = clt_msg
        pack['svr'] = 'hello,pressure.{}'.format(random.randint(0, 10000))
        svr_main = GlobalVar.get_value('svr_main')
        svr_main.send_socket_msg(self._sock_id, pack.pack())
    
    