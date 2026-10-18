from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from typing import Union

from inline_snapshot._external._external_location import FileLocation
from inline_snapshot._external._format._protocol import Format
from inline_snapshot._external._format._protocol import get_format_handler_from_suffix
from inline_snapshot._external._storage._protocol import StorageLookupError
from inline_snapshot._global_state import state

from ._external_base import ExternalBase
from ._external_base import ExternalBaseData


@dataclass(eq=False, kw_only=True)
class ExternalFileData(ExternalBaseData):
    path: Path
    base_path: Path
    format: Format

    def __repr__(self) -> str:
        filename = self.path.resolve()
        try:
            path = filename.relative_to(self.base_path.resolve())
        except ValueError:  # pragma: no cover
            path = filename
        return f"external_file({str(path)!r})"


class ExternalFile(ExternalBase):

    def __init__(self, data: ExternalFileData):
        self._data = data

    @property
    def _format(self):
        return self._data.format

    def _is_empty(self):
        return not self._data.path.exists()

    def _assign(self, other):

        self._tmp_file = state().new_tmp_path(self._location.suffix)
        self._format.encode(other, self._tmp_file)

    def __repr__(self):
        return repr(self._data)

    def _load_value(self, which):
        if which == "new":
            if self._tmp_file:
                format = get_format_handler_from_suffix(self._location.suffix)
                return format.decode(self._tmp_file)
            else:
                raise StorageLookupError("no new value", files=[])
        if which == "old":
            try:
                return self._format.decode(self._data.path)
            except FileNotFoundError:
                raise StorageLookupError("old value not found", files=[])

        assert False


def external_file(path: Union[Path, str], *, format: Optional[str] = None):
    """
    Arguments:
        path: the path to the external file, relative to the directory of the current file.
        format: overwrite the format handler which should be used to load and save the content.
                It can be used to treat markdown files as text files with `format=".txt"` for example.
    """
    path = Path(path)

    from inspect import currentframe

    frame = currentframe()
    assert frame
    frame = frame.f_back
    assert frame
    base_path = Path(frame.f_code.co_filename).parent

    if not path.is_absolute():
        path = base_path / path

    path = path.resolve()

    if format is None:
        format = path.suffix

    format_handler = get_format_handler_from_suffix(format)

    if not state().active:
        return format_handler.decode(path)

    key = ("file", path)
    data = state().snapshots.get(key)
    if not isinstance(data, ExternalFileData):
        location = FileLocation(path)
        data = ExternalFileData(
            original_location=location,
            location=location,
            path=path,
            base_path=base_path,
            format=format_handler,
        )
        state().snapshots[key] = data

    assert data.format.suffix == format_handler.suffix

    return ExternalFile(data)
