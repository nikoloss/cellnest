# coding: utf8
import sys, inspect
from lib.log import app_log
import http
import functools



class Router(object):
    services = {}
    GET = 1
    POST = 1 << 1
    PUT = 1 << 2
    DELETE = 1 << 3

    @staticmethod
    def routine(**kwargs):

        def _register(func):
            url = kwargs['url']
            method = kwargs.get('method', Router.GET | Router.POST)
            timeout = str(kwargs.get('timeout', 0))
            if Router.services.get(url):
                app_log.fatal('Url Conflict: [%s]', url)
                sys.exit(1)
            Router.services[url] = {
                'method': method,
                'timeout': timeout or '',
                'key': inspect.stack()[1][3],
                'func': func
            }
            return func
        return _register

    @staticmethod
    def dispatch(source_id, url, seed_id, method, params, url_params, callwrap):
        service = Router.services.get(url)
        key = service['key']
        func = service['func']
        if not int(method) & service['method']:
            raise http.HttpMethodNotAllowed()
        klass = func.func_globals[key]
        instance = klass()
        if url_params:
            ifunc = functools.partial(func, instance, params, *url_params)
        else:
            ifunc = functools.partial(func, instance, params)
        callwrap(ifunc, source_id, seed_id)

    @staticmethod
    def register_urls(exporter):
        for serv_ident, service in Router.services.iteritems():
            exporter.send(['train', serv_ident, service['timeout'], serv_ident])