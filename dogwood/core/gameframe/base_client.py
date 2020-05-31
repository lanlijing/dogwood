# -*- coding: UTF-8 -*-

from enum import Enum
import copy

from dogwood.core.logger import Logger
from dogwood.core.network.sock_id import SockId

class ClientDef(Enum):
    STATUS_EMPTY = 0        # 空状态
    STATUS_NET_CONNECT = 1  # 网络连接上
    STATUS_LOGINING = 2     # 登陆中
    STATUS_LOGIN_OK = 3     # 登陆成功
    
class ClientError(Exception):
    def __init__(self, msg):
        self.msg = msg
        
    def __str__(self):
        return 'ClientError: {}'.format(self.msg)

class ClientMgr:
    __slots__ = ('sid_dict', 'uid_dict', 'account_new_login_dict')
    def __init__(self):
        self.sid_dict = {}                              # 以sock_id为key的字典
        self.uid_dict = {}                              # 以user_id为key的字典
        self.account_new_login_dict = {}                # 帐号在新的地方登陆的字典,以uid为Key,value是新登陆的client
    
    def on_net_connect(self, sock_id):
        if not sock_id in self.sid_dict.keys():
            raise ClientError('on_net_connect error, sock_id not exist.{}'.format(sock_id))
            return
        self.sid_dict[sock_id].on_net_connect()
    
    def on_net_disconnect(self, sock_id):
        if not sock_id in self.sid_dict.keys():
            raise ClientError('on_net_disconnect error, sock_id not exist.{}'.format(sock_id))
            return
        self.sid_dict[sock_id].on_net_disconnect()
        
    def push_net_msg(self, sock_id, msg):
        if not sock_id in self.sid_dict.keys():
            raise ClientError('push_net_msg error, sock_id not exist.{}'.format(sock_id))
            return
        client = self.sid_dict[sock_id]
        client.on_net(msg)
        
    def push_module_msg(self, user_id, msg):
        if not user_id in self.uid_dict.keys():
            raise ClientError('push_module_msg error, user_id not exist.{}'.format(user_id))
            return
        client = self.uid_dict[user_id]
        client.on_module(msg)
        
    def check_old_login_exist(self, user_id, new_login):
        '''查询uid是否存在,顶替, 谳用者可以选择等待原来的关闭了，再执行接下来的代码'''
        if user_id in self.uid_dict.keys():
            old_client = self.uid_dict[user_id]
            old_client.on_account_new_login()
            self.account_new_login_dict[user_id] = new_login
            return True
        return False
    
    def on_client_quit(self, sock_id, user_id):
        if sock_id in self.sid_dict.keys():
            del self.sid_dict[sock_id]
        else:
            Logger().warning('BaseClient:quit error, sock_id not in mgr dict.{}'.format(sock_id))
        if not user_id is None:
            if user_id in self.uid_dict.keys():
                del self.uid_dict[user_id]
            else:
                Logger().warning('BaseClient:quit error, user_id not in mgr dict.{}'.format(user_id))
        if user_id in self.account_new_login_dict.keys():       # 在新登录队列中存在
            new_client = self.account_new_login_dict[user_id]
            new_client.on_account_old_login_quit()
            del self.account_new_login_dict[user_id]
            
    def sock_id_exist(self, sock_id):
        return sock_id in self.sid_dict.keys()
    
    def add_sid_client(self, sock_id, client):
        self.sid_dict[sock_id] = client
        
    def user_id_exist(self, user_id):
        return user_id in self.uid_dict.keys()
    
    def add_uid_client(self, user_id, client):
        self.uid_dict[user_id] = client
        
    def sid_num(self):
        return len(self.sid_dict)
        
    def run_timer(self, now_milli):
        for clt in self.sid_dict.values():
            clt.run_timer(now_milli)
                
    
class BaseClient:
    __slots__ = ('_mgr', '_sock_id', '_user_id', '_status')
    def __init__(self, mgr, sock_id):
        '''
    paras:
    mgr: ClientMgr对象
    sock_id: SockId 类型,唯一网络表示
            子 类重载：
            需要调用：super().__init__(mgr, sock_id)
        '''
        if mgr.sock_id_exist(sock_id):
            raise ClientError('BaseClient:init error, sock_id exist.{}'.format(sock_id))
            return
        
        self._mgr = mgr
        self._sock_id = copy.deepcopy(sock_id)
        self._user_id = None
        self._status = ClientDef.STATUS_EMPTY.value
        
        self._mgr.add_sid_client(self._sock_id, self)
        
    def quit(self):       
        ''''子类重载的时候,要注意调用super().quit(),否则内存泄漏'''                             
        self._status = ClientDef.STATUS_EMPTY.value
        sock_id = self._sock_id
        user_id = self._user_id
        self._mgr.on_client_quit(sock_id, user_id)
                
    def set_user_id(self, user_id):
        if user_id is None or self._mgr.user_id_exist(user_id):
            raise ClientError('BaseClient:set_user_id error, user_id exist or None.{}'.format(user_id))
            return
        self._user_id = user_id
        self._mgr.add_uid_client(self._user_id, self)
        
    @property
    def sock_id(self):
        return self._sock_id
    
    @property
    def user_id(self):
        return self._user_id
        
    def on_net_connect(self):
        self._status = ClientDef.STATUS_NET_CONNECT.value
        
    def on_net_disconnect(self):
        '''子类继承,注意调用super().on_net_disconnect()'''
        self.quit()
        
    def on_account_new_login(self):
        '''帐户在其它地方登陆，子类要继承，加入自己的处理，包括下线'''
        pass
    
    def on_account_old_login_quit(self):
        '''原来的账户登陆下线，子类要继承，加入自己的处理，包括下线'''
        pass
    
    def on_net(self, msg):
        '''子类需重写'''
        pass
        
    def on_module(self, msg):
        '''子类需重写'''
        pass
    
    def run_timer(self, now_milli):
        '''子类需重写'''
        pass

        