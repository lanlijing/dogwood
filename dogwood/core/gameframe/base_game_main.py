# -*- coding: UTF-8 -*-

from dogwood.core.logger import Logger
from dogwood.core.base_thread import BaseThread
from dogwood.core.network.net_notify import NetNotify
from dogwood.core.network.net_def import NeTDef
from dogwood.core.gameframe.net_packet_split import NetPacketSplit, NetSplitMgr, NetSplitError
from dogwood.core.gameframe.base_client import BaseClient, ClientMgr, ClientError
from dogwood.core.base_packet import PacketError
from dogwood.core.mysql.mysql_monitor import MySqlMonitor
from dogwood.core.meta_class import Singleton, DeriveSingleton

class BaseGameMain(BaseThread, metaclass=Singleton):
    '''此类及派生类,一个工程里只能启动一个'''
    __slots__ = ('_mysql_monitor', '_client_mgr', '_net_split_mgr', '_net_dict')
    def __init__(self, event):
        real_cls_name = self.__class__.__name__
        DeriveSingleton.check_exist('BaseGameMain', real_cls_name)
        
        super().__init__(event)
        
        self._mysql_monitor = MySqlMonitor(self)         # mysql操作器
        self._client_mgr = ClientMgr()                   # 管理所有客户端连接
        self._net_split_mgr = NetSplitMgr()              # 网络粘包处理的管理器
        self._net_dict = {}                              # 网络监听进程字典
        
    def add_net(self, net_process):
        self._net_dict[net_process.net_id] = net_process
        
    def thread_init(self):              # 重载
        super().thread_init()
        self.create_db_monitor()
        self.create_game_config()
        
    def thread_quit(self):              
        self.close_db_monitor()
        super().thread_quit()
    
    def create_game_config(self):
        '''子类要重载,创建自己的配置类'''
        pass
    
    def create_db_monitor(self):
        '''子类要重载,创建自己的数据库管理类'''
        pass
    
    def close_db_monitor(self):
        self._mysql_monitor.close_all()
        
    def fill_msg_queue(self):                               # 重载父类   
        for net_proc in self._net_dict.values(): 
            while not net_proc.pull_msg_empty():
                msg_obj = net_proc.pull_msg()
                self._msg_queue.put(msg_obj)
        
    def process_msg(self, msg_obj):                     # 重载父类
        '''子类重载时,记得调用super().process_msg'''
        if type(msg_obj) is NetNotify:                      # 只处理网络消息
            if msg_obj.ope == NeTDef.CONNECT.value:             #新连接连上
                try:
                    self.create_packet_split(msg_obj.sid)           # 创建粘包处理器
                except NetSplitError as e:
                    Logger().warning(e)
                try:
                    client = self.create_client(msg_obj.sid)
                    self._client_mgr.on_net_connect(msg_obj.sid)
                except ClientError as e:
                    Logger().warning(e)
            elif msg_obj.ope == NeTDef.DISCONNECT.value:        # 连接关闭
                self._net_split_mgr.remove_split(msg_obj.sid)     # 关闭粘包处理
                try:
                    self._client_mgr.on_net_disconnect(msg_obj.sid)     # 关闭客户端
                except ClientError as e:
                    Logger().warning(e)
            elif msg_obj.ope == NeTDef.RECV.value:              # 收到网络消息
                if msg_obj.buf is None or len(msg_obj.buf) == 0:
                    Logger().warning('收到空串,{}'.format(msg_obj.sid))
                    return
                try:
                    sid, pack_list = self._net_split_mgr.deal_with_bytes(msg_obj.sid, msg_obj.buf)      #粘包处理
                    for pack in pack_list:
                        try:
                            self._client_mgr.push_net_msg(sid, pack)
                        except ClientError as e:
                            Logger().warning(e)
                except PacketError as e:
                    Logger().warning(e)
            elif msg_obj.ope == NeTDef.CLIENT_CONNECT_FAIL.value:           # 作为客户端,连远程服务器失败
                self.on_client_connect_fail(msg_obj.sid)
                
    def create_packet_split(self, sock_id):
        '''子类要重载，返回自己的粘包处理类'''
        split = NetPacketSplit(sock_id)
        self._net_split_mgr.add_split(sock_id, split)
    
    def create_client(self, sock_id):
        '''子类要重载，返回自己的客户端类'''
        client = BaseClient(self._client_mgr, sock_id)
        return client
                
    def process_timer(self, now_milli): 
        '''子类重载,需调用super().process_timer(now_milli)'''
        super().process_timer(now_milli)
        self._mysql_monitor.run_timer(now_milli)
        self._client_mgr.run_timer(now_milli)
        
    def on_client_connect_fail(self, sock_id):
        '''子类选择重载,添加自己的连远程服务器失败处理,如果不存在连接远程服务器,则不需要'''
        pass
                        
    def close_socket(self, sock_id, is_svr):
        if is_svr:
            ntif = NetNotify(sock_id, NeTDef.SERVER_CLOSE.value)
        else: 
            ntif = NetNotify(sock_id, NeTDef.CLIENT_CLOSE.value)
        self._net_dict[sock_id.net_id].push_msg(ntif)
        
    def send_socket_msg(self, sock_id, buffer):
        ntif = NetNotify(sock_id, NeTDef.SEND.value, buffer)
        self._net_dict[sock_id.net_id].push_msg(ntif)
        
    @property
    def mysql_monitor(self):
        return self._mysql_monitor
    
    @property
    def client_mgr(self):
        return self._client_mgr