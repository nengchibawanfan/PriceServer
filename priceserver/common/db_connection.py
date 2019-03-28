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
                    ConnectRedis.r = redis.StrictRedis(host="127.0.0.1", port=6379, decode_responses=True)
        return ConnectRedis.r

if __name__ == '__main__':
    r = ConnectRedis()
    print(r)