# coding: utf8
import time
import thread
import threading
import functools
import zmq
import numbers
import heapq
from log import app_log as log


class Handler(object):
    def handle(self, event):
        if event & zmq.POLLIN:
            self._handle_recv()
        elif event & zmq.POLLOUT:
            self._handle_send()

    def _handle_recv(self):
        raise NotImplementedError

    def _handle_send(self):
        raise NotImplementedError


class Waker(Handler):
    def __init__(self):
        self._ctx = zmq.Context()
        self._reader = self._ctx.socket(zmq.PULL)
        self._writer = self._ctx.socket(zmq.PUSH)
        self._reader.bind('inproc://IOLOOPWAKER')
        self._writer.connect('inproc://IOLOOPWAKER')

    def fileno(self):
        return self._reader

    def _handle_recv(self):
        try:
            self._reader.recv(zmq.NOBLOCK)
        except zmq.ZMQError:
            pass

    def wake_up(self):
        try:
            self._writer.send(b'x', zmq.NOBLOCK)
        except zmq.ZMQError:
            pass


class Timeout(object):
    __slots__ = ['deadline', 'callback', 'cancelled']

    def __init__(self, deadline, callback, *args, **kwargs):
        if not isinstance(deadline, numbers.Real):
            raise TypeError("Unsupported deadline %r" % deadline)
        self.deadline = deadline
        self.callback = functools.partial(callback, *args, **kwargs)
        self.cancelled = False
        # IOLoop.instance().add_callback(IOLoop.instance().add_timeout, self)

    def cancel(self):
        self.cancelled = True

    def __le__(self, other):
        return self.deadline <= other.deadline

    def __lt__(self, other):
        return self.deadline < other.deadline


class IOLoop(object):
    _instance_lock = threading.Lock()
    _local = threading.local()

    @staticmethod
    def instance():
        """Returns a global `IOLoop` instance.
        """
        if not hasattr(IOLoop, "_instance"):
            with IOLoop._instance_lock:
                if not hasattr(IOLoop, "_instance"):
                    # New instance after double check
                    IOLoop._instance = IOLoop()
        return IOLoop._instance

    @staticmethod
    def initialized():
        """Returns true if the singleton instance has been created."""
        return hasattr(IOLoop, "_instance")

    def __init__(self):
        self._handlers = {}
        self._callbacks = []
        self._callback_lock = threading.Lock()
        self._timeouts = []
        self._poller = zmq.Poller()
        self._idle_timeout = 3600.0
        self._thread_ident = -1
        self._waker = Waker()
        self.add_handler(self._waker.fileno(), self._waker.handle, zmq.POLLIN)

    def add_handler(self, fd, handler, flag):
        self._handlers[fd] = handler
        self._poller.register(fd, flag)

    def update_handler(self, fd, flag):
        self._poller.modify(fd, flag)

    def remove_handler(self, handler):
        fd = handler.fileno()
        self._handlers.pop(fd)
        self._poller.unregister(fd)

    def add_callback(self, callback, *args, **kwargs):
        with self._callback_lock:
            is_empty = not self._callbacks
            self._callbacks.append(functools.partial(callback, *args, **kwargs))
            if is_empty and self._thread_ident != thread.get_ident():
                self._waker.wake_up()

    def _run_callback(self, callback):
        try:
            callback()
        except Exception, e:
            log.exception(e)

    def add_timeout(self, timeout):
        heapq.heappush(self._timeouts, timeout)

    def start(self):

        self._thread_ident = thread.get_ident()

        while True:

            poll_time = self._idle_timeout

            with self._callback_lock:
                callbacks = self._callbacks
                self._callbacks = []

            for callback in callbacks:
                self._run_callback(callback)
            # 为什么把超时列表放到callbacks执行之后读取?
            # 因为:
            # 1.add_timeout的动作也是通过add_callback来完成的,callbacks执行可能会影响到timeouts长度
            # 2.callback在执行的时候也会耽误一些时间, 在callbacks执行之后判断timeout才是比较准确的
            due_timeouts = []
            now = time.time()
            while self._timeouts:
                lastest_timeout = heapq.heappop(self._timeouts)
                if not lastest_timeout.cancelled:
                    if lastest_timeout.deadline <= now:
                        due_timeouts.append(lastest_timeout)
                    else:
                        # 拿多了, 推进去, 顺便把poll()的时间确定出来
                        heapq.heappush(self._timeouts, lastest_timeout)
                        poll_time = lastest_timeout.deadline - time.time()  # 这个值有可能是负数,
                        poll_time = max(0.0, poll_time)  # 为负数的话变为0
                        break
            for timeout in due_timeouts:
                self._run_callback(timeout.callback)

            if self._callbacks:
                poll_time = 0.0

            sockets = dict(self._poller.poll(poll_time * 1000))
            if sockets:
                for sock, event in sockets.iteritems():
                    handler = self._handlers[sock]
                    try:
                        handler(event)
                    except Exception as e:
                        log.exception(e)
