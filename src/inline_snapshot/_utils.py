import ast
import io
import token
import tokenize
from collections import namedtuple

from ._code_repr import code_repr


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
                return False

            return ast.literal_eval(self.string) == ast.literal_eval(
                other.string
            ) and self.string.replace("'", '"') == other.string.replace("'", '"')
        else:
            return super().__eq__(other)


def value_to_token(value):
    input = io.StringIO(code_repr(value))

    def map_string(tok):
        """Convert strings with newlines in triple quoted strings."""
        if tok.type == token.STRING:
            s = ast.literal_eval(tok.string)
            if isinstance(s, str) and (
                ("\n" in s and s[-1] != "\n") or s.count("\n") > 1
            ):
                # unparse creates a triple quoted string here,
                # because it thinks that the string should be a docstring
                triple_quoted_string = triple_quote(s)

                assert ast.literal_eval(triple_quoted_string) == s

                return simple_token(tok.type, triple_quoted_string)

        return simple_token(tok.type, tok.string)

    return [
        map_string(t)
        for t in tokenize.generate_tokens(input.readline)
        if t.type not in ignore_tokens
    ]
