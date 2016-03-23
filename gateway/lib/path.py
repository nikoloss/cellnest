# coding=utf-8
import os
from autoconf import conf_drawer

HOME_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BIZ_PATH = os.path.join(HOME_PATH, 'biz')
ETC_PATH = os.path.join(HOME_PATH, 'etc')
LIB_PATH = os.path.join(HOME_PATH, 'lib')


@conf_drawer.register_my_setup()
def all_beautiful_memories_begin():
    import log
    files_list = os.listdir(BIZ_PATH)
    files_list = set(['biz.' + x[:x.rfind(".")] for x in files_list if x.endswith(".py")])
    map(__import__, files_list)
