import tokenize
from pathlib import Path

from executing import Source

from inline_snapshot._format import enforce_formatting
from inline_snapshot._format import format_code
from inline_snapshot._utils import normalize
from inline_snapshot._utils import simple_token
from inline_snapshot._utils import value_to_token

from ._utils import ignore_tokens


class SourceFile:
    _source: Source

    def __init__(self, source: Source):
        self._source = source

    @property
    def filename(self):
        return self._source.filename

    def _format(self, text):
        if self._source is None or enforce_formatting():
            return text
        else:
            return format_code(text, Path(self._source.filename))

    def asttokens(self):
        return self._source.asttokens()

    def _token_to_code(self, tokens):
        return self._format(tokenize.untokenize(tokens)).strip()

    def _value_to_code(self, value):
        return self._token_to_code(value_to_token(value))

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
