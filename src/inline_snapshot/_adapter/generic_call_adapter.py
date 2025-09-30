from __future__ import annotations

import ast
import warnings
from abc import ABC
from collections import defaultdict
from dataclasses import MISSING
from dataclasses import fields
from dataclasses import is_dataclass
from typing import Any

from inline_snapshot._customize import CustomCall
from inline_snapshot._customize import Default
from inline_snapshot._customize import unwrap_default

from .._change import CallArg
from .._change import Delete
from ..syntax_warnings import InlineSnapshotSyntaxWarning
from .adapter import Adapter
from .adapter import Item


def get_adapter_for_type(value_type):
    subclasses = GenericCallAdapter.__subclasses__()
    options = [cls for cls in subclasses if cls.check_type(value_type)]

    if not options:
        return

    assert len(options) == 1
    return options[0]


class GenericCallAdapter(Adapter):

    @classmethod
    def check_type(cls, value_type) -> bool:
        raise NotImplementedError(cls)

    @classmethod
    def arguments(cls, value) -> CustomCall:
        raise NotImplementedError(cls)

    @classmethod
    def argument(cls, value, pos_or_name) -> Any:
        return cls.arguments(value).argument(pos_or_name)

    @classmethod
    def repr(cls, value):

        call = cls.arguments(value)

        arguments = [repr(value) for value in call.args] + [
            f"{key}={repr(value)}"
            for key, value in call.kwargs.items()
            if not isinstance(value, Default)
        ]

        return f"{repr(type(value))}({', '.join(arguments)})"

    @classmethod
    def map(cls, value, map_function):
        return cls.arguments(value).map(map_function)

    @classmethod
    def items(cls, value, node):

        args = cls.arguments(value)
        new_args = args.args
        new_kwargs = args.kwargs

        if node is not None:
            assert isinstance(node, ast.Call)
            assert all(kw.arg for kw in node.keywords)
            kw_arg_node = {kw.arg: kw.value for kw in node.keywords if kw.arg}.get

            def pos_arg_node(pos):
                return node.args[pos]

        else:

            def kw_arg_node(_):
                return None

            def pos_arg_node(_):
                return None

        return [
            Item(value=unwrap_default(arg), node=pos_arg_node(i))
            for i, arg in enumerate(new_args)
        ] + [
            Item(value=unwrap_default(kw), node=kw_arg_node(name))
            for name, kw in new_kwargs.items()
        ]

    def assign(self, old_value, old_node, new_value):
        if old_node is None or not isinstance(old_node, ast.Call):
            result = yield from self.value_assign(old_value, old_node, new_value)
            return result

        call_type = self.context.eval(old_node.func)

        if not (isinstance(call_type, type) and self.check_type(call_type)):
            result = yield from self.value_assign(old_value, old_node, new_value)
            return result

        # positional arguments
        for pos_arg in old_node.args:
            if isinstance(pos_arg, ast.Starred):
                warnings.warn_explicit(
                    "star-expressions are not supported inside snapshots",
                    filename=self.context.file._source.filename,
                    lineno=pos_arg.lineno,
                    category=InlineSnapshotSyntaxWarning,
                )
                return old_value

        # keyword arguments
        for kw in old_node.keywords:
            if kw.arg is None:
                warnings.warn_explicit(
                    "star-expressions are not supported inside snapshots",
                    filename=self.context.file._source.filename,
                    lineno=kw.value.lineno,
                    category=InlineSnapshotSyntaxWarning,
                )
                return old_value

        call = self.arguments(new_value)
        new_args = call.args
        new_kwargs = call.kwargs

        # positional arguments

        result_args = []

        for i, (new_value_element, node) in enumerate(zip(new_args, old_node.args)):
            old_value_element = self.argument(old_value, i)
            result = yield from self.get_adapter(
                old_value_element, unwrap_default(new_value_element)
            ).assign(old_value_element, node, unwrap_default(new_value_element))
            result_args.append(result)

        if len(old_node.args) > len(new_args):
            for arg_pos, node in list(enumerate(old_node.args))[len(new_args) :]:
                yield Delete(
                    "fix",
                    self.context.file._source,
                    node,
                    self.argument(old_value, arg_pos),
                )

        if len(old_node.args) < len(new_args):
            for insert_pos, value in list(enumerate(new_args))[len(old_node.args) :]:
                yield CallArg(
                    flag="fix",
                    file=self.context.file._source,
                    node=old_node,
                    arg_pos=insert_pos,
                    arg_name=None,
                    new_code=self.context.file._value_to_code(unwrap_default(value)),
                    new_value=value,
                )

        # keyword arguments
        result_kwargs = {}
        for kw in old_node.keywords:
            if kw.arg not in new_kwargs or isinstance(new_kwargs[kw.arg], Default):
                # delete entries
                yield Delete(
                    (
                        "update"
                        if self.argument(old_value, kw.arg)
                        == self.argument(new_value, kw.arg)
                        else "fix"
                    ),
                    self.context.file._source,
                    kw.value,
                    self.argument(old_value, kw.arg),
                )

        old_node_kwargs = {kw.arg: kw.value for kw in old_node.keywords}

        to_insert = []
        insert_pos = 0
        for key, new_value_element in new_kwargs.items():
            if isinstance(new_value_element, Default):
                continue
            if key not in old_node_kwargs:
                # add new values
                to_insert.append((key, new_value_element))
                result_kwargs[key] = new_value_element
            else:
                node = old_node_kwargs[key]

                # check values with same keys
                old_value_element = self.argument(old_value, key)
                result_kwargs[key] = yield from self.get_adapter(
                    old_value_element, new_value_element
                ).assign(old_value_element, node, new_value_element)

                if to_insert:
                    for key, value in to_insert:

                        yield CallArg(
                            flag="fix",
                            file=self.context.file._source,
                            node=old_node,
                            arg_pos=insert_pos,
                            arg_name=key,
                            new_code=self.context.file._value_to_code(value),
                            new_value=value,
                        )
                    to_insert = []

                insert_pos += 1

        if to_insert:

            for key, value in to_insert:

                yield CallArg(
                    flag="fix",
                    file=self.context.file._source,
                    node=old_node,
                    arg_pos=insert_pos,
                    arg_name=key,
                    new_code=self.context.file._value_to_code(value),
                    new_value=value,
                )
        return type(old_value)(*result_args, **result_kwargs)


class DataclassAdapter(GenericCallAdapter):

    @classmethod
    def check_type(cls, value):
        return is_dataclass(value)

    @classmethod
    def arguments(cls, value):

        kwargs = {}

        for field in fields(value):  # type: ignore
            if field.repr:
                field_value = getattr(value, field.name)
                is_default = False

                if field.default != MISSING and field.default == field_value:
                    is_default = True

                if (
                    field.default_factory != MISSING
                    and field.default_factory() == field_value
                ):
                    is_default = True

                if is_default:
                    field_value = Default(field_value)
                kwargs[field.name] = field_value

        return CustomCall(type(value), *[], **kwargs)


try:
    import attrs
except ImportError:  # pragma: no cover
    pass
else:

    class AttrAdapter(GenericCallAdapter):

        @classmethod
        def check_type(cls, value):
            return attrs.has(value)

        @classmethod
        def arguments(cls, value):

            kwargs = {}

            for field in attrs.fields(type(value)):
                if field.repr:
                    field_value = getattr(value, field.name)
                    is_default = False

                    if field.default is not attrs.NOTHING:

                        default_value = (
                            field.default
                            if not isinstance(field.default, attrs.Factory)
                            else (
                                field.default.factory()
                                if not field.default.takes_self
                                else field.default.factory(value)
                            )
                        )

                        if default_value == field_value:
                            is_default = True

                    if is_default:
                        field_value = Default(field_value)

                    kwargs[field.name] = field_value

            return CustomCall(type(value), **kwargs)


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

    class PydanticContainer(GenericCallAdapter):

        @classmethod
        def check_type(cls, value):
            return issubclass(value, BaseModel)

        @classmethod
        def arguments(cls, value):

            kwargs = {}

            for name, field in get_fields(value).items():  # type: ignore
                if getattr(field, "repr", True):
                    field_value = getattr(value, name)
                    is_default = False

                    if (
                        field.default is not PydanticUndefined
                        and field.default == field_value
                    ):
                        is_default = True

                    if (
                        field.default_factory is not None
                        and field.default_factory() == field_value
                    ):
                        is_default = True

                    if is_default:
                        field_value = Default(field_value)

                    kwargs[name] = field_value

            return CustomCall(type(value), **kwargs)


class IsNamedTuple(ABC):
    _inline_snapshot_name = "namedtuple"

    _fields: tuple
    _field_defaults: dict

    @classmethod
    def __subclasshook__(cls, t):
        b = t.__bases__
        if len(b) != 1 or b[0] != tuple:
            return False
        f = getattr(t, "_fields", None)
        if not isinstance(f, tuple):
            return False
        return all(type(n) == str for n in f)


class NamedTupleAdapter(GenericCallAdapter):

    @classmethod
    def check_type(cls, value):
        return issubclass(value, IsNamedTuple)

    @classmethod
    def arguments(cls, value: IsNamedTuple):

        return CustomCall(
            type(value),
            **{
                field: getattr(value, field)
                for field in value._fields
                if field not in value._field_defaults
                or getattr(value, field) != value._field_defaults[field]
            },
        )


class DefaultDictAdapter(GenericCallAdapter):
    @classmethod
    def check_type(cls, value):
        return issubclass(value, defaultdict)

    @classmethod
    def arguments(cls, value: defaultdict):

        return CustomCall(
            type(value),
            *[value.default_factory, dict(value)],
        )
