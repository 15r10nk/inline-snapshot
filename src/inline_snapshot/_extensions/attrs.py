import sys
from typing import NewType

import attrs

from inline_snapshot._core._customize._builder import Builder
from inline_snapshot._core.plugin._spec import customize


class InlineSnapshotAttrsPlugin:
    @customize
    def attrs_handler(self, value, builder: Builder):

        if attrs.has(type(value)):

            kwargs = {}

            for field in attrs.fields(type(value)):
                if field.repr:
                    field_value = getattr(value, field.name)

                    if sys.version_info >= (3, 10):
                        if isinstance(field.type, NewType):
                            field_value = builder.create_call(field.type, [field_value])

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
                        field_value = builder.with_default(field_value, default_value)

                    kwargs[field.name] = field_value

            return builder.create_call(type(value), [], kwargs)
