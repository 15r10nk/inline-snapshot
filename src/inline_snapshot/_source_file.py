import tokenize
from pathlib import Path

from executing import Source

from inline_snapshot._code_repr import code_repr
from inline_snapshot._format import enforce_formatting
from inline_snapshot._format import format_code
from inline_snapshot._generator_utils import only_value
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

    def format_expression(self, code):
        return self._format(code).strip()

    def asttokens(self):
        return self._source.asttokens()

    def _token_to_code(self, tokens):
        return self.format_expression(tokenize.untokenize(tokens))

    def _value_to_code(self, value, context):
        from inline_snapshot._customize._custom import Custom

        if isinstance(value, Custom):
            return self.format_expression(only_value(value.repr(context)))
        else:
            # TODO assert False
            return self.format_expression(code_repr(value))

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
