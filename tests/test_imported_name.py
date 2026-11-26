import pytest

from inline_snapshot import Is
from inline_snapshot.testing import Example


@pytest.fixture
def imported_name_files():
    return {
        "import_target/__init__.py": "from .sub import Value\n",
        "import_target/sub.py": """\
class Value:
    def __init__(self, data):
        self.data = data

    def __eq__(self, other):
        if not isinstance(other, Value):
            return NotImplemented
        return self.data == other.data
""",
        "producer.py": """\
from import_target.sub import Value

def get_value():
    return Value(1)
""",
    }


@pytest.mark.parametrize(
    "original, flag", [("", "create"), ("None", "fix"), ("get_value()", "update")]
)
@pytest.mark.parametrize(
    "existing, options, added, expression",
    [
        ("", {}, "from import_target.sub import Value\n", "Value"),
        ("from import_target.sub import Value as V\n", {}, "", "V"),
        ("from import_target import Value as V\n", {}, "", "V"),
        ("import import_target.sub\n", {}, "", "import_target.sub.Value"),
        ("import import_target.sub as ps\n", {}, "", "ps.Value"),
        ("import import_target as p\n", {}, "", "p.Value"),
        ("from import_target import sub as ps\n", {}, "", "ps.Value"),
        (
            "import import_target as p\nfrom import_target.sub import Value as V\n",
            {},
            "",
            "V",
        ),
        (
            "from import_target.sub import Value as V\n",
            {"style": "import"},
            "import import_target.sub\n",
            "import_target.sub.Value",
        ),
        (
            "import import_target.sub as ps\n",
            {"style": "import-from"},
            "from import_target.sub import Value\n",
            "Value",
        ),
        (
            "import import_target.sub as ps\n",
            {"import_as": "V"},
            "from import_target.sub import Value as V\n",
            "V",
        ),
        (
            "from import_target.sub import Value as V\n",
            {"style": "import", "import_as": "ps"},
            "import import_target.sub as ps\n",
            "ps.Value",
        ),
        (
            "from import_target.sub import Value as V\n",
            {"style": "import-from", "import_as": "V"},
            "",
            "V",
        ),
        (
            "import import_target.sub as ps\n",
            {"style": "import", "import_as": "ps"},
            "",
            "ps.Value",
        ),
        (
            "from import_target.sub import Value as V\n",
            {"style": "import-from"},
            "from import_target.sub import Value\n",
            "Value",
        ),
        (
            "import import_target.sub as ps\n",
            {"style": "import"},
            "import import_target.sub\n",
            "import_target.sub.Value",
        ),
    ],
)
def test_imported_name(
    existing, options, added, expression, original, flag, imported_name_files
):
    files = dict(imported_name_files)
    files["conftest.py"] = f"""\
from import_target.sub import Value
from inline_snapshot.plugin import customize

@customize
def handler(value, builder):
    if isinstance(value, Value):
        return builder.create_call(
            builder.create_imported_name("import_target.sub", "Value", **{options!r}),
            [value.data],
        )
"""
    source = f"""\
from inline_snapshot import snapshot
from producer import get_value
{existing}
def test_value():
    for _ in range(2):
        assert get_value() == snapshot({original})
"""
    files["tests/test_something.py"] = source
    expected = source.replace(f"snapshot({original})", f"snapshot({expression}(1))")
    if added:
        last_import = (
            existing.rstrip().splitlines()[-1]
            if existing
            else "from producer import get_value"
        )
        expected = expected.replace(last_import + "\n", last_import + "\n\n" + added, 1)
    Example(files).run_inline(
        [f"--inline-snapshot={flag}"],
        changed_files={"tests/test_something.py": Is(expected)},
    ).run_inline(changed_files={}).run_inline(
        ["--inline-snapshot=disable"], reported_categories=set()
    )


@pytest.mark.parametrize(
    "existing, local, added, expression",
    [
        ("import math\n", "", "from import_target.sub import Value\n", "Value"),
        ("", "    from import_target.sub import Value as V\n", "", "V"),
        ("", "    import import_target.sub as ps\n", "", "ps.Value"),
        (
            "from import_target.sub import Value as V\n",
            "    V = 42\n",
            "from import_target.sub import Value\n",
            "Value",
        ),
        (
            "import import_target.sub as ps\n",
            "    ps = 42\n",
            "from import_target.sub import Value\n",
            "Value",
        ),
        (
            "from unittest.mock import patch\nimport import_target\n",
            "    with patch.object(import_target, 'Value', None):\n    ",
            "",
            "import_target.sub.Value",
        ),
        (
            "from unittest.mock import patch\nimport import_target\n",
            "    with patch.object(import_target, 'Value', None), patch.object(import_target, 'sub', None):\n    ",
            "from import_target.sub import Value\n",
            "Value",
        ),
        (
            "",
            "    def unused():\n        from import_target.sub import Value as V\n",
            "from import_target.sub import Value\n",
            "Value",
        ),
        (
            "",
            "    Alias = get_value().__class__\n",
            "from import_target.sub import Value\n",
            "Value",
        ),
        (
            "import import_target.sub\n",
            "    import_target = 42\n",
            "from import_target.sub import Value\n",
            "Value",
        ),
    ],
)
def test_imported_name_scope(existing, local, added, expression, imported_name_files):
    files = dict(imported_name_files)
    files["conftest.py"] = """\
from import_target.sub import Value
from inline_snapshot.plugin import customize

@customize
def handler(value, builder):
    if isinstance(value, Value):
        return builder.create_call(builder.create_imported_name("import_target.sub", "Value"), [value.data])
"""
    source = f"""\
from inline_snapshot import snapshot
from producer import get_value
{existing}
def test_value():
{local}    assert get_value() == snapshot()
"""
    files["tests/test_something.py"] = source
    expected = source.replace("snapshot()", f"snapshot({expression}(1))")
    if added:
        last_import = (
            existing.rstrip().splitlines()[-1]
            if existing
            else "from producer import get_value"
        )
        expected = expected.replace(last_import + "\n", last_import + "\n\n" + added, 1)
    Example(files).run_inline(
        ["--inline-snapshot=create"],
        changed_files={"tests/test_something.py": Is(expected)},
    ).run_inline(["--inline-snapshot=disable"], reported_categories=set())


@pytest.mark.parametrize(
    "options, message",
    [
        ({"style": "invalid"}, "style must be 'import' or 'import-from'"),
        ({"module": "import_target..sub"}, "module must be a valid Python name"),
        ({"name": "not.valid"}, "name must be a valid Python name"),
        ({"import_as": "class"}, "import_as must be a valid Python name"),
        ({"import_as": ""}, "import_as must be a valid Python name"),
    ],
)
def test_imported_name_invalid_options(options, message, imported_name_files):
    arguments = {"module": "import_target.sub", "name": "Value", **options}
    files = dict(imported_name_files)
    files["conftest.py"] = f"""\
from import_target.sub import Value
from inline_snapshot.plugin import customize

@customize
def handler(value, builder):
    if isinstance(value, Value):
        return builder.create_imported_name(**{arguments!r})
"""
    files["tests/test_something.py"] = """\
from inline_snapshot import snapshot
from producer import get_value

def test_value():
    assert get_value() == snapshot()
"""
    Example(files).run_inline(
        ["--inline-snapshot=create"],
        raises=Is(f"UsageError: {message}"),
        reported_categories=set(),
        changed_files={},
    )


@pytest.mark.parametrize(
    "binding, options",
    [("Value", {}), ("import_target", {"style": "import"}), ("V", {"import_as": "V"})],
)
def test_imported_name_binding_conflict(binding, options, imported_name_files):
    files = dict(imported_name_files)
    files["conftest.py"] = f"""\
from import_target.sub import Value
from inline_snapshot.plugin import customize

@customize
def handler(value, builder):
    if isinstance(value, Value):
        return builder.create_imported_name("import_target.sub", "Value", **{options!r})
"""
    files["tests/test_something.py"] = f"""\
from inline_snapshot import snapshot
from producer import get_value

def test_value():
    {binding} = 42
    assert get_value() == snapshot()
"""
    Example(files).run_inline(
        ["--inline-snapshot=create"],
        raises=Is(
            f"UsageError: cannot import 'import_target.sub': {binding!r} is already bound to a different value"
        ),
        reported_categories=set(),
        changed_files={},
    )


@pytest.mark.parametrize(
    "code, specification, added",
    [
        (
            "ps.Value(1)",
            'Import("import_target.sub", asname="ps")',
            "import import_target.sub as ps",
        ),
        (
            "V(1)",
            'ImportFrom("import_target.sub", "Value", asname="V")',
            "from import_target.sub import Value as V",
        ),
    ],
)
def test_create_code_aliased_imports(code, specification, added, imported_name_files):
    files = dict(imported_name_files)
    files["conftest.py"] = f"""\
from import_target.sub import Value
from inline_snapshot.plugin import customize, Import, ImportFrom

@customize
def handler(value, builder):
    if isinstance(value, Value):
        return builder.create_code({code!r}, imports=[{specification}])
"""
    source = """\
from inline_snapshot import snapshot
from producer import get_value

def test_value():
    assert get_value() == snapshot()
"""
    files["tests/test_something.py"] = source
    expected = source.replace(
        "from producer import get_value\n",
        f"from producer import get_value\n\n{added}\n",
    ).replace("snapshot()", f"snapshot({code})")
    Example(files).run_inline(
        ["--inline-snapshot=create"],
        changed_files={"tests/test_something.py": Is(expected)},
    ).run_inline(changed_files={})
