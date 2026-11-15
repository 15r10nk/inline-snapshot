import builtins
import sys

import pytest

from inline_snapshot._core._global_state import enter_snapshot_context
from inline_snapshot._core._global_state import leave_snapshot_context
from inline_snapshot._core._global_state import snapshot_env


@pytest.mark.parametrize("package", ["attrs", "pydantic", "dirty_equals"])
def test_missing_optional_package(monkeypatch, package):
    monkeypatch.setitem(sys.modules, package, None)

    with snapshot_env() as state:
        extensions = {
            type(plugin).__module__.rsplit(".", 1)[-1]
            for plugin in state.pm.get_plugins()
            if type(plugin).__module__.startswith("inline_snapshot._extensions.")
        }
        assert extensions == {"attrs", "pydantic", "dirty_equals"} - {package}


@pytest.mark.parametrize("package", ["attrs", "pydantic", "dirty_equals"])
def test_extension_import_error_is_not_suppressed(monkeypatch, package):
    original_import = builtins.__import__
    error = ImportError("broken extension dependency")

    def import_with_broken_extension(name, *args, **kwargs):
        if name == f"inline_snapshot._extensions.{package}":
            raise error
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_with_broken_extension)

    try:
        with pytest.raises(ImportError) as raised:
            enter_snapshot_context()
        assert raised.value is error
    finally:
        leave_snapshot_context()
