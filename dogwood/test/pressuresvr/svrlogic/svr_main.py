# -*- coding: UTF-8 -*-

from dogwood.core.gameframe.base_game_main import BaseGameMain

from svrlogic.client.client import PreClient

class SvrMain(BaseGameMain):
    
    def __init__(self, event):
        super().__init__(event)
    
    def create_client(self, sock_id):               # 重载父类,替换自己客户端类
        '''子类要重载，返回自己的客户端类'''
        client = PreClient(self._client_mgr, sock_id)
        return client
        