# -*- coding: UTF-8 -*-

import socket, selectors
import hashlib, base64, struct
import platform

from dogwood.core.helper import Helper
from dogwood.core.base_process import BaseProcess
from dogwood.core.logger import LogInit, Logger
from dogwood.core.network.sock_id import SockId
from dogwood.core.network.net_notify import NetNotify
from dogwood.core.network.net_def import NeTDef
from dogwood.core.base_packet import PacketDef

class WSClientConnect(BaseProcess):
    __slots__ = ('__net_id', '__server_host', '__server_port', '__selector', '__sock_sid_dict', '__sid_sock_dict', '__handshakes_dict')
    def __init__(self, log_name, event, net_id, server_host, server_port):
        super().__init__(log_name, event)
        self.__net_id = net_id
        self.__server_host = server_host
        self.__server_port = server_port
        self.__selector = selectors.DefaultSelector()
        self.__sock_sid_dict = {}
        self.__sid_sock_dict = {}
        self.__handshakes_dict = {}                                     # websocket握手情况,只有通过了握手的连接才能算成正式连接 
        
    def process_init(self):
        self.__create_selector_socket()
    
    def run_frame(self, now_milli):
        events = self.__selector.select(NeTDef.SELECT_TIME_OUT.value)
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
                break                       # 此处break, 因为已经close_all， 服务端类此处是continue
            sid = nf.sid
            if sid.net_id != self.__net_id:
                Logger().warning('ws client connect.net_id error.{}.{}'.format(self.__net_id, nf.sid))
                continue
            if nf.ope == NeTDef.CLIENT_CREATE.value:
                if platform.system().lower() == 'windows':    
                    '''windows select模型超过509连接会报错'''
                    conn_num = len(self.__sock_sid_dict)
                    if conn_num >= NeTDef.WINDOWS_SELECT_MAX.value:
                        Logger().error('ws_client windows下select连接树超出数量.{}:{}'.format(self.__net_id, conn_num))
                        continue
                self.__create_socket()
            elif nf.ope == NeTDef.CLIENT_CLOSE.value:
                self.__close_socket(sid, True)
            elif nf.ope == NeTDef.SEND.value:
                self.__send_ws_msg(sid, nf.buf)
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
        self.__handshakes_dict[sock] = False
        self.__selector.register(sock, selectors.EVENT_READ, self.__on_read)
        
        self.__send_handshake_msg(sock)
    
    def __create_selector_socket(self):
        '''专门用来创建selector用的socket，因为不建一个这样的socket,self.selector.select()会报错
此socket不连服务端'''
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock_id = SockId(self.__net_id)
        sock_id.set_data(('127.0.0.1', 1))
        self.__sid_sock_dict[sock_id] = sock
        self.__sock_sid_dict[sock] = sock_id
        self.__handshakes_dict[sock] = False
        self.__selector.register(sock, selectors.EVENT_READ, self.__on_read)
        
    def __on_read(self, sock, mask):
        sid = self.__sock_sid_dict[sock]
        try:
            if self.__handshakes_dict[sock] == False:        # 首先判断websocket握手
                msg = sock.recv(PacketDef.PER_RECV_SIZE.value)
                if (not msg) or (len(msg) == 0):
                    self.__close_socket(sid, False)     # 还未连接上,不发给逻辑层
                    nf = NetNotify(sid, NeTDef.CLIENT_CONNECT_FAIL.value)
                    self._out_queue.put(nf) 
                    return
                handshake_recv = str(msg)
                if handshake_recv.lower().find('connection: upgrade') != -1:
                    self.__handshakes_dict[sock] = True 
                    nf = NetNotify(sid, NeTDef.CONNECT.value)
                    self._out_queue.put(nf)
                return
            #                    
            receive = sock.recv(2)                              # 130是二进制流，129是text
            if (not receive) or (len(receive) == 0):
                self.__close_socket(sid, True)
                return
            len_tag = receive[1] & 0x7f
            content_len = 0         #实际应该接收的内容长度
            if len_tag <= 125:
                content_len = len_tag
            elif len_tag == 126:
                receive, recv_ok = self.__recv_msg(sock, 2)
                if recv_ok is False:
                    Logger().warning('读取websocket长度出错:126')
                    self.__close_socket(sid, True)
                    return
                content_len, = struct.unpack_from('!h', receive, 0)
            elif len_tag == 127:
                receive, recv_ok = self.receive_msg(sock, 8)
                if recv_ok is False:
                    Logger().warning('读取websocket长度出错:127')
                    self.__close_socket(sid, True)
                    return
                content_len, = struct.unpack_from('!q', receive, 0)
            else:
                Logger().warning('读取websocket长度出错:too large')
                self.__close_socket(sid, True)
                return
            receive, recv_ok = self.__recv_msg(sock, content_len)
            if recv_ok is False:
                Logger().warning('读取websocket包内容出错')
                self.__close_socket(sid, True)
                return
            
            ntif = NetNotify(sid, NeTDef.RECV.value, receive)        # 告诉主进程收到网络消息
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
            
    def __send_handshake_msg(self, sock):
        handshake_str = ('GET / HTTP/1.1\r\nHost: {}:{}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: EZFAWipfRYaGQ79BAMHd+A=='.format
                         (self.__server_host, self.__server_port))
        handshake_bytes = handshake_str.encode(encoding="utf8")
        try:
            sock.send(handshake_bytes)
        except Exception as e:
            Logger().warning(e)
    
    def __send_ws_msg(self, sock_id, msg):
        if not sock_id in self.__sid_sock_dict.keys():
            Logger().warning('ws client send_ws_msg. sid not exist. {}'.format(sock_id))
            return
        msgLen = len(msg)
        backMsgList = []
        backMsgList.append(struct.pack('B', 0x82))   # 130是二进制流，129是text
        if msgLen <= 125:
            backMsgList.append(struct.pack('B', (msgLen | 0x80)))
        elif msgLen <= 65535:
            backMsgList.append(struct.pack('B', (126 | 0x80)))
            backMsgList.append(struct.pack('!h', msgLen))
        elif msgLen <= (2^64 - 1):
            backMsgList.append(struct.pack('B', (127 | 0x80)))
            backMsgList.append(struct.pack('!q', msgLen))
        else:
            Logger().info("the message is too long to send in a time")
            return
        backMsgList.append(struct.pack('bbbb', 0x01, 0x02, 0x03, 0x04)) #mask, 自定义
        bye_arr = bytearray()
        mask = b'\x01\x02\x03\x04'
        i = 0
        for d in msg:
            bye_arr.append(d ^ mask[i % 4])
            i += 1
        message_byte = bytes()
        for c in backMsgList:
            message_byte += c
        message_byte += bytes(bye_arr)
        sock = self.__sid_sock_dict[sock_id]
        try:
            sock.send(message_byte)
        except Exception as e:
            Logger().warning(e)
        
    def __recv_msg(self, sock, length):        
        try: 
            receive = sock.recv(length)
        except ConnectionResetError as err:
            Logger().info(err)
            return None, False
        except Exception as e:
            Logger().info(e)
            return None, False
        return receive, True
    
    def __close_socket(self, sock_id, b_out):
        if not sock_id in self.__sid_sock_dict.keys():
            Logger().warning('close sock id not exist.{}'.format(sock_id))            
            return
        sock = self.__sid_sock_dict[sock_id]
        sock.close()
        self.__selector.unregister(sock)
        del self.__sid_sock_dict[sock_id]
        del self.__sock_sid_dict[sock]
        del self.__handshakes_dict[sock]
        
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
