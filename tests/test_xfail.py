from inline_snapshot import snapshot
from inline_snapshot.testing import Example


def test_xfail_snapshot_from_module_fixture():
    Example("""\
import pytest
from inline_snapshot import snapshot

@pytest.fixture(scope="module")
def expected():
    return snapshot(3 + 2)

@pytest.mark.xfail(strict=False)
def test_value(expected):
    assert expected == 5
""").run_pytest(
        ["--inline-snapshot=update"],
        report=snapshot(""),
        changed_files={},
        outcomes={"xpassed": 1},
    )


def test_xfail_min_max_update_from_module_fixtures():
    Example("""\
import pytest
from inline_snapshot import snapshot

@pytest.fixture(scope="module")
def lower():
    return snapshot(3 + 2)

@pytest.fixture(scope="module")
def upper():
    return snapshot(3 + 2)

@pytest.mark.xfail(strict=False)
def test_bounds(lower, upper):
    assert lower <= 5
    assert upper >= 5
""").run_pytest(
        ["--inline-snapshot=update"],
        changed_files=snapshot({"tests/test_something.py": """\
import pytest
from inline_snapshot import snapshot

@pytest.fixture(scope="module")
def lower():
    return snapshot(5)

@pytest.fixture(scope="module")
def upper():
    return snapshot(5)

@pytest.mark.xfail(strict=False)
def test_bounds(lower, upper):
    assert lower <= 5
    assert upper >= 5
"""}),
        outcomes={"xpassed": 1},
    ).run_pytest(
        ["--inline-snapshot=short-report"],
        report=snapshot(""),
        changed_files={},
        outcomes={"xpassed": 1},
    )


def test_xfail_without_condition():

    Example("""\
import pytest

@pytest.mark.xfail
def test_a():
    assert 1==snapshot(5)
""").run_pytest(
        ["--inline-snapshot=fix"],
        report=snapshot(""),
        returncode=snapshot(0),
        stderr=snapshot(""),
        changed_files=snapshot({}),
        outcomes={"xfailed": 1},
    )


def test_xfail_True():
    Example("""\
import pytest
from inline_snapshot import snapshot

@pytest.mark.xfail(True,reason="...")
def test_a():
    assert 1==snapshot(5)
""").run_pytest(
        ["--inline-snapshot=fix"],
        report=snapshot(""),
        returncode=snapshot(0),
        stderr=snapshot(""),
        changed_files=snapshot({}),
        outcomes={"xfailed": 1},
    )


def test_xfail_False():
    Example("""\
import pytest
from inline_snapshot import snapshot

@pytest.mark.xfail(False,reason="...")
def test_a():
    assert 1==snapshot(5)
""").run_pytest(
        ["--inline-snapshot=fix"],
        report=snapshot("""\
-------------------------------- Fix snapshots ---------------------------------
+-------------------------- tests/test_something.py ---------------------------+
| @@ -3,4 +3,4 @@                                                              |
|                                                                              |
|                                                                              |
|  @pytest.mark.xfail(False,reason="...")                                      |
|  def test_a():                                                               |
| -    assert 1==snapshot(5)                                                   |
| +    assert 1==snapshot(1)                                                   |
+------------------------------------------------------------------------------+
These changes will be applied, because you used fix\
"""),
        returncode=snapshot(1),
        stderr=snapshot(""),
        changed_files=snapshot({"tests/test_something.py": """\
import pytest
from inline_snapshot import snapshot

@pytest.mark.xfail(False,reason="...")
def test_a():
    assert 1==snapshot(1)
"""}),
        outcomes={"passed": 1, "errors": 1},
    )
