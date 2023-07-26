import ast
import copy
import inspect
import io
import sys
import token
import tokenize
from collections import namedtuple
from pathlib import Path
from typing import Any
from typing import Dict  # noqa
from typing import overload
from typing import Tuple  # noqa
from typing import TypeVar

from executing import Source

from ._format import format_code
from ._rewrite_code import ChangeRecorder
from ._rewrite_code import end_of
from ._rewrite_code import start_of


# sentinels
class Undefined:
    pass


undefined = Undefined()

snapshots = {}  # type: Dict[Tuple[int, int], Snapshot]

_active = False

_files_with_snapshots = set()


class Flags:
    """
    fix: the value needs to be changed to pass the tests
    update: the value should be updated because the token-stream has changed
    create: the snapshot is empty `snapshot()`
    trim: the snapshot contains more values than neccessary. 1 could be trimmed in `5 in snapshot([1,5])`.
    """

    def __init__(self, flags=set()):
        self.fix = "fix" in flags
        self.update = "update" in flags
        self.create = "create" in flags
        self.trim = "trim" in flags

    def change_something(self):
        return self.fix or self.update or self.create or self.trim

    def to_set(self):
        return {k for k, v in self.__dict__.items() if v}

    def __repr__(self):
        return f"Flags({self.to_set()})"


_update_flags = Flags()


def ignore_old_value():
    return _update_flags.fix or _update_flags.update


class GenericValue:
    _new_value: Any
    _old_value: Any
    _current_op = "undefined"

    def _needs_trim(self):
        return False

    def _needs_create(self):
        return self._old_value == undefined

    def _needs_fix(self):
        raise NotImplemented

    def _ignore_old(self):
        return (
            _update_flags.fix
            or _update_flags.update
            or _update_flags.create
            or self._old_value is undefined
        )

    def _visible_value(self):
        if self._ignore_old():
            return self._new_value
        else:
            return self._old_value

    def get_result(self, flags):
        return self._old_value

    def __repr__(self):
        return repr(self._visible_value())

    def _type_error(self, op):
        __tracebackhide__ = True
        raise TypeError(
            f"This snapshot cannot be use with `{op}`, because it was previously used with `{self._current_op}`"
        )

    def __eq__(self, _other):
        __tracebackhide__ = True
        self._type_error("==")

    def __le__(self, _other):
        __tracebackhide__ = True
        self._type_error("<=")

    def __ge__(self, _other):
        __tracebackhide__ = True
        self._type_error(">=")

    def __contains__(self, _other):
        __tracebackhide__ = True
        self._type_error("in")

    def __getitem__(self, _item):
        __tracebackhide__ = True
        self._type_error("snapshot[key]")


class UndecidedValue(GenericValue):
    def __init__(self, _old_value):
        self._old_value = _old_value
        self._new_value = undefined

    def _change(self, cls):
        self.__class__ = cls

    def _needs_fix(self):
        return False

    # functions which determine the type

    def __eq__(self, other):
        self._change(EqValue)
        return self == other

    def __le__(self, other):
        self._change(MinValue)
        return self <= other

    def __ge__(self, other):
        self._change(MaxValue)
        return self >= other

    def __contains__(self, other):
        self._change(CollectionValue)
        return other in self

    def __getitem__(self, item):
        self._change(DictValue)
        return self[item]


class EqValue(GenericValue):
    _current_op = "x == snapshot"

    def __eq__(self, other):
        other = copy.deepcopy(other)

        if self._new_value is undefined:
            self._new_value = other

        return self._visible_value() == other

    def _needs_fix(self):
        return self._old_value is not undefined and self._old_value != self._new_value

    def get_result(self, flags):
        if flags.fix and self._needs_fix() or flags.create and self._needs_create():
            return self._new_value
        return self._old_value


class MinMaxValue(GenericValue):
    """Generic implementation for <=, >="""

    @staticmethod
    def cmp(a, b):
        raise NotImplemented

    def _generic_cmp(self, other):
        other = copy.deepcopy(other)

        if self._new_value is undefined:
            self._new_value = other
        else:
            self._new_value = (
                self._new_value if self.cmp(self._new_value, other) else other
            )

        return self.cmp(self._visible_value(), other)

    def _needs_trim(self):
        if self._old_value is undefined:
            return False

        return not self.cmp(self._new_value, self._old_value)

    def _needs_fix(self):
        if self._old_value is undefined:
            return False
        return not self.cmp(self._old_value, self._new_value)

    def get_result(self, flags):
        if flags.create and self._needs_create():
            return self._new_value

        if flags.fix and self._needs_fix():
            return self._new_value

        if flags.trim and self._needs_trim():
            return self._new_value

        return self._old_value


class MinValue(MinMaxValue):
    """
    handles:

    >>> snapshot(5) <= 6
    True

    >>> 6 >= snapshot(5)
    True

    """

    _current_op = "x >= snapshot"

    @staticmethod
    def cmp(a, b):
        return a <= b

    __le__ = MinMaxValue._generic_cmp


class MaxValue(MinMaxValue):
    """
    handles:

    >>> snapshot(5) >= 4
    True

    >>> 4 <= snapshot(5)
    True

    """

    _current_op = "x <= snapshot"

    @staticmethod
    def cmp(a, b):
        return a >= b

    __ge__ = MinMaxValue._generic_cmp


class CollectionValue(GenericValue):
    _current_op = "x in snapshot"

    def __contains__(self, item):
        item = copy.deepcopy(item)

        if self._new_value is undefined:
            self._new_value = [item]
        else:
            if item not in self._new_value:
                self._new_value.append(item)

        if ignore_old_value() or self._old_value is undefined:
            return True
        else:
            return item in self._old_value

    def _needs_trim(self):
        if self._old_value is undefined:
            return False
        return any(item not in self._new_value for item in self._old_value)

    def _needs_fix(self):
        if self._old_value is undefined:
            return False
        return any(item not in self._old_value for item in self._new_value)

    def get_result(self, flags):
        if (flags.fix and flags.trim) or (flags.create and self._needs_create()):
            return self._new_value

        if self._old_value is not undefined:
            if flags.fix:
                return self._old_value + [
                    v for v in self._new_value if v not in self._old_value
                ]

            if flags.trim:
                return [v for v in self._old_value if v in self._new_value]

        return self._old_value


class DictValue(GenericValue):
    _current_op = "snapshot[key]"

    def __getitem__(self, index):
        if self._new_value is undefined:
            self._new_value = {}

        old_value = self._old_value
        if old_value is undefined:
            old_value = {}

        if index not in self._new_value:
            self._new_value[index] = UndecidedValue(old_value.get(index, undefined))

        return self._new_value[index]

    def _needs_fix(self):
        if self._old_value is not undefined and self._new_value is not undefined:
            if any(v._needs_fix() for v in self._new_value.values()):
                return True

        return False

    def _needs_trim(self):
        if self._old_value is not undefined and self._new_value is not undefined:
            if any(v._needs_trim() for v in self._new_value.values()):
                return True

            return any(item not in self._new_value for item in self._old_value)
        return False

    def _needs_create(self):
        if super()._needs_create():
            return True

        return any(item not in self._old_value for item in self._new_value)

    def get_result(self, flags):
        result = {k: v.get_result(flags) for k, v in self._new_value.items()}

        result = {k: v for k, v in result.items() if v is not undefined}

        if not flags.trim and self._old_value is not undefined:
            for k, v in self._old_value.items():
                if k not in result:
                    result[k] = v

        return result


T = TypeVar("T")

found_snapshots = []


class ReprWrapper:
    def __init__(self, func):
        self.func = func

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def __repr__(self):
        return self.func.__name__


_T = TypeVar("_T")


def repr_wrapper(func: _T) -> _T:
    return ReprWrapper(func)  # type: ignore


@overload
def snapshot() -> Any:
    ...


@overload
def snapshot(obj: T) -> T:
    ...


@repr_wrapper
def snapshot(obj=undefined):
    """`snapshot()` is a placeholder for some value.

    `pytest --inline-snapshot=create` will create the value which matches your conditions.

    >>> assert 5 == snapshot()
    >>> assert 5 <= snapshot()
    >>> assert 5 >= snapshot()
    >>> assert 5 in snapshot()

    `snapshot()[key]` can be used to create sub-snapshots.

    The generated value will be inserted as argument to `snapshot()`

    >>> assert 5 == snapshot(5)

    `snapshot(value)` has the semantic of an noop which returns `value`.
    """
    if not _active:
        if isinstance(obj, Undefined):
            raise AssertionError(
                "your snapshot is missing a value run pytest with --inline-snapshot=create"
            )
        else:
            return obj

    frame = inspect.currentframe().f_back.f_back
    expr = Source.executing(frame)

    module = inspect.getmodule(frame)
    if module is not None:
        _files_with_snapshots.add(module.__file__)

    key = id(frame.f_code), frame.f_lasti

    if key not in snapshots:
        node = expr.node
        if node is None:
            # we can run without knowing of the calling expression but we will not be able to fix code
            snapshots[key] = Snapshot(obj, None)
        else:
            assert isinstance(node.func, ast.Name)
            assert node.func.id == "snapshot"
            snapshots[key] = Snapshot(obj, expr)
        found_snapshots.append(snapshots[key])

    return snapshots[key]._value


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

    string = "\\\n" + string

    if not string.endswith("\n"):
        string = string + "\\\n"

    return f"{quote_type}{string}{quote_type}"


simple_token = namedtuple("simple_token", "type,string")


def used_externals(tree):
    if sys.version_info < (3, 8):
        return [
            n.args[0].s
            for n in ast.walk(tree)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name)
            and n.func.id == "external"
            and n.args
            and isinstance(n.args[0], ast.Str)
        ]
    else:
        return [
            n.args[0].value
            for n in ast.walk(tree)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name)
            and n.func.id == "external"
            and n.args
            and isinstance(n.args[0], ast.Constant)
        ]


class Snapshot:
    def __init__(self, value, expr):
        self._expr = expr
        self._value = UndecidedValue(value)
        self._uses_externals = []

    @property
    def _filename(self):
        return self._expr.source.filename

    def _format(self, text):
        return format_code(text, Path(self._filename))

    def _value_to_token(self, value):
        if value is undefined:
            return []
        input = io.StringIO(self._format(repr(value)))

        def map_string(tok):
            """Convert strings with newlines in triple quoted strings."""
            if tok.type == token.STRING:
                s = ast.literal_eval(tok.string)
                if isinstance(s, str) and "\n" in s:
                    # unparse creates a triple quoted string here,
                    # because it thinks that the string should be a docstring
                    tripple_quoted_string = triple_quote(s)

                    assert ast.literal_eval(tripple_quoted_string) == s

                    return simple_token(tok.type, tripple_quoted_string)

            return simple_token(tok.type, tok.string)

        return [
            map_string(t)
            for t in tokenize.generate_tokens(input.readline)
            if t.type not in ignore_tokens
        ]

    def _change(self):
        assert self._expr is not None

        change = ChangeRecorder.current.new_change()

        tokens = list(self._expr.source.asttokens().get_tokens(self._expr.node))
        assert tokens[0].string == "snapshot"
        assert tokens[1].string == "("
        assert tokens[-1].string == ")"

        change.set_tags("inline_snapshot")

        needs_fix = self._value._needs_fix()
        needs_create = self._value._needs_create()
        needs_trim = self._value._needs_trim()
        needs_update = self._needs_update()

        if (
            _update_flags.update
            and needs_update
            or _update_flags.fix
            and needs_fix
            or _update_flags.create
            and needs_create
            or _update_flags.trim
            and needs_trim
        ):
            new_value = self._value.get_result(_update_flags)

            text = self._format(
                tokenize.untokenize(self._value_to_token(new_value))
            ).strip()

            try:
                tree = ast.parse(text)
            except:
                return

            self._uses_externals = used_externals(tree)

            change.replace(
                (end_of(tokens[1]), start_of(tokens[-1])),
                text,
                filename=self._filename,
            )

    def _current_tokens(self):
        if not self._expr.node.args:
            return []

        return [
            simple_token(t.type, t.string)
            for t in self._expr.source.asttokens().get_tokens(self._expr.node.args[0])
            if t.type not in ignore_tokens
        ]

    def _normalize_strings(self, token_sequence):
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
                yield (token.STRING, repr(current_string))
                current_string = None

            yield t

        if current_string is not None:
            yield (token.STRING, repr(current_string))

    def _needs_update(self):
        return self._expr is not None and [] != list(
            self._normalize_strings(self._current_tokens())
        ) != list(self._normalize_strings(self._value_to_token(self._value._old_value)))

    @property
    def _flags(self):
        s = set()
        if self._value._needs_fix():
            s.add("fix")
        if self._value._needs_trim():
            s.add("trim")
        if self._value._needs_create():
            s.add("create")
        if self._value._old_value is not undefined and self._needs_update():
            s.add("update")

        return s
