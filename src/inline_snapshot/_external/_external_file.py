from pathlib import Path
from typing import Iterator
from typing import Optional
from typing import Union
from typing import cast

from inline_snapshot._change import ChangeBase
from inline_snapshot._change import ExternalChange
from inline_snapshot._external._external_location import FileLocation
from inline_snapshot._external._format._protocol import Format
from inline_snapshot._external._format._protocol import get_format_handler_from_suffix
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
        elif (
            not self._filename.exists()
            and state().update_flags.create
            and self._tmp_file is not None
        ):
            assert self._tmp_file
            yield ExternalChange(
                "create", self._tmp_file, file_location, file_location, self._format
            )

    def __eq__(self, other):
        if not self._filename.exists():
            state().missing_values += 1

            if state().update_flags.create:
                self._tmp_file = state().new_tmp_path(self._filename.suffix)
                self._format.encode(other, self._tmp_file)
                return True
            return False

        if self._load_value() != other:
            state().incorrect_values += 1

            if state().update_flags.fix:
                self._tmp_file = state().new_tmp_path(self._filename.suffix)
                self._format.encode(other, self._tmp_file)
                self._value_changed = True
                return True
            return False

        return True

    def _load_value(self):
        return self._format.decode(self._filename)


def external_file(path: Union[Path, str], *, format: Optional[str] = None):
    """
    Arguments:
        path: the path to the external file, relative to the directory of the current file.
        format: overwrite the format handler which should be used to load and save the content.
                It can be used to treat markdown files as text files with `format=".txt"` for example.
    """
    path = Path(path)

    if not path.is_absolute():
        from inspect import currentframe

        frame = currentframe()
        assert frame
        frame = frame.f_back
        assert frame
        path = Path(frame.f_code.co_filename).parent / path

    path = path.resolve()

    if format is None:
        format = path.suffix

    format_handler = get_format_handler_from_suffix(format)

    key = ("file", path)
    if key not in state().snapshots:
        new = ExternalFile(path, format_handler)
        state().snapshots[key] = new
    else:
        new = cast(ExternalFile, state().snapshots[key])

    assert new._format.suffix == format_handler.suffix

    return new
