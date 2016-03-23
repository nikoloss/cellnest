# coding: utf8
import re


class ServNode(object):
    __slots__ = ['kw', 'reg', 'servers', 'leafs']
    def __init__(self, kw):
        self.kw = kw
        self.reg = re.compile(kw)  # regex
        self.servers = []
        self.leafs = []


def train(current_node, words, server):
    if not words:
        current_node.servers.append(server)
        current_node.servers.reverse()
        return
    else:
        for serv_node in current_node.leafs:
            if words[0] == serv_node.kw:
                train(serv_node, words[1:], server)
                break
        else:
            serv_node = ServNode(words[0])
            current_node.leafs.append(serv_node)
            train(serv_node, words[1:], server)


def search_server(current_node, words, params=[]):
    if not words:
        return current_node.servers
    for serv_node in current_node.leafs:
        m = re.match(serv_node.reg, words[0])
        if m:
            params += m.groups()
            return search_server(serv_node, words[1:], params)
    else:
        return


if __name__ == '__main__':
    begin = ServNode('ROOT')
    urls = [
        ['path', 'com', '([a-zA-Z]+)', '(\d+)'],
        ['path', 'com', '400', 'ok'],
        ['other', 'st']
    ]
    # train(begin, urls[0], 'serv#1')
    # train(begin, urls[0], 'serv#12')
    # train(begin, urls[1], 'serv#2')
    # train(begin, urls[2], 'serv#3')
    params = []

    node = search_server(begin, ['path', 'tt', 'www', '71'], params)
    print '==============================='
    if node:
        print '[result] = ', node, params
