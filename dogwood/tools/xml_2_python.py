# -*- coding: UTF-8 -*-

import sys
import os
import xml.dom.minidom

g_xml_path = sys.argv[1] 
g_py_path = sys.argv[2] 
trans_files_dict = {}    # key为xml文件, value 为python文件

def list_dir():
    trans_files_dict.clear()
    
    for xml_fl in os.listdir(g_xml_path):
        if ((xml_fl.split('.')[-1]).lower() == 'xml'):
            py_fl = xml_fl[:-3] + 'py'        
            in_fl = os.path.join(g_xml_path, xml_fl)
            out_fl = os.path.join(g_py_path, py_fl)
            if os.path.isfile(in_fl):
                trans_files_dict[in_fl] = out_fl
                
def trans_xml_to_py(src_fl, dst_fl):
    str_content = parse_xml_content(src_fl)
    create_py_file(dst_fl, str_content)

def create_py_file(out_file_name, str_content):
    encode_str = '# -*- coding: UTF-8 -*-'
    pre_fix = '#以下是自动生成部分不要手动修改'
    suf_fix = '#以上是自动生成部分不要手动修改'
    ipt_str = 'from enum import Enum'
    
    all_input = encode_str + '\n\n' + pre_fix + '\n\n' + ipt_str + '\n\n' + str_content + '\n' + suf_fix
    f = open(out_file_name, mode="w", encoding ='UTF-8')
    f.writelines(all_input)
    f.close()
    
def parse_xml_content(xml_fl_name):
    ret_content = ''
    try:
        xml_dom=xml.dom.minidom.parse(xml_fl_name)
    except Exception as e:
        print(e, xml_fl_name)
        os._exit(-1)
    # 先取得msgid
    msg_id_title = xml_fl_name.split('/')[-1]
    msg_id_title = msg_id_title[:-4]
    msg_id_title = msg_id_title.capitalize()
    msg_id_title += 'MsgId'
    ret_content += ('class ' + msg_id_title + '(Enum):\n')
    mids = xml_dom.getElementsByTagName('mid')
    for mid in mids:                        # mid
        str_mid = '    ' + mid.getAttribute('dname').upper() + ' = ' + mid.getAttribute('value') + '  # ' + mid.getAttribute('memo')
        ret_content += str_mid
        ret_content += '\n'
    ret_content += '\n'
    for mid in mids:  # nid
        nids = mid.getElementsByTagName('nid')
        for nid in nids:
            str_nid = '    ' + nid.getAttribute('cname').upper() + ' = ' + nid.getAttribute('value') + '  # ' + nid.getAttribute('dmemo')
            ret_content += str_nid
            ret_content += '\n'
    ret_content += '\n'
    
    return ret_content
    
def main():
    if not os.path.exists(g_xml_path):
        return
    if not os.path.exists(g_py_path):
        return
    
    list_dir()        
    for k, v in trans_files_dict.items():
        trans_xml_to_py(k, v)
        print(k, v)
    

if __name__ == "__main__":
    main()
    print('转换完成')