from functools import partial
from typing import Any
from typing import List

import pluggy

from inline_snapshot._customize._builder import Builder
from inline_snapshot.plugin._context_value import ContextValue

hookspec = pluggy.HookspecMarker("inline_snapshot")
hookimpl = pluggy.HookimplMarker("inline_snapshot")

customize = partial(hookimpl, specname="customize")
"""
    Registers a function as a customization hook inside inline-snapshot.

    Customization hooks allow you to control how objects are represented in snapshot code.
    When inline-snapshot generates code for a value, it calls each registered customization
    function in reverse order of registration until one returns a Custom object.

    **Important**: Customization handlers should be registered in your `conftest.py` file to ensure
    they are loaded before your tests run.


    Example:
        Basic usage with a custom class:
        <!-- inline-snapshot-lib: myclass.py -->
        ``` python
        class MyClass:
            def __init__(self, arg1, arg2, key=None):
                self.arg1 = arg1
                self.arg2 = arg2
                self.key_attr = key
        ```

        <!-- inline-snapshot-lib: conftest.py -->
        ``` python
        from myclass import MyClass
        from inline_snapshot import customize


        @customize
        def my_custom_handler(value, builder):
            if isinstance(value, MyClass):
                # Generate code like: MyClass(arg1, arg2, key=value)
                return builder.create_call(
                    MyClass, [value.arg1, value.arg2], {"key": value.key_attr}
                )
            return None  # Let other handlers process this value
        ```

        <!-- inline-snapshot: create fix first_block outcome-failed=1 outcome-errors=1 -->
        ``` python
        from inline_snapshot import snapshot
        from myclass import MyClass


        def test_myclass():
            obj = MyClass(42, "hello", key="world")
            assert obj == snapshot(MyClass(42, "hello", key="world"))
        ```

    Note:
        - **Always register handlers in `conftest.py`** to ensure they're available for all tests
        - If no handler returns a Custom object, a default representation is used
        - Use builder methods (`create_call`, `create_external`) to construct representations
        - Always return `None` if your handler doesn't apply to the given value type
        - The builder automatically handles recursive conversion of nested values, therfor `create_list` and `create_dict` are unlikely needed because you can just use `[]` or `{}`


    See Also:
        - [Builder][inline_snapshot._customize.Builder]: Available builder methods
        - [Custom][inline_snapshot._customize.Custom]: Base class for custom representations
    """


class InlineSnapshotPluginSpec:
    @hookspec(firstresult=True)
    def customize(
        self,
        value: Any,
        builder: Builder,
        local_vars: List[ContextValue],
        global_vars: List[ContextValue],
        snapshot_value: Any,
    ) -> Any: ...

    # @hookspec
    # def format_code(self, filename, str) -> str: ...
