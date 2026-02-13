deprecated

`@customize_repr` will be removed in the future because [`@customize`](https://15r10nk.github.io/inline-snapshot/development/plugin/#customize-examples) provides the same and even more features. You should use

conftest.py

```
class InlineSnapshotPlugin:
    @customize
    def my_class_handler(value, builder):
        if isinstance(value, MyClass):
            return builder.create_code("my_class_repr")
```

instead of

conftest.py

```
@customize_repr
def my_class_handler(value: MyClass):
    return "my_class_repr"
```

`@customize` allows you not only to generate code but also imports and function calls which can be analysed by inline-snapshot.

That said, what is/was `@customize_repr` for?

`repr()` can be used to convert a Python object into a source code representation of the object, but this does not work for every type. Here are some examples:

```
>>> repr(int)
"<class 'int'>"

>>> from enum import Enum
>>> E = Enum("E", ["a", "b"])
>>> repr(E.a)
'<E.a: 1>'
```

`customize_repr` can be used to overwrite the default `repr()` behaviour.

The implementation for `MyClass` could look like this:

my_class.py

```
class MyClass:
    def __init__(self, values):
        self.values = values.split()

    def __repr__(self):
        return repr(self.values)

    def __eq__(self, other):
        if not isinstance(other, MyClass):
            return NotImplemented
        return self.values == other.values
```

You can specify the `repr()` used by inline-snapshot in your *conftest.py*

conftest.py

```
from my_class import MyClass
from inline_snapshot import customize_repr


@customize_repr
def _(value: MyClass):
    return f"{MyClass.__qualname__}({' '.join(value.values) !r})"
```

This implementation is then used by inline-snapshot if `repr()` is called during code generation, but not in normal code.

```
from my_class import MyClass
from inline_snapshot import snapshot


def test_my_class():
    e = MyClass("1 5 hello")

    # normal repr
    assert repr(e) == "['1', '5', 'hello']"

    # the special implementation to convert the Enum into code
    assert e == snapshot(MyClass("1 5 hello"))
```

Note

The example above can be better handled with [`@customize`](https://15r10nk.github.io/inline-snapshot/development/plugin/#customize-examples) as shown in the [plugin documentation](https://15r10nk.github.io/inline-snapshot/development/plugin/index.md).

## customize recursive repr

You can also use `repr()` inside `__repr__()` if you want to make your own type compatible with inline-snapshot.

```
from enum import Enum
from inline_snapshot import snapshot


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


E = Enum("E", ["a", "b"])


def test_enum():

    # the special repr implementation is used recursively here
    # to convert every Enum to the correct representation
    assert Pair(E.a, [E.b]) == snapshot(Pair(E.a, [E.b]))
```

Note

using `f"{obj!r}"` or `PyObject_Repr()` will not work, because inline-snapshot replaces `builtins.repr` during the code generation. The only way to use the custom repr implementation is to use the `repr()` function.

Note

This implementation allows inline-snapshot to use the custom `repr()` recursively, but it does not allow you to use [unmanaged](https://15r10nk.github.io/inline-snapshot/development/eq_snapshot/#unmanaged-snapshot-values) snapshot values like `Pair(Is(some_var),5)`

You can also customize the representation of data types in other libraries:

```
from inline_snapshot import customize_repr
from other_lib import SomeType


@customize_repr
def _(value: SomeType):
    return f"SomeType(x={repr(value.x)})"
```
