# -*- coding: UTF-8 -*-

from  multiprocessing import freeze_support, Event as PeEvent
from threading import Event as ThEvent;
import time

from dogwood.core.network.ws_client_connect import WSClientConnect
from dogwood.core.logger import LogInit
from dogwood.core.global_var import GlobalVar

from cltlogic.game_define import GameDefine
from cltlogic.logic_main import LogicMain

def main():
    freeze_support()   #  windows下multiprocessing使用pyinstaller需要
    LogInit('pressure_clt')
    
    pe_evt = PeEvent()
    net_clt = WSClientConnect(GameDefine.NET_NAME.value, pe_evt, GameDefine.NET_ID.value, '127.0.0.1', 8899)  
    net_clt.start()
    pe_evt.wait()
    
    th_evt = ThEvent()
    game_main = LogicMain(th_evt, 100)
    game_main.add_net(net_clt)
    game_main.start()
    th_evt.wait()
    GlobalVar.set_value('game_main', game_main)
    
    time.sleep(1)
    while True:
        cmd_line = input('输入命令:\n')
        if cmd_line.lower() == 'quit':
            net_clt.quit()
            net_clt.join()
            
            game_main.quit()
            game_main.join()
            
            break

if __name__ == '__main__':
    main()

