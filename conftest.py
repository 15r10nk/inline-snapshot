import pytest

from inline_snapshot._external import DiscStorage
from tests.utils import snapshot_env
from tests.utils import useStorage


@pytest.fixture(autouse=True)
def snapshot_env_for_doctest(request, tmp_path):
    if hasattr(request.node, "dtest"):
        with snapshot_env():
            storage = DiscStorage(tmp_path / ".storage")
            with useStorage(storage):
                yield
    else:
        yield
