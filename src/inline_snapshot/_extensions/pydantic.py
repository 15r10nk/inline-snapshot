import sys
from typing import NewType

import pydantic

from inline_snapshot._core._customize._builder import Builder
from inline_snapshot._core.plugin._spec import customize

if pydantic.version.VERSION.startswith("1."):
    # pydantic v1
    from pydantic.fields import Undefined as PydanticUndefined  # type: ignore[attr-defined,no-redef]
    from pydantic.generics import _assigned_parameters

    def get_fields(value):
        return value.__fields__

    def get_generic_type(value):
        assigned = _assigned_parameters.get(value)
        if assigned is not None:
            # GenericModel creates each specialization with its source class
            # as the first base, and records the corresponding substitutions.
            origin = value.__bases__[0]
            return origin, tuple(assigned[p] for p in origin.__parameters__)

else:
    # pydantic v2
    from pydantic_core import PydanticUndefined

    def get_fields(value):
        return type(value).model_fields

    def get_generic_type(value):
        metadata = getattr(value, "__pydantic_generic_metadata__", None)
        if metadata is not None and metadata["origin"] is not None:
            return metadata["origin"], metadata["args"]


from pydantic import BaseModel


class InlineSnapshotPydanticPlugin:
    @customize
    def pydantic_generic_type_handler(self, value, builder: Builder, local_vars):
        if isinstance(value, type) and issubclass(value, BaseModel):
            generic_type = get_generic_type(value)
            if generic_type is not None:
                for name, local_value in local_vars.items():
                    if local_value is value:
                        return builder.create_code(name)

                origin, args = generic_type
                index = args[0] if len(args) == 1 else builder.create_tuple(args)
                return builder.create_subscript(origin, index)

    @customize
    def pydantic_model_handler(self, value, builder: Builder):

        if isinstance(value, BaseModel):

            kwargs = {}

            for name, field in get_fields(value).items():  # type: ignore
                if getattr(field, "repr", True):
                    field_value = getattr(value, name)

                    type_ = field.annotation

                    if sys.version_info >= (3, 10):
                        if isinstance(type_, NewType):
                            field_value = builder.create_call(type_, [field_value])

                    if field.default_factory is not None:
                        field_value = builder.with_default(
                            field_value, field.default_factory()
                        )
                    elif field.default is not PydanticUndefined:
                        field_value = builder.with_default(field_value, field.default)

                    kwargs[name] = field_value

            return builder.create_call(type(value), [], kwargs)
