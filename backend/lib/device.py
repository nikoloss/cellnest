# coding: utf8
import zmq
import http
from collections import deque
from eloop import Handler, IOLoop
from log import app_log
from router import Router

try:
    import ujson as json
except ImportError:
    import json

from concurrent import futures

MAX_WORKERS = 8
executor = futures.ThreadPoolExecutor(max_workers=MAX_WORKERS)


def on_thread(**conf):
    global executor
    t_executor = conf.get('executor') or executor

    def _deco_func(func):
        def _deco_params(*args, **kwargs):
            t_executor.submit(func, *args, **kwargs)

        return _deco_params

    return _deco_func


class Exporter(Handler):
    def __init__(self, sock, ioloop=IOLoop.instance()):
        self._ioloop = ioloop
        self._sock = sock
        self._buffer = deque(maxlen=100)
        self._flag = zmq.POLLIN
        self._ioloop.add_handler(self._sock, self.handle, self._flag)

    def send(self, frame):
        try:
            self._sock.send_multipart(frame, zmq.NOBLOCK)
        except zmq.Again:
            self._buffer.append(frame)
            self._flag |= zmq.POLLOUT
            self._ioloop.update_handler(self._sock, self._flag)
        except Exception as e:
            app_log.exception(e)

    def _handle_send(self):
        try:
            frame = self._buffer.popleft()
            self._sock.send_multipart(frame, zmq.NOBLOCK)
        except IndexError:
            self._flag &= (~zmq.POLLOUT)
            self._ioloop.update_handler(self._sock, self._flag)
        except Exception as e:
            app_log.exception(e)
            self._flag &= (~zmq.POLLOUT)
            self._ioloop.update_handler(self._sock, self._flag)

    def _handle_recv(self):
        source_id, url, seed_id, method, url_params, params = self._sock.recv_multipart()
        try:
            params = json.loads(params)
            Router.dispatch(source_id, url, seed_id, method, params, json.loads(url_params), self.on_wrap)
        except http.HttpMethodNotAllowed as e:
            self._ioloop.add_callback(self.send, ['rep', source_id, seed_id, e.state, e.content])
        except Exception as e:
            self._ioloop.add_callback(self.send, ['rep', source_id, seed_id, '500', '(500): internal error'])
            app_log.exception(e)

    @on_thread()
    def on_wrap(self, func, source_id, seed_id):
        try:
            ret = func()
            if isinstance(ret, unicode):
                ret = ret.encode()
            elif not isinstance(ret, str):
                ret = json.dumps(ret)
            self._ioloop.add_callback(self.send, ['rep', source_id, seed_id, '200', ret])
        except Exception as e:
            self._ioloop.add_callback(self.send, ['rep', source_id, seed_id, '500', '(500): internal error'])
            app_log.exception(e)
