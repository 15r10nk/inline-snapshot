import dataclasses
from collections import Counter
from collections import OrderedDict
from collections import UserDict
from collections import UserList
from collections import defaultdict
from collections import namedtuple
from dataclasses import dataclass
from typing import NamedTuple

import pytest

from inline_snapshot import HasRepr
from inline_snapshot import snapshot
from inline_snapshot._code_repr import code_repr
from inline_snapshot._sentinels import undefined
from inline_snapshot.testing import Example


def test_enum(check_update):

    assert (
        check_update(
            """
from enum import Enum

class color(Enum):
    val="val"


assert [color.val] == snapshot()

    """,
            flags="create",
        )
        == snapshot(
            """\

from enum import Enum

class color(Enum):
    val="val"


assert [color.val] == snapshot([color.val])

"""
        )
    )


def test_snapshot_generates_hasrepr():

    Example(
        """\
from inline_snapshot import snapshot

class Thing:
    def __repr__(self):
        return "<something>"

    def __eq__(self,other):
        if not isinstance(other,Thing):
            return NotImplemented
        return True

def test_thing():
    assert Thing() == snapshot()

    """
    ).run_pytest(
        ["--inline-snapshot=create"],
        returncode=snapshot(1),
        changed_files=snapshot(
            {
                "test_something.py": """\
from inline_snapshot import snapshot

from inline_snapshot import HasRepr

class Thing:
    def __repr__(self):
        return "<something>"

    def __eq__(self,other):
        if not isinstance(other,Thing):
            return NotImplemented
        return True

def test_thing():
    assert Thing() == snapshot(HasRepr(Thing, "<something>"))

    \
"""
            }
        ),
    ).run_pytest(
        ["--inline-snapshot=disable"], returncode=0
    ).run_pytest(
        returncode=0
    )


def test_hasrepr_type():
    assert 5 == HasRepr(int, "5")
    assert not "a" == HasRepr(int, "5")
    assert not HasRepr(float, "nan") == HasRepr(str, "nan")
    assert not HasRepr(str, "a") == HasRepr(str, "b")


def test_enum_in_dataclass(check_update):

    assert (
        check_update(
            """
from enum import Enum
from dataclasses import dataclass

class color(Enum):
    red="red"
    blue="blue"

@dataclass
class container:
    bg: color=color.red
    fg: color=color.blue

assert container(bg=color.red,fg=color.red) == snapshot()

    """,
            flags="create",
        )
        == snapshot(
            """\

from enum import Enum
from dataclasses import dataclass

class color(Enum):
    red="red"
    blue="blue"

@dataclass
class container:
    bg: color=color.red
    fg: color=color.blue

assert container(bg=color.red,fg=color.red) == snapshot(container(fg=color.red))

"""
        )
    )


def test_flag(check_update):

    assert (
        check_update(
            """
from enum import Flag, auto

class Color(Flag):
    red = auto()
    green = auto()
    blue = auto()

assert Color.red | Color.blue == snapshot()

    """,
            flags="create",
        )
        == snapshot(
            """\

from enum import Flag, auto

class Color(Flag):
    red = auto()
    green = auto()
    blue = auto()

assert Color.red | Color.blue == snapshot(Color.red | Color.blue)

"""
        )
    )


def test_type(check_update):

    assert (
        check_update(
            """\
class Color:
    pass

assert [Color,int] == snapshot()

    """,
            flags="create",
        )
        == snapshot(
            """\
class Color:
    pass

assert [Color,int] == snapshot([Color, int])

"""
        )
    )


def test_qualname():

    Example(
        """\
from enum import Enum
from inline_snapshot import snapshot


class Namespace:
    class Color(Enum):
        red="red"

def test():
    assert Namespace.Color.red == snapshot()

    """
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "test_something.py": """\
from enum import Enum
from inline_snapshot import snapshot


class Namespace:
    class Color(Enum):
        red="red"

def test():
    assert Namespace.Color.red == snapshot(Namespace.Color.red)

    \
"""
            }
        ),
    ).run_inline()


A = namedtuple("A", "a,b", defaults=[0])
B = namedtuple("B", "a,b", defaults=[0, 0])


class C(NamedTuple):
    a: int
    b: int = 0
    c: int = 0


@dataclass
class Dataclass:
    a: int
    b: int = dataclasses.field(default=0)
    c: list = dataclasses.field(default_factory=lambda: [])


default_dict = defaultdict(list)
default_dict[5].append(2)
default_dict[3].append(1)


@pytest.mark.parametrize(
    "d",
    [
        frozenset(["a"]),
        frozenset(),
        {"a"},
        set(),
        list(),
        ["a"],
        {},
        {1: "1"},
        (),
        (1,),
        (1, 2, 3),
        A(1, 2),
        A(1),
        A(0, 0),
        B(),
        B(b=5),
        C(1),
        C(1, 2),
        C(a=1, c=2),
        Dataclass(a=0, b=0, c=[]),
        Dataclass(a=1, b=2, c=[3]),
        default_dict,
        OrderedDict({1: 2, 3: 4}),
        UserDict({1: 2}),
        UserList([1, 2]),
        undefined,
    ],
)
def test_datatypes(d):
    code = code_repr(d)
    print("repr:     ", repr(d))
    print("code_repr:", code)
    assert d == eval(code)


def test_set():
    assert code_repr({1, 2, 3, "a", True, "b"}) == snapshot("{'a', 'b', 1, 2, 3}")
    assert code_repr({1j, 2j, 3j, "a", True, "b"}) == snapshot(
        "{'a', 'b', 1j, 2j, 3j, True}"
    )
    assert code_repr({1, 2, 3, 10, 11, 20, 200}) == snapshot(
        "{1, 2, 3, 10, 11, 20, 200}"
    )


def test_datatypes_explicit():
    assert code_repr(C(a=1, c=2)) == snapshot("C(a=1, c=2)")
    assert code_repr(B(b=5)) == snapshot("B(b=5)")
    assert code_repr(B(b=0)) == snapshot("B()")

    assert code_repr(Dataclass(a=0, b=0, c=[])) == snapshot("Dataclass(a=0)")
    assert code_repr(Dataclass(a=1, b=2, c=[3])) == snapshot(
        "Dataclass(a=1, b=2, c=[3])"
    )
    assert code_repr(Counter([1, 1, 1, 2])) == snapshot("Counter({1: 3, 2: 1})")

    assert code_repr(default_dict) == snapshot("defaultdict(list, {5: [2], 3: [1]})")


def test_tuple():

    class FakeTuple(tuple):
        def __init__(self):
            self._fields = 5

        def __repr__(self):
            return "FakeTuple()"

    assert code_repr(FakeTuple()) == snapshot("FakeTuple()")


def test_invalid_repr(check_update):
    assert (
        check_update(
            """\
class Thing:
    def __repr__(self):
        return "+++"

    def __eq__(self,other):
        if not isinstance(other,Thing):
            return NotImplemented
        return True

assert Thing() == snapshot()
""",
            flags="create",
        )
        == snapshot(
            """\
class Thing:
    def __repr__(self):
        return "+++"

    def __eq__(self,other):
        if not isinstance(other,Thing):
            return NotImplemented
        return True

assert Thing() == snapshot(HasRepr(Thing, "+++"))
"""
        )
    )
