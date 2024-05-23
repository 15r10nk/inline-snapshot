from .example import Example
from inline_snapshot import snapshot


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


def test_hasrepr():

    Example(
        """\
from inline_snapshot import snapshot

class Thing:
    def __repr__(self):
        return "<something>"

def test_thing():
    assert Thing() == snapshot()

    """
    ).run_pytest(
        "--inline-snapshot=create",
        returncode=snapshot(0),
        changed_files=snapshot(
            {
                "test_something.py": """\
from inline_snapshot import snapshot

from inline_snapshot import HasRepr

class Thing:
    def __repr__(self):
        return "<something>"

def test_thing():
    assert Thing() == snapshot(HasRepr(Thing, "<something>"))

    \
"""
            }
        ),
    ).run_pytest(
        "--inline-snapshot=disable", returncode=0
    ).run_pytest(
        returncode=0
    )


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

assert container(bg=color.red,fg=color.red) == snapshot(container(bg=color.red, fg=color.red))

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

assert Namespace.Color.red == snapshot()

    """
    ).run_inline(
        "create",
        files=snapshot(
            {
                "test_something.py": """\
from enum import Enum
from inline_snapshot import snapshot


class Namespace:
    class Color(Enum):
        red="red"

assert Namespace.Color.red == snapshot(Namespace.Color.red)

    \
"""
            }
        ),
    ).run_inline()
