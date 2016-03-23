# coding: utf8
import zmq
import getopt
from serv import device, trie
from lib.eloop import IOLoop
from lib import path
from lib.autoconf import *
from lib.log import app_log

front_dist = "tcp://*:{front}"
backend_dist = "tcp://*:{backend}"
context = zmq.Context()
front_handler = None
backend_handler = None
serv_node_trie = trie.ServNode('ROOT')

#===========TEST==============
serv_node = device.Server('', 'identify', '15')
trie.train(serv_node_trie, ['ok', 'test'], serv_node)



@conf_drawer.register_my_setup(look='router')
def setup(conf):
    global front_dist, backend_dist, front_handler, backend_handler
    front_dist = front_dist.format(front=conf['front'])
    backend_dist = backend_dist.format(backend=conf['backend'])
    front_sock = context.socket(zmq.ROUTER)
    front_sock.bind(front_dist)
    backend_sock = context.socket(zmq.ROUTER)
    backend_sock.bind(backend_dist)
    front_handler = device.Front(front_sock, serv_node_trie)
    backend_handler = device.Backend(backend_sock, serv_node_trie)
    device.connect(front_handler, 'on_recv', backend_handler, 'send')
    device.connect(backend_handler, 'on_response', front_handler, 'send')


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

    app_log.info('checked! All Green...')
    IOLoop.instance().start()
