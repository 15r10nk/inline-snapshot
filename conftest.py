import pytest

from inline_snapshot._external import external
from tests.utils import snapshot_env
from tests.utils import storage  # noqa
from tests.utils import useStorage


@pytest.fixture(autouse=True)
def snapshot_env_for_doctest(request, tmp_path):
    if hasattr(request.node, "dtest"):
        with snapshot_env():
            storage = external.HashStorage(tmp_path / ".storage")
            with useStorage(storage):
                yield
    else:
        yield
