from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Generator

from inline_snapshot._adapter_context import AdapterContext
from inline_snapshot._change import ChangeBase
from inline_snapshot._change import ExternalChange
from inline_snapshot._change import RequiredImports
from inline_snapshot._external._external_location import ExternalLocation
from inline_snapshot._external._format._protocol import get_format_handler

from ._custom import Custom


@dataclass(frozen=True)
class CustomExternal(Custom):
    value: Any
    format: str | None = None
    storage: str | None = None

    def _map(self, f):
        return f(self.value)

    def _code_repr(self, context: AdapterContext) -> Generator[ChangeBase, None, str]:
        from inline_snapshot._global_state import state

        storage_name = self.storage or state().config.default_storage

        format = get_format_handler(self.value, self.format or "")

        location = ExternalLocation(
            storage=storage_name,
            stem="",
            suffix=self.format or format.suffix,
            filename=Path(context.file.filename),
            qualname=context.qualname,
        )

        tmp_file = state().new_tmp_path(location.suffix)

        storage = state().all_storages[storage_name]

        format.encode(self.value, tmp_file)
        location = storage.new_location(location, tmp_file)

        yield ExternalChange(
            "create",
            tmp_file,
            ExternalLocation.from_name("", context=context),
            location,
            format,
        )
        yield RequiredImports(
            "create", context.file, {"inline_snapshot": ["external"]}, []
        )

        return f"external({location.to_str()!r})"
