import redis
import threading


class ConnectRedis(object):
    _instance_lock = threading.Lock()

    def __init__(self):
        pass

    def __new__(cls, *args, **kwargs):
        if not hasattr(ConnectRedis, "r"):
            with ConnectRedis._instance_lock:
                if not hasattr(ConnectRedis, "r"):
                    ConnectRedis.r = redis.StrictRedis(decode_responses=True)
        return ConnectRedis.r
