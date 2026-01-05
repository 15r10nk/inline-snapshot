import pytest

from inline_snapshot._global_state import snapshot_env


@pytest.fixture(autouse=True)
def snapshot_env_for_doctest(request):
    if hasattr(request.node, "dtest"):
        with snapshot_env():
            yield
    else:
        yield


from inline_snapshot import customize, Builder
from dirty_equals import IsNow


@customize
def is_now_handler(value, builder: Builder):
    if value == IsNow():
        return IsNow
