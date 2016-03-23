# coding: utf8
from lib.router import Router


class Hello(object):
    @Router.routine(url='api/hello/(\w+)', method=Router.POST | Router.GET, timeout=5)
    def test(self, params, name):
        age = params.get('age', '13')
        return 'hello! My name is ' + name + ', I\'m ' + age + ' years old'
