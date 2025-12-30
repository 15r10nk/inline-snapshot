import ast
import copy
import io
import token
import tokenize
from collections import namedtuple
from pathlib import Path

from inline_snapshot._exceptions import UsageError

from ._code_repr import value_code_repr


def link(text, link=None):
    return f"[italic blue link={link or text}]{text}[/]"


def category_link(category):
    return link(
        category,
        f"https://15r10nk.github.io/inline-snapshot/latest/categories/#{category}",
    )


def is_relative_to(base: Path, relative: Path):
    try:
        relative.relative_to(base)
    except ValueError:
        return False
    return True


def normalize_strings(token_sequence):
    """Normalize string concattenanion.

    "a" "b" -> "ab"
    """

    current_string = None
    for t in token_sequence:
        if (
            t.type == token.STRING
            and not t.string.startswith(("'''", '"""', "b'''", 'b"""'))
            and t.string.startswith(("'", '"', "b'", 'b"'))
        ):
            if current_string is None:
                current_string = ast.literal_eval(t.string)
            else:
                current_string += ast.literal_eval(t.string)

            continue

        if current_string is not None:
            yield simple_token(token.STRING, repr(current_string))
            current_string = None

        yield t

    if current_string is not None:
        yield simple_token(token.STRING, repr(current_string))


def skip_trailing_comma(token_sequence):
    token_sequence = list(token_sequence)

    for index, token in enumerate(token_sequence):
        if index + 1 < len(token_sequence):
            next_token = token_sequence[index + 1]

            if token.string == "," and next_token.string in ("]", ")", "}"):
                continue
        yield token


def normalize(token_sequence):
    return skip_trailing_comma(normalize_strings(token_sequence))


ignore_tokens = (token.NEWLINE, token.ENDMARKER, token.NL)


# based on ast.unparse
def _str_literal_helper(string, *, quote_types):
    """Helper for writing string literals, minimizing escapes.

    Returns the tuple (string literal to write, possible quote types).
    """

    def escape_char(c):
        # \n and \t are non-printable, but we only escape them if
        # escape_special_whitespace is True
        if c in "\n\t":
            return c
        # Always escape backslashes and other non-printable characters
        if c == "\\" or not c.isprintable():
            return c.encode("unicode_escape").decode("ascii")
        if c == extra:
            return "\\" + c
        return c

    extra = ""
    if "'''" in string and '"""' in string:
        extra = '"' if string.count("'") >= string.count('"') else "'"

    escaped_string = "".join(map(escape_char, string))

    possible_quotes = [q for q in quote_types if q not in escaped_string]

    if escaped_string:
        # Sort so that we prefer '''"''' over """\""""
        possible_quotes.sort(key=lambda q: q[0] == escaped_string[-1])
        # If we're using triple quotes and we'd need to escape a final
        # quote, escape it
        if possible_quotes[0][0] == escaped_string[-1]:
            assert len(possible_quotes[0]) == 3
            escaped_string = escaped_string[:-1] + "\\" + escaped_string[-1]
    return escaped_string, possible_quotes


def triple_quote(string):
    """Write string literal value with a best effort attempt to avoid
    backslashes."""
    string, quote_types = _str_literal_helper(string, quote_types=['"""', "'''"])
    quote_type = quote_types[0]

    string = string.replace(" \n", " \\n\\\n")

    string = "\\\n" + string

    if not string.endswith("\n"):
        string = string + "\\\n"

    return f"{quote_type}{string}{quote_type}"


class simple_token(namedtuple("simple_token", "type,string")):

    def __eq__(self, other):
        if self.type == other.type == 3:
            if any(
                s.startswith(suffix)
                for s in (self.string, other.string)
                for suffix in ("f", "rf", "Rf", "F", "rF", "RF")
            ):
                # I don't know why this is not covered/(maybe needed) with the new customize algo
                # but I think it is better to handle it as 'no cover' for now
                return False  # pragma: no cover

            return ast.literal_eval(self.string) == ast.literal_eval(
                other.string
            ) and self.string.replace("'", '"') == other.string.replace("'", '"')
        else:
            return super().__eq__(other)


def value_to_token(value):
    from inline_snapshot._customize._custom import Custom

    assert isinstance(value, Custom)
    return map_strings(value.repr())


def map_strings(code_repr):
    input = io.StringIO(code_repr)

    return [
        simple_token(t.type, t.string)
        for t in tokenize.generate_tokens(input.readline)
        if t.type not in ignore_tokens
    ]


def clone(obj):
    new = copy.deepcopy(obj)
    if not obj == new:
        raise UsageError(
            f"""\
inline-snapshot uses `copy.deepcopy` to copy objects,
but the copied object is not equal to the original one:

value = {value_code_repr(obj)}
copied_value = copy.deepcopy(value)
assert value == copied_value

Please fix the way your object is copied or your __eq__ implementation.
"""
        )
    return new
