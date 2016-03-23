# coding: utf8

import getopt
import tornado.ioloop
import tornado.web
from biz.core import Application
from zmq.eventloop.ioloop import ZMQIOLoop
from lib.autoconf import *
from lib import path
from tornado.log import app_log

loop = ZMQIOLoop()
loop.install()


if __name__ == "__main__":
    # init
    port = 8888
    includes = None
    opts, argvs = getopt.getopt(sys.argv[1:], "c:p:")
    for op, value in opts:
        if op == '-c':
            includes = value
        elif op == '-p':
            port = int(value)
    if not includes:
        includes = os.path.join(path.ETC_PATH, 'etc.json')
        print "no configuration found!,will use [%s] instead" % includes
    cpff = ConfigParserFromFile()
    includes | E(cpff.parseall) | E(conf_drawer.setup)
    app = Application()
    app.listen(port)
    app_log.info('starting...')
    tornado.ioloop.IOLoop.instance().start()
