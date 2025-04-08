


`repr()` can be used to convert a python object into a source code representation of the object, but this does not work for every type.
Here are some examples:

```pycon
>>> repr(int)
"<class 'int'>"

>>> from enum import Enum
>>> E = Enum("E", ["a", "b"])
>>> repr(E.a)
'<E.a: 1>'
```

`customize_repr` can be used to overwrite the default `repr()` behaviour.

The implementation for `Enum` looks like this:

``` python exec="1" result="python"
print('--8<-- "src/inline_snapshot/_code_repr.py:Enum"')
```

This implementation is then used by inline-snapshot if `repr()` is called during the code generation, but not in normal code.

<!-- inline-snapshot: create fix first_block outcome-passed=1 -->
``` python
from inline_snapshot import snapshot
from enum import Enum


def test_enum():
    E = Enum("E", ["a", "b"])

    # normal repr
    assert repr(E.a) == "<E.a: 1>"

    # the special implementation to convert the Enum into a code
    assert E.a == snapshot(E.a)
```

## built-in data types

inline-snapshot comes with a special implementation for the following types:

``` python exec="1"
from inline_snapshot._code_repr import code_repr_dispatch, code_repr

for name, obj in sorted(
    (
        getattr(
            obj, "_inline_snapshot_name", f"{obj.__module__}.{obj.__qualname__}"
        ),
        obj,
    )
    for obj in code_repr_dispatch.registry.keys()
):
    if obj is not object:
        print(f"- `{name}`")
```

Please open an [issue](https://github.com/15r10nk/inline-snapshot/issues) if you found a built-in type which is not supported by inline-snapshot.

!!! note
    Container types like `dict`, `list`, `tuple` or `dataclass` are handled in a different way, because inline-snapshot also needs to inspect these types to implement [unmanaged](/eq_snapshot.md#unmanaged-snapshot-values) snapshot values.


## customize recursive repr

You can also use `repr()` inside `__repr__()`, if you want to make your own type compatible with inline-snapshot.

<!-- inline-snapshot: create fix first_block outcome-passed=1 -->
``` python
from inline_snapshot import snapshot
from enum import Enum


class Pair:
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __repr__(self):
        # this would not work
        # return f"Pair({self.a!r}, {self.b!r})"

        # you have to use repr()
        return f"Pair({repr(self.a)}, {repr(self.b)})"

    def __eq__(self, other):
        if not isinstance(other, Pair):
            return NotImplemented
        return self.a == other.a and self.b == other.b


def test_enum():
    E = Enum("E", ["a", "b"])

    # the special repr implementation is used recursive here
    # to convert every Enum to the correct representation
    assert Pair(E.a, [E.b]) == snapshot(Pair(E.a, [E.b]))
```

!!! note
    using `#!python f"{obj!r}"` or `#!c PyObject_Repr()` will not work, because inline-snapshot replaces `#!python builtins.repr` during the code generation. The only way to use the custom repr implementation is to use the `repr()` function.

!!! note
    This implementation allows inline-snapshot to use the custom `repr()` recursively, but it does not allow you to use [unmanaged](/eq_snapshot.md#unmanaged-snapshot-values) snapshot values like `#!python Pair(Is(some_var),5)`


you can also customize the representation of data types in other libraries:

``` python
from inline_snapshot import customize_repr
from other_lib import SomeType


@customize_repr
def _(value: SomeType):
    return f"SomeType(x={repr(value.x)})"
```
