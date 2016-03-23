# coding: utf8

import zmq
import getopt, functools

from lib.log import app_log
from lib import path
from lib.autoconf import *
from lib.eloop import IOLoop
from lib.device import Exporter
from lib.router import Router

HEARTBEAT_CC = 3.0  # 心跳周期

exporter = None
context = zmq.Context()


@conf_drawer.register_my_setup(look='connect')
def init(conf_file):
    global exporter
    #automic scan dirs
    files_list = os.listdir(path.BIZ_PATH)
    files_list = set([x[:x.rfind(".")] for x in files_list if x.endswith(".py")])
    map(__import__, ['biz.' + x for x in files_list])
    sock = context.socket(zmq.DEALER)
    sock.connect('tcp://' + conf_file)
    exporter = Exporter(sock)
    Router.register_urls(exporter)
    IOLoop.instance().set_idel_call(functools.partial(exporter.send, ['echo']))




if __name__ == '__main__':
    opts, argvs = getopt.getopt(sys.argv[1:], "c:f:b:")
    includes = None
    for op, value in opts:
        if op == '-c':
            includes = value
    if not includes:
        includes = os.path.join(path.ETC_PATH, 'etc.json')
        print "no configuration found!,will use [%s] instead" % includes
    includes = os.path.join(path.ETC_PATH, 'etc.json')
    cpff = ConfigParserFromFile()
    includes | E(cpff.parseall) | E(conf_drawer.setup)

    app_log.info('backend server started!')
    IOLoop.instance().start()