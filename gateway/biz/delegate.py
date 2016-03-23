# coding: utf8
import urllib
import tornado.web

try:
    import json as json
except ImportError:
    import json
from biz.zbus import ZBus, ZRequest
from core import Application


@Application.register(path=r"^/([^\.|]*)(?!\.\w+)$")
class Xroute(tornado.web.RequestHandler):
    '''doorlet'''
    GET = 1
    POST = 1 << 1
    PUT = 1 << 2
    DELETE = 1 << 3

    def prepare(self):
        # 获得正确的客户端ip
        ip = self.request.headers.get("X-Real-Ip", self.request.remote_ip)
        ip = self.request.headers.get("X-Forwarded-For", ip)
        ip = ip.split(',')[0].strip()
        self.request.remote_ip = ip
        # 允许跨域请求
        req_origin = self.request.headers.get("Origin")
        if req_origin:
            self.set_header("Access-Control-Allow-Origin", req_origin)
            self.set_header("Access-Control-Allow-Credentials", "true")
            self.set_header("Allow", "GET, HEAD, POST")
            if self.request.method == "OPTIONS":
                self.set_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
                self.set_header("Access-Control-Allow-Headers", "Accept, Cache-Control, Content-Type")
                self.finish()
                return
            else:
                self.set_header("Cache-Control", "no-cache")
        # 分析请求参数
        self.dict_args = {}
        # json格式请求
        if self.request.headers.get('Content-Type', '').find("application/json") >= 0:
            try:
                self.dict_args = json.loads(self.request.body)
                if not self.json_args.get('ck'):
                    # 如果没有ck，尝试从cookie里面加载usercheck
                    self.json_args['ck'] = urllib.unquote(self.get_cookie('usercheck', ''))
                return
            except Exception as ex:
                self.send_error(400)
        # 普通参数请求
        else:
            self.dict_args = dict((k, v[-1]) for k, v in self.request.arguments.items())
            return

    @tornado.web.asynchronous
    def get(self, path):
        req = ZRequest(path, str(Xroute.GET), self.dict_args)
        ZBus.instance().send(req, self.handle_zresponse)

    @tornado.web.asynchronous
    def post(self, path):
        req = ZRequest(path, str(Xroute.POST), self.dict_args)
        ZBus.instance().send(req, self.handle_zresponse)

    @tornado.web.asynchronous
    def put(self, path):
        req = ZRequest(path, str(Xroute.PUT), self.dict_args)
        ZBus.instance().send(req, self.handle_zresponse)

    @tornado.web.asynchronous
    def delete(self, path):
        req = ZRequest(path, str(Xroute.DELETE), self.dict_args)
        ZBus.instance().send(req, self.handle_zresponse)

    def handle_zresponse(self, zresponse):
        state_code = zresponse.state
        if state_code:
            self.set_status(state_code)
        self.finish(zresponse.content)