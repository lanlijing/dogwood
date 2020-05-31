# -*- coding: UTF-8 -*-

from  multiprocessing import freeze_support, Event as PeEvent
from threading import Event as ThEvent;
import time
import random

from dogwood.core.helper import Helper
from dogwood.core.network.ws_server_listen import WSServerListen
from dogwood.core.logger import LogInit
from dogwood.core.global_var import GlobalVar

from svrlogic.svr_define import SvrDefine
from svrlogic.svr_main import SvrMain

def main():
    freeze_support()   #  windows下multiprocessing使用pyinstaller需要
    LogInit('pressure_svr')
    random.seed(Helper.get_time_stamp_second())
    
    pe_evt = PeEvent()
    net_clt = WSServerListen(SvrDefine.SVR_NET_NAME.value, pe_evt, SvrDefine.SVR_NET_ID.value, 8899)  
    net_clt.start()
    pe_evt.wait()
    
    th_evt = ThEvent()
    game_main = SvrMain(th_evt)
    game_main.add_net(net_clt)
    game_main.start()
    th_evt.wait()
    GlobalVar.set_value('svr_main', game_main)
    
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