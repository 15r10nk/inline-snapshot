import pytest

from inline_snapshot.testing._example import snapshot_env


@pytest.fixture(autouse=True)
def snapshot_env_for_doctest(request):
    if hasattr(request.node, "dtest"):
        with snapshot_env():
            yield
    else:
        yield
