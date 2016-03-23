# coding: utf8
import zmq
import time
from collections import deque
from lib.eloop import Handler, IOLoop, Timeout
from trie import search_server, train
from lib.log import app_log
from lib.autoconf import E

try:
    import ujson as json
except ImportError:
    import json

BUFFER_SZ = 100
HEARTBEAT_CC = 5
timeouts = {}
serv_hb = {}


def connect(subject, sub_func, object, obj_func):
    sub_function = getattr(subject, sub_func)
    obj_function = getattr(object, obj_func)

    def _deco_func(sfunc, ofunc):
        def _deco_params(*args, **kwargs):
            sfunc(*args, **kwargs) | E(ofunc)

        return _deco_params

    sub_function = _deco_func(sub_function, obj_function)
    setattr(subject, sub_func, sub_function)


class Server(object):
    def __init__(self, timeout_conf, serv_ident, function_id):
        self.timeout_conf = int(timeout_conf) if timeout_conf else None
        self.serv_ident = serv_ident
        self.function_id = function_id


class Front(Handler):
    def __init__(self, sock, root, ioloop=IOLoop.instance()):
        self._ioloop = ioloop
        self._sock = sock
        self._root = root
        self._buffer = deque(maxlen=BUFFER_SZ)
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

    def on_timeout(self, source_ident, seed_id):
        self.send([source_ident, seed_id, '408', 'timeout'])
        if timeouts.get(seed_id):
            timeouts.pop(seed_id)

    def on_recv(self, frame):
        ret = None
        source_ident, seed_id, path, method, params = frame
        url_fragments = path.split('/')
        url_params = []
        servers = search_server(self._root, url_fragments, url_params)
        if not servers:
            self.send([source_ident, seed_id, '404', 'resource is not found!'])
            return
        to_be_del = []
        for server in servers:
            been = (time.time() - serv_hb[server.serv_ident])
            if been > 2 * HEARTBEAT_CC:
                app_log.warn('[%s] has lost contact for %f minute', server.function_id, been)
                if been > 10 * HEARTBEAT_CC:
                    app_log.info('[%s] removed!', server.function_id)
                    # servers.remove(server)
                    to_be_del.append(server)
            else:
                if server.timeout_conf:
                    timeout = Timeout(
                        time.time() + max(server.timeout_conf, 1),
                        self.on_timeout,
                        source_ident,
                        seed_id
                    )
                    self._ioloop.add_timeout(timeout)
                ret = [server.serv_ident, source_ident, server.function_id, seed_id, method, json.dumps(url_params), params]
                break
        else:
            self.send([source_ident, seed_id, '502', 'resource temporary unavailable'])
        if to_be_del:
            map(servers.remove, to_be_del)
        return ret


    def _handle_recv(self):
        frame = self._sock.recv_multipart()
        self.on_recv(frame)

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


class Backend(Handler):
    def __init__(self, sock, root, ioloop=IOLoop.instance()):
        self._ioloop = ioloop
        self._sock = sock
        self._root = root
        self._buffer = deque(maxlen=BUFFER_SZ)
        self._flag = zmq.POLLIN
        self._ioloop.add_handler(self._sock, self.handle, self._flag)

    def send(self, frame):
        if not frame:
            return
        try:
            self._sock.send_multipart(frame, zmq.NOBLOCK)
        except zmq.Again:
            self._buffer.append(frame)
            self._flag |= zmq.POLLOUT
            self._ioloop.update_handler(self._sock, self._flag)
        except Exception as e:
            app_log.exception(e)

    def on_recv(self, frame):
        if len(frame) > 1:
            server_id = frame[0]
            # any response will be regarded as heartbeat
            serv_hb[server_id] = time.time()
            flag = frame[1]
            if flag == 'rep':
                self.on_response(frame)
            elif flag == 'train':
                self.on_train(frame)
        else:
            app_log.warn('Unknown response: %s', str(frame))

    def on_response(self, frame):
        server_id, flag, source_id, seed_id, state, content = frame
        return [source_id, seed_id, state, content]

    def on_train(self, frame):
        server_id, flag, path, timeout_conf, function_id = frame
        serv_node = Server(timeout_conf, server_id, function_id)
        train(self._root, path.split('/'), serv_node)

    def _handle_recv(self):
        frame = self._sock.recv_multipart()
        self.on_recv(frame)

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
