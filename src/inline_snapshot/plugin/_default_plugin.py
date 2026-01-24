import ast
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
from types import FunctionType
from typing import Any
from typing import Dict

from inline_snapshot._customize._builder import Builder
from inline_snapshot._customize._custom_code import ImportFrom
from inline_snapshot._customize._custom_undefined import CustomUndefined
from inline_snapshot._customize._custom_unmanaged import CustomUnmanaged
from inline_snapshot._external._outsource import Outsourced
from inline_snapshot._sentinels import undefined
from inline_snapshot._unmanaged import is_dirty_equal
from inline_snapshot._unmanaged import is_unmanaged
from inline_snapshot._utils import triple_quote

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
            for name, local_value in local_vars.items():
                if local_value is value:
                    return builder.create_code(name)

            qualname = value.__qualname__.split("[")[0]
            name = qualname.split(".")[0]
            return builder.create_code(
                qualname, imports=[ImportFrom(value.__module__, name)]
            )

    @customize
    def builtin_function_handler(self, value, builder: Builder):
        if isinstance(value, BuiltinFunctionType):
            return builder.create_code(value.__name__)

    @customize
    def path_handler(self, value, builder: Builder):
        if isinstance(value, Path):
            return builder.create_call(Path, [value.as_posix()])

        if isinstance(value, PurePath):
            return builder.create_call(PurePath, [value.as_posix()])

    def sort_set_values(self, set_values):
        is_sorted = False
        try:
            set_values = sorted(set_values)
            is_sorted = True
        except TypeError:
            pass

        set_values = list(map(repr, set_values))
        if not is_sorted:
            set_values = sorted(set_values)

        return set_values

    @customize
    def set_handler(self, value, builder: Builder):
        if isinstance(value, set):
            if len(value) == 0:
                return builder.create_code("set()")
            else:
                return builder.create_code(
                    "{" + ", ".join(self.sort_set_values(value)) + "}"
                )

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


try:
    pass
except ImportError:  # pragma: no cover

    pass

else:
    import datetime

    from dirty_equals import IsNow
    from dirty_equals._utils import Omit

    class InlineSnapshotDirtyEqualsPlugin:
        @customize(tryfirst=True)
        def dirty_equals_handler(self, value, builder: Builder):

            if is_dirty_equal(value) and builder._build_new_value:

                if isinstance(value, type):
                    return builder.create_code(
                        value.__name__,
                        imports=[ImportFrom("dirty_equals", value.__name__)],
                    )
                else:

                    args = [a for a in value._repr_args if a is not Omit]
                    kwargs = {
                        k: a for k, a in value._repr_kwargs.items() if a is not Omit
                    }
                    if type(value) == IsNow:
                        kwargs.pop("approx")
                        if (
                            isinstance(delta := kwargs["delta"], datetime.timedelta)
                            and delta.total_seconds() == 2
                        ):
                            kwargs.pop("delta")
                    return builder.create_call(type(value), args, kwargs)

        @customize(tryfirst=True)
        def is_now_handler(self, value, builder: Builder):
            if value == IsNow():
                return IsNow()


try:
    import attrs
except ImportError:  # pragma: no cover

    pass

else:

    class InlineSnapshotAttrsPlugin:
        @customize
        def attrs_handler(self, value, builder: Builder):

            if attrs.has(type(value)):

                kwargs = {}

                for field in attrs.fields(type(value)):
                    if field.repr:
                        field_value = getattr(value, field.name)

                        if field.default is not attrs.NOTHING:

                            default_value = (
                                field.default
                                if not isinstance(field.default, attrs.Factory)  # type: ignore
                                else (
                                    field.default.factory()
                                    if not field.default.takes_self
                                    else field.default.factory(value)
                                )
                            )
                            field_value = builder.with_default(
                                field_value, default_value
                            )

                        kwargs[field.name] = field_value

                return builder.create_call(type(value), [], kwargs)


try:
    import pydantic
except ImportError:  # pragma: no cover

    pass

else:
    # import pydantic
    if pydantic.version.VERSION.startswith("1."):
        # pydantic v1
        from pydantic.fields import Undefined as PydanticUndefined  # type: ignore[attr-defined,no-redef]

        def get_fields(value):
            return value.__fields__

    else:
        # pydantic v2
        from pydantic_core import PydanticUndefined

        def get_fields(value):
            return type(value).model_fields

    from pydantic import BaseModel

    class InlineSnapshotPydanticPlugin:
        @customize
        def pydantic_model_handler(self, value, builder: Builder):

            if isinstance(value, BaseModel):

                kwargs = {}

                for name, field in get_fields(value).items():  # type: ignore
                    if getattr(field, "repr", True):
                        field_value = getattr(value, name)

                        if (
                            field.default is not PydanticUndefined
                            and field.default == field_value
                        ):
                            field_value = builder.with_default(
                                field_value, field.default
                            )

                        elif field.default_factory is not None:
                            field_value = builder.with_default(
                                field_value, field.default_factory()
                            )

                        kwargs[name] = field_value

                return builder.create_call(type(value), [], kwargs)
