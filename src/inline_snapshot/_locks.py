from threading import RLock

snapshot_lock = RLock()


def locked(f):
    def w(*a, **ka):
        __tracebackhide__ = True
        with snapshot_lock:
            return f(*a, **ka)

    return w
