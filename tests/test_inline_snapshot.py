import contextlib
import itertools
import re
import textwrap
import warnings
from collections import namedtuple
from dataclasses import dataclass
from typing import Union

import pytest
from dirty_equals import AnyThing

from inline_snapshot import snapshot
from inline_snapshot._flags import Flags
from inline_snapshot._format import format_code
from inline_snapshot._global_state import snapshot_env
from inline_snapshot._is import Is
from inline_snapshot.extra import Transformed
from inline_snapshot.testing import Example
from tests.conftest import check_update


@pytest.mark.no_rewriting
def test_snapshot_eq():
    with snapshot_env():
        assert 1 == snapshot(1)
        assert snapshot(1) == 1


@pytest.mark.no_rewriting
def test_disabled():
    with snapshot_env() as state:
        state.active = False
        with pytest.raises(AssertionError) as excinfo:
            assert 2 == snapshot()

    assert str(excinfo.value) == snapshot(
        "your snapshot is missing a value run pytest with --inline-snapshot=create"
    )


operation = namedtuple("operation", "value,op,svalue,fvalue,flag")
operations = [
    # compare
    operation("4", "==", "", "4", "create"),
    operation("4", "==", "5", "4", "fix"),
    operation("4", "==", "2+2", "4", "update"),
    # leq
    operation("4", "<=", "", "4", "create"),
    operation("4", "<=", "5", "4", "trim"),
    operation("5", "<=", "4", "5", "fix"),
    operation("5", "<=", "3+2", "5", "update"),
    # geq
    operation("5", ">=", "", "5", "create"),
    operation("5", ">=", "4", "5", "trim"),
    operation("4", ">=", "5", "4", "fix"),
    operation("5", ">=", "3+2", "5", "update"),
    # contains
    operation("5", "in", "", "[5]", "create"),
    operation("5", "in", "[4, 5]", "[5]", "trim"),
    operation("5", "in", "[]", "[5]", "fix"),
    operation("5", "in", "[3+2]", "[5]", "update"),
]


def _generate_test_codes():
    codes = []
    for op in operations:
        codes.append((f"assert {op.value} {op.op} snapshot({op.svalue})", op.flag))
        if op.svalue:
            codes.append(
                (
                    f"assert {op.value} {op.op} snapshot({{0: {op.svalue}}})[0]",
                    op.flag,
                )
            )
        else:
            codes.append((f"assert {op.value} {op.op} snapshot({{}})[0]", op.flag))
    return codes


@pytest.mark.parametrize(
    "code,reported_flag",
    _generate_test_codes(),
    ids=lambda x: x if isinstance(x, str) else "",
)
def test_generic(code, reported_flag, executing_used):
    all_flags = ["trim", "fix", "create", "update"]

    # s = source(code)
    e = Example(
        f"""\
from inline_snapshot import snapshot
def test_a():
    {code}
"""
    )

    e.run_inline(
        reported_categories=(
            [] if not executing_used and reported_flag == "update" else [reported_flag]
        ),
        raises=AnyThing(),
        changed_files=AnyThing(),
    )

    for flag in all_flags:
        if flag == reported_flag:
            continue
        print("use flag:", flag)
        # no changes
        e.run_inline([f"--inline-snapshot={flag}"], raises=AnyThing())

    if not executing_used:
        return

    e.run_inline(
        [f"--inline-snapshot={reported_flag}"],
        changed_files=AnyThing(),
    ).run_inline()


@pytest.mark.parametrize(
    "ops",
    [
        pytest.param(ops, id=" ".join(f"{op.flag}({op.op})" for op in ops))
        for ops in itertools.combinations(operations, 2)
    ],
)
def test_generic_multi(ops, executing_used):

    def gen_code(ops, fixed, old_keys):
        keys = old_keys + [k for k in range(len(ops)) if k not in old_keys]
        new_keys = []

        args = []
        print(keys)
        for k in keys:
            op = ops[k]
            value = op.fvalue if op.flag in fixed else op.svalue
            if value:
                args.append(f'"k_{k}": {value}')
                new_keys.append(k)
        args = ", ".join(args)

        code = "s = snapshot({" + args + "})\n"

        for k, op in enumerate(ops):
            code += f'print({op.value} {op.op} s["k_{k}"]) # {op.flag} {op.svalue or "<undef>"} -> {op.fvalue}\n'

        code = f"""\
from inline_snapshot import snapshot
def test_a():
{textwrap.indent(code,"    ")}
"""
        return code, new_keys

    all_flags = {op.flag for op in ops}
    keys = []
    code, keys = gen_code(ops, {}, keys)

    e = Example(code)
    e.run_inline(
        reported_categories=sorted(
            all_flags - ({"update"} if not executing_used else set())
        ),
        raises=AnyThing(),
    )

    if executing_used:
        for flags in itertools.permutations(all_flags):
            e2 = e
            fixed_flags = set()
            for flag in flags:
                fixed_flags.add(flag)
                code, keys = gen_code(ops, fixed_flags, keys)
                e2 = e2.run_inline(
                    [f"--inline-snapshot={flag}"],
                    changed_files=snapshot({"tests/test_something.py": Is(code)}),
                )

                e2 = e2.run_inline(reported_categories=sorted(all_flags - fixed_flags))

    for flag in {"update", "fix", "trim", "create"} - all_flags:
        e.run_inline([f"--inline-snapshot={flag}"])


def test_mutable_values():
    check_update(
        """\
l=[1,2]
assert l==snapshot()
l.append(3)
assert l==snapshot()\
""",
        flags="create",
        expected_code="""\
l=[1,2]
assert l==snapshot([1, 2])
l.append(3)
assert l==snapshot([1, 2, 3])\
""",
    )

    check_update(
        """\
l=[1,2]
assert l<=snapshot()
l.append(3)
assert l<=snapshot()\
""",
        flags="create",
        expected_code="""\
l=[1,2]
assert l<=snapshot([1, 2])
l.append(3)
assert l<=snapshot([1, 2, 3])\
""",
    )

    check_update(
        """\
l=[1,2]
assert l>=snapshot()
l.append(3)
assert l>=snapshot()\
""",
        flags="create",
        expected_code="""\
l=[1,2]
assert l>=snapshot([1, 2])
l.append(3)
assert l>=snapshot([1, 2, 3])\
""",
    )

    check_update(
        """\
l=[1,2]
assert l in snapshot()
l.append(3)
assert l in snapshot()\
""",
        flags="create",
        expected_code="""\
l=[1,2]
assert l in snapshot([[1, 2]])
l.append(3)
assert l in snapshot([[1, 2, 3]])\
""",
    )


def test_comparison():
    check_update(
        "assert 5==snapshot()", flags="create", expected_code="assert 5==snapshot(5)"
    )

    check_update(
        "assert 5==snapshot(9)", flags="fix", expected_code="assert 5==snapshot(5)"
    )

    check_update(
        'assert "a"==snapshot("""a""")',
        flags="update",
        expected_code='assert "a"==snapshot("a")',
    )

    check_update(
        'assert "a"==snapshot("""a""")',
        reported_flags={"update"},
        flags="fix",
        expected_code='assert "a"==snapshot("""a""")',
    )

    check_update(
        """\
for a in [1,1,1]:
    assert a==snapshot()\
""",
        flags="create",
        expected_code="""\
for a in [1,1,1]:
    assert a==snapshot(1)\
""",
    )

    check_update(
        """\
for a in [1,1,1]:
    assert a==snapshot(2)\
""",
        flags="fix",
        expected_code="""\
for a in [1,1,1]:
    assert a==snapshot(1)\
""",
    )


def test_ge():
    check_update(
        "assert 5<=snapshot()", flags="create", expected_code="assert 5<=snapshot(5)"
    )

    check_update(
        "assert 5<=snapshot()",
        reported_flags={"create"},
        expected_code="assert 5<=snapshot()",
    )

    check_update(
        """\
s=snapshot({"v": 7, "q": 4})
assert 5<=s["v"]
assert 5==s["q"]\
""",
        flags="fix",
        reported_flags={"fix", "trim"},
        expected_code="""\
s=snapshot({"v": 7, "q": 5})
assert 5<=s["v"]
assert 5==s["q"]\
""",
    )

    check_update(
        """\
s=snapshot({"q": 4})
assert 5<=s["v"]
assert 5==s["q"]\
""",
        flags="fix",
        reported_flags={"create", "fix"},
        expected_code="""\
s=snapshot({"q": 5})
assert 5<=s["v"]
assert 5==s["q"]\
""",
    )

    check_update(
        "assert 5<=snapshot(9)", flags="trim", expected_code="assert 5<=snapshot(5)"
    )

    check_update(
        "assert 5<=snapshot(3)", flags="fix", expected_code="assert 5<=snapshot(5)"
    )

    check_update(
        "assert snapshot(3) >= 5", flags="fix", expected_code="assert snapshot(5) >= 5"
    )

    check_update("assert 5<=snapshot(5)", expected_code="assert 5<=snapshot(5)")

    check_update(
        "for i in range(5): assert i <=snapshot(2)",
        flags="fix",
        expected_code="for i in range(5): assert i <=snapshot(4)",
    )

    check_update(
        "for i in range(5): assert i <=snapshot(10)",
        flags="trim",
        expected_code="for i in range(5): assert i <=snapshot(4)",
    )


def test_le():
    check_update(
        "assert 5>=snapshot()", flags="create", expected_code="assert 5>=snapshot(5)"
    )

    check_update(
        """\
s=snapshot({"v": 3, "q": 4})
assert 5>=s["v"]
assert 5==s["q"]\
""",
        flags="fix",
        reported_flags={"fix", "trim"},
        expected_code="""\
s=snapshot({"v": 3, "q": 5})
assert 5>=s["v"]
assert 5==s["q"]\
""",
    )

    check_update(
        """\
s=snapshot({"q": 4})
assert 5>=s["v"]
assert 5==s["q"]\
""",
        flags="fix",
        reported_flags={"create", "fix"},
        expected_code="""\
s=snapshot({"q": 5})
assert 5>=s["v"]
assert 5==s["q"]\
""",
    )

    check_update(
        "assert 5>=snapshot(2)", flags="trim", expected_code="assert 5>=snapshot(5)"
    )

    check_update(
        "assert 5>=snapshot(8)", flags="fix", expected_code="assert 5>=snapshot(5)"
    )

    check_update(
        "assert snapshot(8) <= 5", flags="fix", expected_code="assert snapshot(5) <= 5"
    )

    check_update("assert 5>=snapshot(5)", expected_code="assert 5>=snapshot(5)")

    check_update(
        "for i in range(5): assert i >=snapshot(2)",
        flags="fix",
        expected_code="for i in range(5): assert i >=snapshot(0)",
    )

    check_update(
        "for i in range(5): assert i >=snapshot(-10)",
        flags="trim",
        expected_code="for i in range(5): assert i >=snapshot(0)",
    )


def test_contains():
    check_update(
        "assert 5 in snapshot()",
        flags="create",
        expected_code="assert 5 in snapshot([5])",
    )

    check_update(
        "assert 5 in snapshot([])",
        flags="fix",
        expected_code="assert 5 in snapshot([5])",
    )

    check_update(
        "assert 5 in snapshot([2])",
        flags="fix,trim",
        expected_code="assert 5 in snapshot([5])",
    )

    check_update(
        "assert 5 in snapshot([2,5])",
        flags="trim",
        expected_code="assert 5 in snapshot([5])",
    )

    check_update(
        "for i in range(5): assert i in snapshot([0,1,2,3,4,5,6])",
        flags="trim",
        expected_code="for i in range(5): assert i in snapshot([0,1,2,3,4])",
    )

    check_update(
        """\
s=snapshot()
assert 4 in s
assert 5 in s
assert 5 in s\
""",
        flags="create",
        expected_code="""\
s=snapshot([4, 5])
assert 4 in s
assert 5 in s
assert 5 in s\
""",
    )


def test_getitem():
    check_update(
        'assert 5 == snapshot()["test"]',
        flags="create",
        expected_code='assert 5 == snapshot({"test": 5})["test"]',
    )

    check_update(
        "for i in range(3): assert i in snapshot()[str(i)]",
        flags="create",
        expected_code='for i in range(3): assert i in snapshot({"0": [0], "1": [1], "2": [2]})[str(i)]',
    )

    check_update(
        'for i in range(3): assert i in snapshot({"0": [0], "1": [1], "2": [2]})[str(i)]',
        expected_code='for i in range(3): assert i in snapshot({"0": [0], "1": [1], "2": [2]})[str(i)]',
    )

    check_update(
        'for i in range(2): assert i in snapshot({"0": [0], "1": [1], "2": [2]})[str(i)]',
        flags="trim",
        expected_code='for i in range(2): assert i in snapshot({"0": [0], "1": [1]})[str(i)]',
    )

    check_update(
        'for i in range(3): assert i in snapshot({"0": [0], "1": [1,2], "2": [4]})[str(i)]',
        flags="fix,trim",
        expected_code='for i in range(3): assert i in snapshot({"0": [0], "1": [1], "2": [2]})[str(i)]',
    )

    check_update(
        'for i in range(3): assert i in snapshot({"0": [0], "1": [1,2], "2": [4]})[str(i)]',
        flags="fix",
        reported_flags={"fix", "trim"},
        expected_code='for i in range(3): assert i in snapshot({"0": [0], "1": [1,2], "2": [4, 2]})[str(i)]',
    )

    check_update(
        'for i in range(3): assert i in snapshot({"0": [0], "1": [1,2], "2": [2]})[str(i)]',
        flags="trim",
        expected_code='for i in range(3): assert i in snapshot({"0": [0], "1": [1], "2": [2]})[str(i)]',
    )

    check_update(
        "assert 4 in snapshot({2:[4],3:[]})[2]",
        flags="trim",
        expected_code="assert 4 in snapshot({2:[4]})[2]",
    )

    check_update(
        "assert 5 in snapshot({2:[4],3:[]})[2]",
        flags="fix",
        reported_flags={"fix", "trim"},
        expected_code="assert 5 in snapshot({2:[4, 5],3:[]})[2]",
    )

    check_update(
        "assert 5 in snapshot({2:[4],3:[]})[2]",
        flags="fix,trim",
        expected_code="assert 5 in snapshot({2:[5]})[2]",
    )

    check_update(
        "assert 5 in snapshot({3:[1]})[2]",
        flags="create",
        reported_flags={"create", "trim"},
        expected_code="assert 5 in snapshot({3:[1], 2: [5]})[2]",
    )

    check_update(
        """\
s=snapshot()
assert 5 == s["q"]
assert 5 == s["q"]\
""",
        flags="create",
        expected_code="""\
s=snapshot({"q": 5})
assert 5 == s["q"]
assert 5 == s["q"]\
""",
    )


def test_assert():
    check_update(
        "assert 2 == snapshot(5)",
        reported_flags={"fix"},
        expected_code="assert 2 == snapshot(5)",
        raises="AssertionError",
    )


def test_plain(executing_used):
    check_update("s = snapshot(5)", flags="", expected_code="s = snapshot(5)")

    check_update("s = snapshot()", flags="", expected_code="s = snapshot()")


def test_flags_repr():
    assert repr(Flags({"update"})) == "Flags({'update'})"


def test_format_file():
    check_update(
        'assert ["aaaaaaaaaaaaaaaaa"] * 5 == snapshot()',
        flags="create",
        expected_code="""\
assert ["aaaaaaaaaaaaaaaaa"] * 5 == snapshot([
    "aaaaaaaaaaaaaaaaa",
    "aaaaaaaaaaaaaaaaa",
    "aaaaaaaaaaaaaaaaa",
    "aaaaaaaaaaaaaaaaa",
    "aaaaaaaaaaaaaaaaa",
])\
""",
    )


def test_format_value():
    check_update(
        'assert ["aaaaaaaaaaaaaaaaa"] * 5==  snapshot()',
        flags="create",
        expected_code="""\
assert ["aaaaaaaaaaaaaaaaa"] * 5==  snapshot([
    "aaaaaaaaaaaaaaaaa",
    "aaaaaaaaaaaaaaaaa",
    "aaaaaaaaaaaaaaaaa",
    "aaaaaaaaaaaaaaaaa",
    "aaaaaaaaaaaaaaaaa",
])\
""",
    )


def test_unused_snapshot():
    check_update(
        "snapshot()",
        flags="create",
        reported_flags=set(),
        expected_code="snapshot()",
    )


def test_type_error():
    tests = ["5 == s", "5 <= s", "5 >= s", "5 in s", "5 == s[0]"]

    for test1, test2 in itertools.product(tests, tests):
        check_update(
            f"""\
s = snapshot()
assert {test1}
assert {test2}\
""",
            reported_flags={"create"},
            expected_code=AnyThing(),
            raises=(
                snapshot("<no exception>")
                if test1 == test2
                else Transformed(
                    lambda s: re.sub(r"`[^`]+`", "`...`", s),
                    value="TypeError: This snapshot cannot be use with `...`, because it was previously used with `...`",
                )
            ),
        )


def test_sub_snapshot_create():

    check_update(
        """\
s=snapshot({})

s["keya"]

assert s["keyb"]==5\
""",
        flags="create",
        expected_code="""\
s=snapshot({"keyb": 5})

s["keya"]

assert s["keyb"]==5\
""",
    )

    check_update(
        """\
s=snapshot()

s["keya"]

assert s["keyb"]==5\
""",
        flags="create",
        expected_code="""\
s=snapshot({"keyb": 5})

s["keya"]

assert s["keyb"]==5\
""",
    )


def test_sub_snapshot_tuple_key():
    # see https://github.com/15r10nk/inline-snapshot/issues/358

    Example(
        """\
from inline_snapshot import snapshot

def test_a():
    for i in (1,2):
        assert 5 == snapshot()[(i,)]
"""
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot import snapshot

def test_a():
    for i in (1,2):
        assert 5 == snapshot({(1,): 5, (2,): 5})[(i,)]
"""
            }
        ),
    )


def test_sub_snapshot_empty_string():

    Example(
        """\
from inline_snapshot import snapshot

def test_a():
    assert ""==snapshot()[5]
    assert "a"==snapshot()[5]

def test_b():
    assert 42==snapshot()[""]
    assert 42==snapshot()["a"]
"""
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot import snapshot

def test_a():
    assert ""==snapshot({5: ""})[5]
    assert "a"==snapshot({5: "a"})[5]

def test_b():
    assert 42==snapshot({"": 42})[""]
    assert 42==snapshot({"a": 42})["a"]
"""
            }
        ),
    )


def test_different_snapshot_name():

    check_update(
        """\
from inline_snapshot import snapshot as s
assert 4==s()\
""",
        flags="create",
        expected_code="""\
from inline_snapshot import snapshot as s
assert 4==s(4)\
""",
    )

    check_update(
        """\
import inline_snapshot
assert 4==inline_snapshot.snapshot()\
""",
        flags="create",
        expected_code="""\
import inline_snapshot
assert 4==inline_snapshot.snapshot(4)\
""",
    )


def test_quoting_change_is_no_update():

    s = (
        Example(
            """\
from inline_snapshot import external,snapshot

class X:
    def __init__(self,a,b):
        assert a==b
        self.a=a

    def __repr__(self):
        return f'''X("{self.a}",\\'{self.a}\\')'''

    def __eq__(self,other):
        if not hasattr(other,"a"):
            return NotImplemented
        return other.a==self.a

def test_a():
    assert X("a","a") == snapshot()
"""
        )
        .run_inline(
            ["--inline-snapshot=create"],
            changed_files=snapshot(
                {
                    "tests/test_something.py": """\
from inline_snapshot import external,snapshot

class X:
    def __init__(self,a,b):
        assert a==b
        self.a=a

    def __repr__(self):
        return f'''X("{self.a}",\\'{self.a}\\')'''

    def __eq__(self,other):
        if not hasattr(other,"a"):
            return NotImplemented
        return other.a==self.a

def test_a():
    assert X("a","a") == snapshot(X("a", "a"))
"""
                }
            ),
            reported_categories=snapshot(["create"]),
        )
        .replace('"', "'")
    )

    s = s.run_inline(
        ["--inline-snapshot=update"],
        changed_files=snapshot({}),
        reported_categories=snapshot([]),
    )


def test_trailing_comma():
    Example(
        format_code(
            """\
from inline_snapshot import external, snapshot

class X:
    def __init__(self, *args):
        self.args = args

    def __repr__(self):
        return f"X({', '.join(map(repr,self.args))})"

    def __eq__(self,other):
        if not isinstance(other,X):
            return NotImplemented

        return self.args == other.args

def test_thing():
    assert X("a" * 40, "a" * 40) == snapshot()
""",
            "",
        )
    ).run_pytest(
        ["--inline-snapshot=create"],
        report=snapshot(
            """\
------------------------------- Create snapshots -------------------------------
+-------------------------- tests/test_something.py ---------------------------+
| @@ -16,4 +16,9 @@                                                            |
|                                                                              |
|                                                                              |
|                                                                              |
|  def test_thing():                                                           |
| -    assert X("a" * 40, "a" * 40) == snapshot()                              |
| +    assert X("a" * 40, "a" * 40) == snapshot(                               |
| +        X(                                                                  |
| +            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",                     |
| +            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",                     |
| +        )                                                                   |
| +    )                                                                       |
+------------------------------------------------------------------------------+
These changes will be applied, because you used create\
"""
        ),
        returncode=1,
        changed_files={
            "tests/test_something.py": """\
from inline_snapshot import external, snapshot


class X:
    def __init__(self, *args):
        self.args = args

    def __repr__(self):
        return f"X({', '.join(map(repr,self.args))})"

    def __eq__(self, other):
        if not isinstance(other, X):
            return NotImplemented

        return self.args == other.args


def test_thing():
    assert X("a" * 40, "a" * 40) == snapshot(
        X(
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        )
    )
"""
        },
    ).run_pytest(
        ["--inline-snapshot=report"], report=snapshot("")
    )


@dataclass
class Warning:
    message: str
    filename: Union[str, None] = None
    line: Union[int, None] = None


@contextlib.contextmanager
def warns(expected_warnings=[], include_line=False, include_file=False):
    with warnings.catch_warnings(record=True) as result:
        warnings.simplefilter("always")
        yield

    assert [
        Warning(
            message=f"{w.category.__name__}: {w.message}",
            line=w.lineno if include_line else None,
            filename=w.filename if include_file else None,
        )
        for w in result
    ] == expected_warnings


def test_starred_warns_list():

    with warns(
        snapshot(
            [
                Warning(
                    message="InlineSnapshotSyntaxWarning: star-expressions are not supported inside snapshots",
                    line=5,
                )
            ]
        ),
        include_line=True,
    ):
        Example(
            """
from inline_snapshot import snapshot

def test():
    assert [5] == snapshot([*[5]])
"""
        ).run_inline(["--inline-snapshot=fix"])


def test_starred_warns_dict():
    with warns(
        snapshot(
            [
                Warning(
                    message="InlineSnapshotSyntaxWarning: star-expressions are not supported inside snapshots",
                    line=5,
                )
            ]
        ),
        include_line=True,
    ):
        Example(
            """
from inline_snapshot import snapshot

def test():
    assert {1:3} == snapshot({**{1:3}})
"""
        ).run_inline(["--inline-snapshot=fix"])


def test_is():

    Example(
        """
from inline_snapshot import snapshot,Is

def test_Is():
    for i in range(3):
        assert ["hello",i] == snapshot(["hi",Is(i)])
        assert ["hello",i] == snapshot({1:["hi",Is(i)]})[i]
"""
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "tests/test_something.py": """\

from inline_snapshot import snapshot,Is

def test_Is():
    for i in range(3):
        assert ["hello",i] == snapshot(["hi",Is(i)])
        assert ["hello",i] == snapshot({1:["hi",Is(i)], 0: ["hello", 0], 2: ["hello", 2]})[i]
"""
            }
        ),
    ).run_inline(
        ["--inline-snapshot=fix"],
        changed_files=snapshot(
            {
                "tests/test_something.py": """\

from inline_snapshot import snapshot,Is

def test_Is():
    for i in range(3):
        assert ["hello",i] == snapshot(["hello",Is(i)])
        assert ["hello",i] == snapshot({1:["hello",Is(i)], 0: ["hello", 0], 2: ["hello", 2]})[i]
"""
            }
        ),
    )


def test_create_ellipsis():
    Example(
        """\
from inline_snapshot import snapshot

def test_a():
    assert 1+1==snapshot(...)
    assert [1,2,8] == snapshot([1,2,...])
        """
    ).run_inline(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "tests/test_something.py": """\
from inline_snapshot import snapshot

def test_a():
    assert 1+1==snapshot(2)
    assert [1,2,8] == snapshot([1,2,8])
        \
"""
            }
        ),
    )
