import ast
import random
import sys

from pysource_minimize import minimize

from inline_snapshot import UsageError
from inline_snapshot.testing import Example

header = """
from dataclasses import dataclass

@dataclass
class A:
    a:int
    b:int=5
    c:int=5

def f(v):
    return v

"""


def chose(l):
    return random.choice(l)


def gen_new_value(values):

    kind = chose(["dataclass", "dict", "tuple", "list", "f"])

    if kind == "dataclass":
        data_type = chose(["A"])
        num_args = chose(range(1, 3))
        num_pos_args = chose(range(num_args))
        assert num_pos_args <= num_args

        args_names = ["a", "b", "c"]
        random.shuffle(args_names)

        args = [
            *[chose(values) for _ in range(num_pos_args)],
            *[
                f"{args_names.pop()}={chose(values)}"
                for _ in range(num_args - num_pos_args)
            ],
        ]

        return f"{data_type}({', '.join(args)})"

    if kind == "tuple":
        return "(" + ", ".join(chose(values) for _ in range(3)) + ")"

    if kind == "list":
        return "[" + ", ".join(chose(values) for _ in range(3)) + "]"

    if kind == "dict":
        return (
            "[" + ", ".join(f"{chose(values)}:{chose(values)}" for _ in range(3)) + "]"
        )

    if kind == "f":
        return f"f({chose(values)})"


context = dict()
exec(header, context, context)


def is_valid_value(v):
    try:
        eval(v, context, {})
    except:
        return False
    return True


def value_of(v):
    return eval(v, context, {})


def gen_values():
    values = [
        "1",
        "'abc'",
        "True",
        "list()",
        "dict()",
        "set()",
        "tuple()",
        "[]",
        "{}",
        "()",
        "{*()}",
    ]

    while len(values) <= 500:
        new_value = gen_new_value([v for v in values if len(v) < 50])

        if is_valid_value(new_value):
            values.append(new_value)

    return values


def fmt(code):
    return ast.unparse(ast.parse(code))


class Store:
    def __eq__(self, other):
        self.value = other
        return True


def gen_test(values):

    va = chose(values)
    vb = chose(values)

    test = f"""
from inline_snapshot import snapshot
{header}

def test_a():
    assert {va} == snapshot({vb})
    assert {vb} == snapshot({va})

def test_b():
    for _ in [1,2,3]:
        assert {va} == snapshot({vb})
        assert {vb} == snapshot({va})

def test_c():
    snapshot({vb})
    snapshot({va})
"""
    test = fmt(test)

    if value_of(va) == value_of(vb):
        return

    def contains_bug(code):

        try:
            Example({"test.py": code}).run_inline(["--inline-snapshot=fix"])
        except UsageError:
            return False
        except KeyboardInterrupt:
            raise
        except AssertionError:
            return True
        except:
            return True

        return False

    if not contains_bug(test):
        return

    test = minimize(test, checker=contains_bug)
    print("minimal code:")
    print("=" * 20)
    print(test)
    sys.exit()


if __name__ == "__main__":
    values = gen_values()

    for i in range(100000):
        gen_test(values)
