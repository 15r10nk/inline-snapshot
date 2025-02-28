import pytest

from tests.utils import snapshot_env
from tests.utils import storage  # noqa


@pytest.fixture(autouse=True)
def snapshot_env_for_doctest(request):
    if hasattr(request.node, "dtest"):
        with snapshot_env():
            with storage():
                yield
    else:
        yield
