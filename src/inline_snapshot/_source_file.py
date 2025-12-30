from pathlib import Path

from executing import Source

from inline_snapshot._format import enforce_formatting
from inline_snapshot._format import format_code
from inline_snapshot._utils import normalize
from inline_snapshot._utils import simple_token

from ._utils import ignore_tokens
from ._utils import map_strings


class SourceFile:
    _source: Source

    def __init__(self, source: Source):
        self._source = source

    @property
    def filename(self) -> str:
        return self._source.filename

    def _format(self, code):
        if self._source is None or enforce_formatting():
            return code
        else:
            return format_code(code, Path(self._source.filename))

    def format_expression(self, code: str) -> str:
        return self._format(code).strip()

    def asttokens(self):
        return self._source.asttokens()

    def code_changed(self, old_node, new_code):

        if old_node is None:
            return False

        new_token = map_strings(new_code)

        return self._token_of_node(old_node) != new_token

    def _token_of_node(self, node):

        return list(
            normalize(
                [
                    simple_token(t.type, t.string)
                    for t in self._source.asttokens().get_tokens(node)
                    if t.type not in ignore_tokens
                ]
            )
        )
