import datetime

import dirty_equals
from dirty_equals._utils import Omit

from inline_snapshot._core._customize._builder import Builder
from inline_snapshot._core._customize._custom_code import ImportFrom
from inline_snapshot._core._unmanaged import is_dirty_equal
from inline_snapshot._core.plugin._spec import customize


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
                kwargs = {k: a for k, a in value._repr_kwargs.items() if a is not Omit}
                if type(value) == dirty_equals.IsNow:
                    kwargs.pop("approx")
                    if (
                        isinstance(delta := kwargs["delta"], datetime.timedelta)
                        and delta.total_seconds() == 2
                    ):
                        kwargs.pop("delta")
                return builder.create_call(type(value), args, kwargs)

    @customize(tryfirst=True)
    def is_now_handler(self, value, builder: Builder):
        if value == dirty_equals.IsNow():
            return dirty_equals.IsNow()
