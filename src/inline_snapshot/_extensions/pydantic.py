import sys
from typing import NewType

import pydantic

from inline_snapshot._core._customize._builder import Builder
from inline_snapshot._core.plugin._spec import customize

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
