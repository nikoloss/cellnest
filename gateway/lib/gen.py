#coding: utf8
import uuid
import time


class Gen(object):

    node_id = str(uuid.getnode())
    gtime = 0
    gid = 0

    @staticmethod
    def global_id():
        now = int(time.time())
        if Gen.gtime == now:
            Gen.gid += 1
        else:
            Gen.gid = 0
        Gen.gtime = now
        return ''.join([Gen.node_id, str(now), str(Gen.gid)])