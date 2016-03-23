# coding: utf8


class ServerErrs(Exception):
    state = '500'
    content = 'Gateway (500):internal error'


class ServerGone(ServerErrs):
    state = '502'
    content = 'Gateway (502):resource is temporary unavailable'
