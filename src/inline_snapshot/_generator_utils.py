from collections import namedtuple

IterResult = namedtuple("IterResult", "value list")


def split_gen(gen):
    it = iter(gen)
    l = []
    while True:
        try:
            l.append(next(it))
        except StopIteration as stop:
            return IterResult(stop.value, l)


def only_value(gen):
    return split_gen(gen).value


def gen_map(stream, f):
    stream = iter(stream)
    while True:
        try:
            yield f(next(stream))
        except StopIteration as stop:
            return stop.value


def with_flag(stream, flag):
    def map(change):
        change.flag = flag
        return change

    return gen_map(stream, map)


def make_gen_map(f):
    def m(stream):

        return gen_map(stream, f)

    return m
