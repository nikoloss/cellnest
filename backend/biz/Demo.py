# coding: utf8
from lib.router import Router


class Hello(object):
    @Router.routine(url='api/hello/(\w+)', method=Router.POST | Router.GET, timeout=5)
    def test(self, params, name):
        '''params是表单数据没有则为空字典，name为正则表达式捕获的参数，
            如果有多个正则参数会依次注入到函数的参数列表中
        '''
        age = params.get('age', '13')
        return 'hello! My name is ' + name + ', I\'m ' + age + ' years old'
