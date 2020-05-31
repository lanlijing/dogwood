# -*- coding: UTF-8 -*-

import socket, selectors
import platform

from dogwood.core.helper import Helper
from dogwood.core.base_process import BaseProcess
from dogwood.core.logger import LogInit, Logger
from dogwood.core.network.sock_id import SockId
from dogwood.core.network.net_notify import NetNotify
from dogwood.core.network.net_def import NeTDef
from dogwood.core.base_packet import PacketDef

class ServerListen(BaseProcess):
    __slots__ = ('__net_id', '__port', '__selector', '__sock_listen', '__conn_sid_dict', '__sid_conn_dict')
    def __init__(self, log_name, event, net_id, port):
        super().__init__(log_name, event)
        self.__net_id = net_id
        self.__port = port
        self.__selector = selectors.DefaultSelector()
        self.__sock_listen = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__sock_listen.setblocking(False)
        self.__conn_sid_dict = {}                                       # key conn, value sock_id 
        self.__sid_conn_dict = {}                                      # key sock_id, value conn
        
    def process_init(self):
        self.__sock_listen.bind(('0.0.0.0', self.__port))
        self.__sock_listen.listen(NeTDef.LISTEN_NUM.value)
        self.__selector.register(self.__sock_listen, selectors.EVENT_READ, self.__on_accept)
        Logger().info('%s 监听启动. 端口:%d' % (self._log_name, self.__port))
    
    def run_frame(self, now_milli):
        try:
            events = self.__selector.select(NeTDef.SELECT_TIME_OUT.value)
        except Exception as e:
            Logger().error('{}.{}'.format(self.__net_id,e))
            return     
        for key, mask in events:
            callback = key.data
            callback(key.fileobj, mask)
        # 以下处理外界的消息,发关消息或关闭socket,或者退出进程
        notify_list = []
        while not self._in_queue.empty():
            nf = self._in_queue.get_nowait()
            notify_list.append(nf)
        send_count = 0
        for nf in notify_list:
            if type(nf) is str and nf.lower() == Helper.quit_signal():
                self._run_flag = False
                continue
            sid = nf.sid
            if sid.net_id != self.__net_id:
                Logger().warning('server listen.net_id error.{}.{}'.format(self.__net_id, sid))
                continue
            if nf.ope == NeTDef.SERVER_CLOSE.value:
                if not sid in self.__sid_conn_dict.keys():
                    Logger().warning('SERVER_CLOSE.sid not exist. {}'.format(sid))
                    continue
                conn_close = self.__sid_conn_dict[sid]
                self.__close_conn(conn_close)
            elif nf.ope == NeTDef.SEND.value:
                self.__send_msg(sid, nf.buf)
                send_count += 1
                if send_count >= NeTDef.MAX_TRANSMIT_ONE_FRAME.value:
                    continue
        
    def __on_accept(self, sock, mask):
        conn, addr = sock.accept()
        conn.setblocking(False)
        if platform.system().lower() == 'windows':       
            '''windows select模型超过509连接会报错'''
            conn_num = len(self.__conn_sid_dict)
            if conn_num >= NeTDef.WINDOWS_SELECT_MAX.value:
                Logger().error('listen_server, windows平台超过最大select数量.{}:{}'.format(self.__net_id, conn_num))
                conn.close()
                return
        sid = SockId(self.__net_id)
        sid.set_data(addr)
        self.__conn_sid_dict[conn] = sid
        self.__sid_conn_dict[sid] = conn
        self.__selector.register(conn, selectors.EVENT_READ, self.__on_read)
        
        ntif = NetNotify(sid, NeTDef.CONNECT.value)
        self._out_queue.put(ntif)
            
    def __on_read(self, conn, mask):
        sid = self.__conn_sid_dict[conn]
        try:
            msg = conn.recv(PacketDef.PER_RECV_SIZE.value)
            if (not msg) or (len(msg) == 0):
                self.__close_conn(conn)
                return
            ntif = NetNotify(sid, NeTDef.RECV.value, msg)
            self._out_queue.put(ntif)
        except ConnectionResetError as err:     # 目标方突然强行关闭程序会发生,如果是正常关闭socket，不会产生异常
            # Logger().info('ConnectionResetError:{} {}'.format(sid, err))
            self.__close_conn(conn)            
        except Exception as e:
            Logger().info(sid, e)
            self.__close_conn(conn)
    
    def __close_conn(self, conn):
        if not conn in self.__conn_sid_dict.keys():        # 已经关闭，不重复关闭
            return
        
        self.__selector.unregister(conn)
        sid = self.__conn_sid_dict[conn]
        conn.close()
        del self.__sid_conn_dict[sid]
        del self.__conn_sid_dict[conn]  
        
        ntif = NetNotify(sid, NeTDef.DISCONNECT.value)
        self._out_queue.put(ntif)   
    
    def __send_msg(self, sock_id, buf):
        if sock_id in self.__sid_conn_dict.keys():
            try:
                self.__sid_conn_dict[sock_id].send(buf)
            except Exception as e:
                Logger().warning(e)
        else:
            Logger().warning('server send_msg. sid not exist. {}'.format(sock_id))
    
    def quit(self):
        self._in_queue.put(Helper.quit_signal())
        
    @property
    def net_id(self):
        return self.__net_id
    
    @property
    def port(self):
        return self.__port