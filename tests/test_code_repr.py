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
