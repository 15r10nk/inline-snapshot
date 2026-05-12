import sys
from typing import NewType

from pydantic import BaseModel

from inline_snapshot._core._customize._builder import Builder
from inline_snapshot._core.plugin._spec import customize
from inline_snapshot.matcher import IsPydantic
from inline_snapshot.pydantic_compatibility import PydanticUndefined
from inline_snapshot.pydantic_compatibility import get_fields


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

            cls = type(value)
            if hasattr(cls, "__pydantic_generic_metadata__"):
                origin = cls.__pydantic_generic_metadata__.get("origin")
                if origin is not None:
                    cls = origin

            return builder.create_call(
                builder.create_subscript(IsPydantic, cls), [], kwargs
            )
