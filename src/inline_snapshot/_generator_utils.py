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
