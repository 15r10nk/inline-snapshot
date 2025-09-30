custom_functions = []


def customize(f):
    custom_functions.append(f)
    return f


class Custom:
    pass


class Default:
    def __init__(self, value):
        self.value = value


def unwrap_default(value):
    if isinstance(value, Default):
        return value.value
    return value


class CustomCall(Custom):
    def __init__(self, function, *args, **kwargs):
        """
        CustomCall(f,1,2,a=3).kwonly(b=4)
        """
        self._function = function
        self._args = args
        self._kwargs = kwargs
        self._kwonly = {}

    @property
    def args(self):
        return self._args

    @property
    def all_pos_args(self):
        return [*self._args, *self._kwargs.values()]

    @property
    def kwargs(self):
        return {**self._kwargs, **self._kwonly}

    def kwonly(self, **kwonly):
        assert not self._kwonly, "you should not call kwonly twice"
        assert (
            not kwonly.keys() & self._kwargs.keys()
        ), "same keys in kwargs and kwonly arguments"
        self._kwonly = kwonly
        return self

    def argument(self, pos_or_str):
        if isinstance(pos_or_str, int):
            return unwrap_default(self.all_pos_args[pos_or_str])
        else:
            return unwrap_default(self.kwargs[pos_or_str])

    def map(self, f):
        return self._function(
            *[f(unwrap_default(x)) for x in self._args],
            **{k: f(unwrap_default(v)) for k, v in self.kwargs.items()},
        )


def get_handler(v):
    for f in reversed(custom_functions):
        r = f(v)
        if isinstance(r, Custom):
            return r
