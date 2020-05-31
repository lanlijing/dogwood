# -*- coding: UTF-8 -*-

from enum import Enum
import json
import struct

from dogwood.core.logger import Logger

class PacketDef(Enum):
    MIN_PACKET_LEN = 7            # json的最短长度会是7'{"m":0}'
    MAX_PACKET_LEN = 16384         # 消息包最大长度,16K
    PACKET_SPLIT_BUFFER_SIZE = 65536     # 粘包处理缓冲区长度,64K
    PER_RECV_SIZE = 2048          # 网络读取时也使用此长度
    
class PacketError(Exception):
    def __init__(self, msg):
        self.msg = msg
        
    def __str__(self):
        return 'PacketError: {}'.format(self.msg)

class BasePacket:
    '''网络通讯及服务器内部进程线程间通讯用的协议,两个字节的json长度.
    长度不包括两个字节本身,json格式的内容'''
    __slots__ = ('data')
    def __init__(self):
        self.data = {}
        
    def empty(self):
        return len(self.data) == 0      
    
    def unpack(self, buffer):
        length, = struct.unpack_from('<h', buffer, 0)          #json长度
        bys_read, = struct.unpack_from('%ds' % length, buffer, 2)      #json内容
        try:
            str_data = bys_read.decode(encoding='utf8')
        except Exception as e:
            raise PacketError('{}.{}'.format(e, bys_read[:30]))
            return
        try:
            self.data = json.loads(str_data)
        except json.JSONDecodeError:
            self.data.clear()
            raise PacketError(str_data[:30])        # 只打印前30个字符,太多不方便显示
    
    def pack(self):
        js_str = json.dumps(self.data, ensure_ascii=False)
        bys = js_str.encode(encoding='utf8')
        length = len(bys)
        buffer = struct.pack('<h%ds' % length, length, bys)
        return buffer
    
    def set_id(self, mid, nid):
        self.data['m'] = mid
        self.data['n'] = nid
    
    def __setitem__(self, key, value):
        self.data[key] = value
        
    def get(self, key, def_value):
        return self.data.get(key, def_value)
    

class PacketSplit:
    '''处理网络传输中的粘包处理'''
    __slots__ = ('_byte_arr', '_copy_pos', '_split_pos', '_data_len')
    def __init__(self):
        self._byte_arr = bytearray(PacketDef.PACKET_SPLIT_BUFFER_SIZE.value)
        self._copy_pos = 0
        self._split_pos = 0
        self._data_len = 0
        
    def clear(self):
        for i in range(0, PacketDef.PACKET_SPLIT_BUFFER_SIZE.value):
            self._byte_arr[i] = 0
        self._copy_pos = 0
        self._split_pos = 0
        self._data_len = 0
        
    def push_data(self, dt_bys):
        dt_len = len(dt_bys)
        if (dt_len > PacketDef.MAX_PACKET_LEN.value):
            Logger().warning('PacketSplit.push_data.长度超长.{}'.format(dt_len))
            return False
        for i in range(0, dt_len):
            if self._copy_pos >= PacketDef.PACKET_SPLIT_BUFFER_SIZE.value:
                self._copy_pos = 0
            self._byte_arr[self._copy_pos] = dt_bys[i]
            self._copy_pos += 1
        self._data_len += dt_len
        return True
        
    def split(self):
        '''派生类重载'''
        if self._data_len <= 0:
            return []
        len_arr = bytearray(2)
        pack_list = []
        
        while self._data_len > 0:
            if self._split_pos >= PacketDef.PACKET_SPLIT_BUFFER_SIZE.value:
                self._split_pos = 0
            len_pos1 = self._split_pos
            len_pos2 = self._split_pos + 1
            if len_pos2 >= PacketDef.PACKET_SPLIT_BUFFER_SIZE.value:
                len_pos2 = 0
            len_arr[0] = self._byte_arr[len_pos1]
            len_arr[1] = self._byte_arr[len_pos2]
            content_len = int.from_bytes(len_arr, 'little')
            if content_len < PacketDef.MIN_PACKET_LEN.value or content_len > PacketDef.MAX_PACKET_LEN.value:  #等于0也是异常
                self.raise_error()
                return []
            '''判断是否有完整包,
            __data_len不为0的情况下,__copy_pos和__split_pos不可能相等。因为每次的MAX_PER_TO_SPLIT_SIZE只有2048,而缓冲区65536,不可能出现一次填充到尾又到头又到__split_pos
            的情况。
            同一边:_copy_pos > _split_pos
            不同边:_copy_pos < _split_pos
            '''
            if self._copy_pos == self._split_pos:
                self.raise_error()
                return []
            if self._copy_pos > self._split_pos and content_len > (self._copy_pos - self._split_pos):              #同一边
                break
            if self._copy_pos < self._split_pos:                                                                  # 不同边
                if content_len > (PacketDef.MAX_PACKET_LEN.value - self._split_pos) + self._copy_pos:
                    break
            pack_len = content_len + 2          # BasePacket开头的两个字节长度不包括长度本身
            data_arr = bytearray(pack_len)      
            pack_pos = len_pos1
            for i in range(0, pack_len):            
                if pack_pos >= PacketDef.PACKET_SPLIT_BUFFER_SIZE.value:
                    pack_pos = 0
                data_arr[i] = self._byte_arr[pack_pos]
                self._byte_arr[pack_pos] = 0           #清0
                pack_pos += 1
            packet = BasePacket()
            try:
                packet.unpack(bytes(data_arr))
            except Exception as e:
                self.clear()
                raise e
                return []
            pack_list.append(packet)
            self._split_pos = pack_pos
            self._data_len -= pack_len
        
        return pack_list
            
    def raise_error(self):
        '''在此函数里会调用clear'''
        info_len = 30                   # 只打印30数据
        info_pos = self._split_pos
        info_arr = bytearray(info_len)
        for i in range(0, info_len):
            if info_pos >= PacketDef.PACKET_SPLIT_BUFFER_SIZE.value:
                info_pos = 0
            info_arr[i] = self._byte_arr[info_pos]
            info_pos += 1
        # s_i = bytes(info_arr).decode(encoding='utf8') 可能触发UnicodeDecodeError
        s_i = 'datalen:{},arrlen:{},bytes:{}'.format(self._data_len, len(info_arr), bytes(info_arr))
        self.clear()            # 先取出异常打印字符串,再clear
        raise PacketError(s_i)
        
