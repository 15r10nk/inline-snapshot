from pathlib import Path
from typing import Iterator
from typing import Union
from typing import cast

from inline_snapshot._change import ChangeBase
from inline_snapshot._change import ExternalChange
from inline_snapshot._external._external_location import FileLocation
from inline_snapshot._external._format import Format
from inline_snapshot._external._format import get_format_handler_from_suffix
from inline_snapshot._external._tmp_path import new_tmp_path
from inline_snapshot._global_state import state
from inline_snapshot._types import SnapshotRefBase


class ExternalFile(SnapshotRefBase):

    def __init__(self, filename: Path, format: Format):
        self._filename = filename
        self._format = format
        self._value_changed = False
        self._tmp_file = None

    def _changes(self) -> Iterator[ChangeBase]:

        file_location = FileLocation(self._filename)
        if self._value_changed and state().update_flags.fix:
            assert self._tmp_file
            yield ExternalChange(
                "fix", self._tmp_file, file_location, file_location, self._format
            )
        elif not self._filename.exists() and state().update_flags.create:
            assert self._tmp_file
            yield ExternalChange(
                "create", self._tmp_file, file_location, file_location, self._format
            )

    def __eq__(self, other):
        if not self._filename.exists():
            state().missing_values += 1

            if state().update_flags.create:
                self._tmp_file = new_tmp_path(self._filename.suffix)
                self._format.encode(other, self._tmp_file)
                return True
            return False

        if self._load_value() != other:
            state().incorrect_values += 1

            if state().update_flags.fix:
                self._tmp_file = new_tmp_path(self._filename.suffix)
                self._format.encode(other, self._tmp_file)
                self._value_changed = True
                return True
            return False

        return True

    def _load_value(self):
        return self._format.decode(self._filename)


def external_file(path: Union[Path, str], format=None):
    path = Path(path).resolve()

    if format is None:
        format = get_format_handler_from_suffix(path.suffix)

    key = ("file", path)
    if key not in state().snapshots:
        new = ExternalFile(path, format)
        state().snapshots[key] = new
    else:
        new = cast(ExternalFile, state().snapshots[key])

    assert new._format == format

    return new
