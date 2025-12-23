import inspect

from inline_snapshot._exceptions import UsageError


def check_args(func, allowed):
    sign = inspect.signature(func)
    for p in sign.parameters.values():
        if p.default is not inspect.Parameter.empty:
            raise UsageError(f"`{p.name}` has a default value which is not supported")

        if p.kind != inspect.Parameter.POSITIONAL_OR_KEYWORD:
            raise UsageError(
                f"`{p.name}` is not a positional or keyword parameter, which is not supported"
            )

        if p.name not in allowed:
            raise UsageError(
                f"`{p.name}` is an unknown parameter. allowed are {allowed}"
            )


def partial_call(func, args):
    sign = inspect.signature(func)
    used = [p.name for p in sign.parameters.values()]
    return func(**{n: args[n] for n in used})
