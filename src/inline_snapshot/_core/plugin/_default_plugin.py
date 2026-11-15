import ast
import datetime
import sys
from collections import Counter
from collections import defaultdict
from dataclasses import MISSING
from dataclasses import fields
from dataclasses import is_dataclass
from enum import Enum
from enum import Flag
from pathlib import Path
from pathlib import PurePath
from types import BuiltinFunctionType
from types import CodeType
from types import FunctionType
from typing import Any
from typing import Dict
from typing import NewType

from inline_snapshot._core._customize._builder import Builder
from inline_snapshot._core._customize._custom_code import ImportFrom
from inline_snapshot._core._customize._custom_undefined import CustomUndefined
from inline_snapshot._core._customize._custom_unmanaged import CustomUnmanaged
from inline_snapshot._core._external._outsource import Outsourced
from inline_snapshot._core._sentinels import undefined
from inline_snapshot._core._unmanaged import is_unmanaged
from inline_snapshot._core._utils import triple_quote

from ._spec import customize


class InlineSnapshotPlugin:
    @customize
    def standard_handler(self, value, builder: Builder):
        if isinstance(value, list):
            return builder.create_list(value)

        if type(value) is tuple:
            return builder.create_tuple(value)

        if isinstance(value, dict):
            return builder.create_dict(value)

    @customize
    def string_handler(self, value, builder: Builder):
        if isinstance(value, str) and (
            ("\n" in value and value[-1] != "\n") or value.count("\n") > 1
        ):

            triple_quoted_string = triple_quote(value)

            assert ast.literal_eval(triple_quoted_string) == value

            return builder.create_code(triple_quoted_string)

    @customize(tryfirst=True)
    def counter_handler(self, value, builder: Builder):
        if isinstance(value, Counter):
            return builder.create_call(Counter, [dict(value)])

    @customize
    def function_and_type_handler(
        self, value, builder: Builder, local_vars: Dict[str, Any]
    ):
        if isinstance(value, (FunctionType, type)):
            if value is CodeType:
                # delete when customize_repr is removed
                return builder.create_code(
                    "CodeType", imports=[ImportFrom("types", "CodeType")]
                )

            for name, local_value in local_vars.items():
                if local_value is value:
                    return builder.create_code(name)

            qualname = value.__qualname__.split("[")[0]
            name = qualname.split(".")[0]
            return builder.create_code(
                qualname, imports=[ImportFrom(value.__module__, name)]
            )

    if sys.version_info >= (3, 10):

        @customize
        def typing_newtype_handler(
            self, value, builder: Builder, local_vars: Dict[str, Any]
        ):
            if type(value) is NewType:
                for name, local_value in local_vars.items():
                    if local_value is value:
                        return builder.create_code(name)

                qualname = value.__qualname__.split("[")[0]  # type: ignore[attr-defined]
                name = qualname.split(".")[0]
                return builder.create_code(
                    qualname, imports=[ImportFrom(value.__module__, name)]
                )

    @customize
    def builtin_function_handler(self, value, builder: Builder):
        if isinstance(value, BuiltinFunctionType):
            return builder.create_code(value.__name__)

    @customize
    def timezone_handler(self, value, builder: Builder):
        if type(value) is datetime.timezone:
            # Handle timezone.utc specially - it's a constant, not a constructor call
            if value == datetime.timezone.utc:
                return builder.create_code(
                    "timezone.utc",
                    imports=[ImportFrom("datetime", "timezone")],
                )

            # For other timezone objects, use the constructor
            offset = value.utcoffset(None)
            tzname = value.tzname(None)
            return builder.create_call(datetime.timezone, [offset, tzname])

    @customize
    def datetime_handler(self, value, builder: Builder):

        if type(value) is datetime.datetime:
            return builder.create_call(
                datetime.datetime,
                [value.year, value.month, value.day],
                {
                    "hour": builder.with_default(value.hour, 0),
                    "minute": builder.with_default(value.minute, 0),
                    "second": builder.with_default(value.second, 0),
                    "microsecond": builder.with_default(value.microsecond, 0),
                    "tzinfo": builder.with_default(value.tzinfo, None),
                },
            )

        if type(value) is datetime.date:
            return builder.create_call(
                datetime.date, [value.year, value.month, value.day]
            )

        if type(value) is datetime.time:
            return builder.create_call(
                datetime.time,
                [],
                {
                    "hour": builder.with_default(value.hour, 0),
                    "minute": builder.with_default(value.minute, 0),
                    "second": builder.with_default(value.second, 0),
                    "microsecond": builder.with_default(value.microsecond, 0),
                    "tzinfo": builder.with_default(value.tzinfo, None),
                },
            )

        if type(value) is datetime.timedelta:
            return builder.create_call(
                datetime.timedelta,
                [],
                {
                    "days": builder.with_default(value.days, 0),
                    "seconds": builder.with_default(value.seconds, 0),
                    "microseconds": builder.with_default(value.microseconds, 0),
                },
            )

    @customize
    def path_handler(self, value, builder: Builder):
        if isinstance(value, Path):
            return builder.create_call(Path, [value.as_posix()])

        if isinstance(value, PurePath):
            return builder.create_call(PurePath, [value.as_posix()])

    @customize
    def set_handler(self, value, builder: Builder):
        if isinstance(value, set):
            return builder.create_set(value)

    @customize
    def frozenset_handler(self, value, builder: Builder):
        if isinstance(value, frozenset):
            if len(value) == 0:
                return builder.create_code("frozenset()")
            else:
                return builder.create_call(frozenset, [set(value)])

    # -8<- [start:Enum]
    @customize
    def enum_handler(self, value, builder: Builder):
        if isinstance(value, Enum):
            qualname = type(value).__qualname__
            name = qualname.split(".")[0]

            return builder.create_code(
                f"{type(value).__qualname__}.{value.name}",
                imports=[ImportFrom(type(value).__module__, name)],
            )

    # -8<- [end:Enum]

    @customize
    def flag_handler(self, value, builder: Builder):
        if isinstance(value, Flag):
            qualname = type(value).__qualname__
            name = qualname.split(".")[0]

            return builder.create_code(
                " | ".join(
                    f"{qualname}.{flag.name}" for flag in type(value) if flag in value
                ),
                imports=[ImportFrom(type(value).__module__, name)],
            )

    @customize
    def source_file_name_handler(self, value, builder: Builder, global_vars):
        if "__file__" in global_vars and value == global_vars["__file__"]:
            return builder.create_code("__file__")

    @customize
    def dataclass_handler(self, value, builder: Builder):

        if is_dataclass(value) and not isinstance(value, type):

            kwargs = {}

            for field in fields(value):  # type: ignore
                if field.repr:
                    field_value = getattr(value, field.name)

                    if sys.version_info >= (3, 10):
                        if isinstance(field.type, NewType):
                            field_value = builder.create_call(field.type, [field_value])

                    if field.default != MISSING:
                        field_value = builder.with_default(field_value, field.default)

                    if field.default_factory != MISSING:
                        field_value = builder.with_default(
                            field_value, field.default_factory()
                        )

                    kwargs[field.name] = field_value

            return builder.create_call(type(value), [], kwargs)

    @customize
    def namedtuple_handler(self, value, builder: Builder):
        t = type(value)
        b = t.__bases__
        if len(b) != 1 or b[0] != tuple:
            return
        f = getattr(t, "_fields", None)
        if not isinstance(f, tuple):
            return
        if not all(type(n) == str for n in f):
            return

        return builder.create_call(
            type(value),
            [],
            {
                field: (
                    getattr(value, field)
                    if field not in value._field_defaults
                    else builder.with_default(
                        getattr(value, field), value._field_defaults[field]
                    )
                )
                for field in value._fields
            },
        )

    @customize(tryfirst=True)
    def defaultdict_handler(self, value, builder: Builder):
        if isinstance(value, defaultdict):
            return builder.create_call(
                type(value), [value.default_factory, dict(value)], {}
            )

    @customize
    def unmanaged_handler(self, value, builder: Builder):
        if is_unmanaged(value):
            return CustomUnmanaged(value=value)

    @customize
    def undefined_handler(self, value, builder: Builder):
        if value is undefined:
            return CustomUndefined()

    @customize
    def outsource_handler(self, value, builder: Builder):
        if isinstance(value, Outsourced):
            return builder.create_external(
                value.data, format=value.suffix, storage=value.storage
            )
