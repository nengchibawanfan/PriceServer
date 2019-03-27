import redis
import threading

from priceserver.conf.settings import REDIS_HOST, REDIS_PORT


class ConnectRedis(object):
    _instance_lock = threading.Lock()

    def __init__(self):
        pass

    def __new__(cls, *args, **kwargs):
        if not hasattr(ConnectRedis, "r"):
            with ConnectRedis._instance_lock:
                if not hasattr(ConnectRedis, "r"):
                    ConnectRedis.r = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        return ConnectRedis.r
