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

class WSServerListen(BaseProcess):
    __slots__ = ('__net_id', '__port', '__selector', '__sock_listen', '__conn_sid_dict', '__sid_conn_dict', '__handshakes_dict')
    def __init__(self, log_name, event, net_id, port):
        super().__init__(log_name, event)
        self.__net_id = net_id
        self.__port = port
        self.__selector = selectors.DefaultSelector()
        self.__sock_listen = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__sock_listen.setblocking(False)
        self.__conn_sid_dict = {}                                       # key conn, value sock_id 
        self.__sid_conn_dict = {}                                      # key sock_id, value conn
        self.__handshakes_dict = {}                                     # 客户端websocket握手情况,只有通过了握手的连接才能算成正式连接       
        
    def process_init(self):
        self.__sock_listen.bind(('0.0.0.0', self.__port))
        self.__sock_listen.listen(NeTDef.LISTEN_NUM.value)
        self.__selector.register(self.__sock_listen, selectors.EVENT_READ, self.__on_accept)
        Logger().info('WS %s 监听启动. 端口:%d' % (self._log_name, self.__port))
    
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
                Logger().warning('wsserver listen.net_id error.{}.{}'.format(self.__net_id, sid))
                continue
            if nf.ope == NeTDef.SERVER_CLOSE.value:
                if not sid in self.__sid_conn_dict.keys():
                    Logger().warning('ws SERVER_CLOSE.sid not exist. {}'.format(sid))
                    continue
                conn_close = self.__sid_conn_dict[sid]
                self.__close_conn(conn_close)
            elif nf.ope == NeTDef.SEND.value:
                self.__send_ws_msg(sid, nf.buf)
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
                Logger().error('wsserver, windows平台超过最大select数量.{}:{}'.format(self.__net_id, conn_num))
                conn.close()
                return
        sid = SockId(self.__net_id)
        sid.set_data(addr)
        self.__conn_sid_dict[conn] = sid
        self.__sid_conn_dict[sid] = conn
        self.__selector.register(conn, selectors.EVENT_READ, self.__on_read)
        
        self.__handshakes_dict[conn] = False        
            
    def __on_read(self, conn, mask):
        sid = self.__conn_sid_dict[conn]
        try:
            if self.__handshakes_dict[conn] == False:        # 首先判断websocket握手
                msg = conn.recv(PacketDef.PER_RECV_SIZE.value)
                if (not msg) or (len(msg) == 0):
                    self.__close_conn(conn)
                    return
                handshake_recv = str(msg)
                entities = handshake_recv.split("\\r\\n")
                sec_key_in = ''
                for str_sub in entities:
                    if str_sub.split(":")[0].strip() == 'Sec-WebSocket-Key':
                        sec_key_in = str_sub.split(":")[1].strip()
                        break
                sec_websocket_key = sec_key_in + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
                response_key = base64.b64encode(hashlib.sha1(bytes(sec_websocket_key, encoding="utf8")).digest())
                response_key_str = str(response_key)
                response_key_str = response_key_str[2:30]
                response_key_entity = "Sec-WebSocket-Accept: " + response_key_str +"\r\n"
                try:
                    conn.send(bytes("HTTP/1.1 101 Web Socket Protocol Handshake\r\n", encoding="utf8"))
                    conn.send(bytes("Upgrade: websocket\r\n", encoding="utf8"))
                    conn.send(bytes(response_key_entity, encoding="utf8"))
                    conn.send(bytes("Connection: Upgrade\r\n\r\n", encoding="utf8"))
                except Exception as e:
                    Logger().warning(e)
                    return
                self.__handshakes_dict[conn] = True
                ntif = NetNotify(sid, NeTDef.CONNECT.value)    # 没能通过握手的连接不告诉主程序
                self._out_queue.put(ntif)
                return
            #                    
            receive = conn.recv(2)                              # 130是二进制流，129是text
            if (not receive) or (len(receive) == 0):
                self.__close_conn(conn)
                return
            is_mask = receive[1] & 0x80
            if is_mask == 0:
                Logger().warning('暂不支持不带mask的websocket.sid:{}'.format(sid))
                self.__close_conn(conn)
                return
            len_tag = receive[1] & 0x7f
            if len_tag == 0:
                self.__close_conn(conn)
                return
            content_len = 0         #实际应该接收的内容长度
            if len_tag <= 125:
                content_len = len_tag
            elif len_tag == 126:
                receive, recv_ok = self.__recv_msg(conn, 2)
                if recv_ok is False:
                    Logger().warning('读取websocket长度出错:126.sid:{}'.format(sid))
                    self.__close_conn(conn)
                    return
                content_len, = struct.unpack_from('!h', receive, 0)
            elif len_tag == 127:
                receive, recv_ok = self.receive_msg(conn, 8)
                if recv_ok is False:
                    Logger().warning('读取websocket长度出错:127.sid:{}'.format(sid))
                    self.__close_conn(conn)
                    return
                content_len, = struct.unpack_from('!q', receive, 0)
            else:
                Logger().warning('读取websocket长度出错:too large.sid:{}'.format(sid))
                self.__close_conn(conn)
                return
            mask, recv_ok = self.__recv_msg(conn, 4)
            if recv_ok is False:
                Logger().warning('读取websocketmask出错.sid:{}'.format(sid))
                self.__close_conn(conn)
                return
            receive, recv_ok = self.__recv_msg(conn, content_len)
            if recv_ok is False:
                Logger().warning('读取websocket包内容出错.sid:{}'.format(sid))
                self.__close_conn(conn)
                return
            byte_arr = bytearray()
            i = 0
            for d in receive:
                byte_arr.append(d ^ mask[i % 4])
                i += 1
            data_bytes = bytes(byte_arr)
            if (len(data_bytes) == 0):
                self.__close_conn(conn)
                return
            if (len(data_bytes) == 2) and (data_bytes[0] == 0x03) and (data_bytes[1] == 0xe9 or data_bytes[1] == 0xe8):
                self.__close_conn(conn)
                return
            
            ntif = NetNotify(sid, NeTDef.RECV.value, data_bytes)        # 告诉主进程收到网络消息
            self._out_queue.put(ntif)
        except ConnectionResetError as err:     # 目标方突然强行关闭程序会发生,如果是正常关闭socket，不会产生异常
            Logger().info('ConnectionResetError:{} {}'.format(sid, err))
            self.__close_conn(conn)            
        except Exception as e:
            Logger().info(sid, e)
            self.__close_conn(conn)
            
    def __recv_msg(self, conn, length):        
        try: 
            receive = conn.recv(length)
        except ConnectionResetError as err:
            Logger().info(err)
            return None, False
        except Exception as e:
            Logger().info(e)
            return None, False
        return receive, True
    
    def __close_conn(self, conn):
        if not conn in self.__conn_sid_dict.keys():        # 已经关闭，不重复关闭
            return
        
        self.__selector.unregister(conn)
        sid = self.__conn_sid_dict[conn]
        conn.close()
        del self.__sid_conn_dict[sid]
        del self.__conn_sid_dict[conn]  
        b_handshakes = self.__handshakes_dict[conn]
        del self.__handshakes_dict[conn]
        
        if b_handshakes:                    # 没能通过握手的连接不告诉主程序
            ntif = NetNotify(sid, NeTDef.DISCONNECT.value)
            self._out_queue.put(ntif)   
    
    def __send_ws_msg(self, sock_id, buf):
        if sock_id in self.__sid_conn_dict.keys():
            msgLen = len(buf)
            backMsgList = []
            backMsgList.append(struct.pack('B', 0x82))   # 0x82是二进制流，0x81是text
            if msgLen <= 125:
                backMsgList.append(struct.pack('b', msgLen))
            elif msgLen <= 65535:
                backMsgList.append(struct.pack('b', 126))
                backMsgList.append(struct.pack('!h', msgLen))
            elif msgLen <= (2^64 - 1):
                backMsgList.append(struct.pack('b', 127))
                backMsgList.append(struct.pack('!q', msgLen))
            else:
                Logger().info("the message is too long to send in a time")
                return
            message_byte = bytes()
            for c in backMsgList:
                message_byte += c
            message_byte += buf
            try:
                self.__sid_conn_dict[sock_id].send(message_byte)
            except Exception as e:
                Logger().warning(e)
        else:
            Logger().warning('ws server __send_ws_msg. sid not exist. {}'.format(sock_id))
    
    def quit(self):
        self._in_queue.put(Helper.quit_signal())
        
    @property
    def net_id(self):
        return self.__net_id
    
    @property
    def port(self):
        return self.__port
