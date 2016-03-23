# coding:utf8
import zmq
from zmq.eventloop.zmqstream import ZMQStream
from lib.gen import Gen
from tornado.log import app_log
from lib.autoconf import conf_drawer

try:
    import ujson as json
except ImportError:
    import json


@conf_drawer.register_my_setup(look='router')
def setup(dist):
    ZBus.instance().connect(dist)


class ZBus(object):
    def __init__(self):
        self._context = zmq.Context()
        self._callback = {}
        self._zstream = None

    @staticmethod
    def instance():
        if not hasattr(ZBus, '_instance'):
            ZBus._instance = ZBus()
        return ZBus._instance

    @staticmethod
    def initialized():
        return hasattr(ZBus, '_instance')

    def connect(self, dist):
        if self._zstream:
            self._zstream.close()
        self._zsock = self._context.socket(zmq.XREQ)
        self._zsock.connect('tcp://{dist}'.format(dist=dist))
        self._zstream = ZMQStream(self._zsock)
        self._zstream.on_recv(self.on_recv)

    def send(self, request, callback):
        self._callback[request.seed_id] = callback
        self._zstream.send_multipart(request.box())

    def on_recv(self, frame):
        response = ZResponse(frame)
        callback = self._callback.pop(response.seed_id) if self._callback.get(response.seed_id) else None
        if callback and callable(callback):
            callback(response)


class ZRequest(object):
    def __init__(self, path, method, dict_args, gen=Gen.global_id):
        self.seed_id = gen()
        self.path = str(path)
        self.method = method
        self.params = json.dumps(dict_args)

    def box(self):
        return [self.seed_id, self.path, self.method, self.params]


class ZResponse(object):
    def __init__(self, frame):
        self.seed_id, self.state, self.content = frame
        self.state = int(self.state) if self.state else None
