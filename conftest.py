import pytest

from tests.utils import snapshot_env
from tests.utils import storage  # noqa
from tests.utils import useStorage


@pytest.fixture(autouse=True)
def snapshot_env_for_doctest(request, storage):
    if hasattr(request.node, "dtest"):
        with snapshot_env():
            with useStorage(storage):
                yield
    else:
        yield
