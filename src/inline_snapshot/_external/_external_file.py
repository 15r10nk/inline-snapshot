from pathlib import Path
from typing import Optional
from typing import Union
from typing import cast

from inline_snapshot._external._external_location import FileLocation
from inline_snapshot._external._format._protocol import Format
from inline_snapshot._external._format._protocol import get_format_handler_from_suffix
from inline_snapshot._external._storage._protocol import StorageLookupError
from inline_snapshot._global_state import state
from inline_snapshot._types import SnapshotRefBase

from ._external_base import ExternalBase


class ExternalFile(ExternalBase, SnapshotRefBase):

    def __init__(self, filename: Path, format: Format):
        self._filename = filename
        self._format = format
        self._tmp_file = None

        self._location = FileLocation(self._filename)
        self._original_location = self._location
        super().__init__()

    def _is_empty(self):
        return not self._filename.exists()

    def _assign(self, other):

        self._tmp_file = state().new_tmp_path(self._location.suffix)
        self._format.encode(other, self._tmp_file)

    def __repr__(self):
        return f"external_file({str(self._filename)!r})"

    def _load_value(self):
        try:
            return self._format.decode(self._filename)
        except FileNotFoundError:
            raise StorageLookupError(f"can not read {self._filename}")


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

    if not state().active:
        return format_handler.decode(path)

    key = ("file", path)
    if key not in state().snapshots:
        new = ExternalFile(path, format_handler)
        state().snapshots[key] = new
    else:
        new = cast(ExternalFile, state().snapshots[key])

    assert new._format.suffix == format_handler.suffix

    return new
