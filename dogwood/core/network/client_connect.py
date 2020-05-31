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

class ClientConnect(BaseProcess):
    __slots__ = ('__net_id', '__server_host', '__server_port', '__selector', '__sock_sid_dict', '__sid_sock_dict')
    def __init__(self, log_name, event, net_id, server_host, server_port):
        super().__init__(log_name, event)
        self.__net_id = net_id
        self.__server_host = server_host
        self.__server_port = server_port
        self.__selector = selectors.DefaultSelector()
        self.__sock_sid_dict = {}
        self.__sid_sock_dict = {}
        
    def process_init(self):
        self.__create_selector_socket()
    
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
                self.__close_all()
                self._run_flag = False
                break               # 此处break, 因为已经close_all， 服务端类此处是continue
            sid = nf.sid
            if sid.net_id != self.__net_id:
                Logger().warning('client connect.net_id error.{}.{}.'.format(self.__net_id, sid))
                continue
            if nf.ope == NeTDef.CLIENT_CREATE.value:
                if platform.system().lower() == 'windows':       
                    '''windows select模型超过509连接会报错'''
                    conn_num = len(self.__sock_sid_dict)
                    if conn_num >= NeTDef.WINDOWS_SELECT_MAX.value:
                        Logger().error('client connect windows下select连接树超出数量.{}:{}'.format(self.__net_id, conn_num))
                        continue
                self.__create_socket()
            elif nf.ope == NeTDef.CLIENT_CLOSE.value:
                self.__close_socket(sid, True)
            elif nf.ope == NeTDef.SEND.value:
                self.__send_msg(sid, nf.buf)
                send_count += 1
                if send_count >= NeTDef.MAX_TRANSMIT_ONE_FRAME.value:
                    continue
                
    def __create_socket(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #sock.setblocking(False) 这里不能设,否则会出现BlockingIOError: [WinError 10035]
        far_address = (self.__server_host, self.__server_port)
        try: 
            sock.connect(far_address)           
        except Exception as e:
            Logger().info(e)
            sock_id = SockId(self.__net_id)
            nf = NetNotify(sock_id, NeTDef.CLIENT_CONNECT_FAIL.value)
            self._out_queue.put(nf) 
            return
        sock_id = SockId(self.__net_id)
        sock_id.set_data(sock.getsockname())
        self.__sid_sock_dict[sock_id] = sock
        self.__sock_sid_dict[sock] = sock_id
        self.__selector.register(sock, selectors.EVENT_READ, self.__on_read)
        
        nf = NetNotify(sock_id, NeTDef.CONNECT.value)
        self._out_queue.put(nf)
    
    def __create_selector_socket(self):
        '''专门用来创建selector用的socket，因为不建一个这样的socket,self.selector.select()会报错
此socket不连服务端'''
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock_id = SockId(self.__net_id)
        sock_id.set_data(('127.0.0.1', 1))
        self.__sid_sock_dict[sock_id] = sock
        self.__sock_sid_dict[sock] = sock_id
        self.__selector.register(sock, selectors.EVENT_READ, self.__on_read)
        
    def __on_read(self, sock, mask):
        sid = self.__sock_sid_dict[sock]
        try:
            msg = sock.recv(PacketDef.PER_RECV_SIZE.value)      #linux下，创建后就会执行
            if (not msg) or (len(msg) == 0):
                self.__close_socket(sid, True)
                return
            ntif = NetNotify(sid, NeTDef.RECV.value, msg)
            self._out_queue.put(ntif)
        except ConnectionResetError as err:
            #Logger().info('ConnectionResetError:{} {}'.format(sid, err))
            self.__close_socket(sid, True)           
        except Exception as e:
            if (type(e) is OSError) and (e.errno == 107):
                pass             # linux下，没连接上就会recv
            else:
                Logger().info('{}:{}:{}'.format(sid, e, type(e)))
                self.__close_socket(sid, True)
    
    def __send_msg(self, sock_id, buf):
        if sock_id in self.__sid_sock_dict.keys():
            try:
                self.__sid_sock_dict[sock_id].send(buf)
            except Exception as e:
                Logger().warning(e)
        else:
            Logger().warning('client send_msg. sid not exist. {}'.format(sock_id))
    
    def __close_socket(self, sock_id, b_out):
        if not sock_id in self.__sid_sock_dict.keys():
            Logger().warning('close sock id not exist.{}'.format(sock_id))            
            return
        sock = self.__sid_sock_dict[sock_id]
        sock.close()
        self.__selector.unregister(sock)
        del self.__sid_sock_dict[sock_id]
        del self.__sock_sid_dict[sock]
        
        if b_out:
            nf = NetNotify(sock_id, NeTDef.DISCONNECT.value)
            self._out_queue.put(nf)
        
    def __close_all(self):
        del_arr = []
        for k in self.__sid_sock_dict.keys():
            del_arr.append(k)
        for d in del_arr:
            self.__close_socket(d, False)
        
    def quit(self):
        self._in_queue.put(Helper.quit_signal())
        
    @property
    def net_id(self):
        return self.__net_id
        
    @property
    def far_addr(self):
        return (self.__server_addr, self.__server_port)
        
        
