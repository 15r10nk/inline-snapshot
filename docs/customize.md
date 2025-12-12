`@customize` allows you to register special hooks that control how inline-snapshot generates your snapshots.
You should use it when you find yourself manually editing snapshots after they were created by inline-snapshot.

inline-snapshot calls each hook until it finds one that returns a custom object, which can be created with the `create_*` methods of the [`Builder`][inline_snapshot.Builder].

One use case might be that you have a dataclass with a special constructor function that can be used for certain instances of this dataclass, and you want inline-snapshot to use this constructor when possible.


<!-- inline-snapshot: create fix first_block outcome-passed=1 -->
``` python
from dataclasses import dataclass

from inline_snapshot import customize
from inline_snapshot import Builder
from inline_snapshot import snapshot


@dataclass
class Rect:
    width: int
    height: int

    @staticmethod
    def make_quadrat(size):
        return Rect(size, size)


@customize
def quadrat_handler(value, builder: Builder):
    if isinstance(value, Rect) and value.width == value.height:
        return builder.create_call(Rect.make_quadrat, [value.width])


def test_quadrat():
    assert Rect.make_quadrat(5) == snapshot(Rect.make_quadrat(5))  # (1)!
    assert Rect(1, 1) == snapshot(Rect.make_quadrat(1))  # (2)!
    assert Rect(1, 2) == snapshot(Rect(width=1, height=2))  # (3)!
```

1. Your handler is used because you created a quadrat
2. Your handler is used because you created a rect that happens to have the same width and height
3. Your handler is not used because width and height are different


It can also be used to teach inline-snapshot to use specific dirty-equals expressions for specific values.


<!-- inline-snapshot: create fix first_block outcome-passed=1 -->
``` python
from dataclasses import dataclass

from inline_snapshot import customize
from inline_snapshot import Builder
from inline_snapshot import snapshot

from dirty_equals import IsNow
from datetime import datetime


@customize
def quadrat_handler(value, builder: Builder):
    if value == IsNow():
        return builder.create_call(IsNow)


def test_quadrat():
    assert datetime.now() == snapshot(IsNow())
```




::: inline_snapshot
    options:
      heading_level: 3
      members: [customize,Builder,Custom,CustomizeHandler]
      show_root_heading: false
      show_bases: false
      show_source: false
