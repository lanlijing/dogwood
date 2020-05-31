# -*- coding: UTF-8 -*-

from dogwood.core.helper import Helper
from dogwood.core.gameframe.base_client import BaseClient
from dogwood.core.timer_group import TimerGroup
from dogwood.core.global_var import GlobalVar

from dogwood.core.base_packet import BasePacket

from cltlogic.game_define import GameDefine

class TerminateUserId:
    g_user_id = 1

class Terminate(BaseClient):
    __slots__ = ('__time_group')
    def __init__(self, mgr, sock_id):
        super().__init__(mgr, sock_id)
        self.__time_group = TimerGroup()
        self.__time_group.add_timer_event('send_msg', 10000, self.send_msg)
        self.set_user_id(TerminateUserId.g_user_id)
        TerminateUserId.g_user_id += 1
        print('net client.sid:{},uid:{}'.format(self._sock_id, self._user_id))
        
    def on_net(self, msg):
        super().on_net(msg)
        mid = msg.data['m']
        nid = msg.data['n']
        clt = msg.data['clt']
        svr = msg.data['svr']
        print('mid:{},nid:{},clt:{},svr:{}'.format(mid, nid, clt, svr))
        
    def run_timer(self, now_milli):      # 重载
        super().run_timer(now_milli)
        self.__time_group.run_timer(now_milli)
        
    def send_msg(self):
        pack = BasePacket()
        pack['m'] = GameDefine.CLT_MID.value
        pack['n'] = GameDefine.CLT_NID.value
        pack['clt'] = '{}:{}'.format(self._user_id, Helper.get_time_stamp_milli_second())
        game_main = GlobalVar.get_value('game_main')
        game_main.send_socket_msg(self.sock_id, pack.pack())
        