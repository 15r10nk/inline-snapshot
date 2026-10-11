"""Readable workload templates and deterministic data for large literals.

Expected values are rendered inline, so their construction and snapshot source
processing remain part of the measured assertion.
"""

from pprint import pformat
from string import Template

from dirty_equals import IsInt
from dirty_equals import IsStr

SCALAR = """\
from inline_snapshot import snapshot

ACTUAL = 42

def test_snapshot():
    assert ACTUAL == snapshot(42)

def plain():
    assert ACTUAL == 42
"""

MATCHING = Template("""\
$preamble
from inline_snapshot import snapshot

ACTUAL = $actual
# Avoid interned strings turning equality into an identity check.
if isinstance(ACTUAL, str):
    ACTUAL = ACTUAL.encode().decode()

def test_snapshot():
    assert ACTUAL == snapshot($expected)

def plain():
    assert ACTUAL == $expected
""")

DATACLASSES = """\
from dataclasses import dataclass

@dataclass
class Part:
    content: str

@dataclass
class Event:
    index: int
    part: Part
"""

MODELS = """\
from pydantic import BaseModel

class Part(BaseModel):
    content: str

class Event(BaseModel):
    index: int
    part: Part
"""

CREATE = Template("""\
from inline_snapshot import snapshot

ACTUAL = $schema

def test_snapshot():
    assert ACTUAL == snapshot()
""")

FIX = Template("""\
from inline_snapshot import snapshot

ACTUAL = $schema

def test_snapshot():
    assert ACTUAL == snapshot(None)
""")

UPDATE = """\
from inline_snapshot import snapshot

ACTUAL = [1, 2, 3]

def test_snapshot():
    assert ACTUAL == snapshot([1.0, 2.0, 3.0])
"""


def schema(path_count):
    value = {
        "openapi": "3.1.0",
        "info": {"title": "Benchmark API", "version": "1.0"},
        "paths": {
            f"/items/{i}": {
                "get": {
                    "operationId": f"read_item_{i}",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string"},
                                            "tags": {
                                                "type": "array",
                                                "items": {"type": "string"},
                                            },
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            }
            for i in range(path_count)
        },
    }
    return value


def spans(*, matchers=False):
    value = [
        {
            "name": IsStr() if matchers else f"request-{i}",
            "context": {"trace_id": i, "span_id": i + 1},
            "parent": None,
            "start_time": IsInt() if matchers else 1000 + i,
            "attributes": {
                "method": "GET",
                "status": 200,
                "tags": ["http", "server"],
            },
        }
        for i in range(20)
    ]
    return value


def errors():
    value = [
        {
            "type": "greater_than",
            "loc": ("items", i, "value"),
            "msg": "Input should be greater than 10",
            "input": i,
            "ctx": {"gt": 10},
        }
        for i in range(5)
    ]
    return value


def literal(value):
    return pformat(value, sort_dicts=False)


def comparison_template(case):
    if case == "scalar":
        return SCALAR

    preamble = ""
    if case == "text":
        actual = expected = literal(
            "\n".join(f"event {i}: completed request successfully" for i in range(100))
        )
    elif case in {"schema", "schema_large"}:
        actual = expected = literal(schema(3 if case == "schema" else 200))
    elif case in {"spans", "matchers"}:
        actual = literal(spans())
        expected = literal(spans(matchers=case == "matchers"))
        preamble = "from dirty_equals import IsInt\nfrom dirty_equals import IsStr\n"
    elif case in {"events", "models"}:
        preamble = DATACLASSES if case == "events" else MODELS
        actual = expected = (
            "[\n"
            + ",\n".join(
                f"Event(index={i}, part=Part(content='chunk {i}'))" for i in range(50)
            )
            + "\n]"
        )
    elif case == "errors":
        actual = expected = literal(errors())
    else:
        raise ValueError(case)
    return MATCHING.substitute(preamble=preamble, actual=actual, expected=expected)


def session_template(mode):
    if mode in {"active", "disabled"}:
        return comparison_template("schema")
    if mode == "create":
        return CREATE.substitute(schema=literal(schema(3)))
    if mode == "fix":
        return FIX.substitute(schema=literal(schema(3)))
    if mode == "update":
        return UPDATE
    raise ValueError(mode)
