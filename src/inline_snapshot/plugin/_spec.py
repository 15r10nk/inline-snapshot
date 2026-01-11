from functools import partial
from typing import Any
from typing import List

import pluggy

from inline_snapshot._customize._builder import Builder
from inline_snapshot.plugin._context_variable import ContextVariable

inline_snapshot_plugin_name = "inline-snapshot"

hookspec = pluggy.HookspecMarker(inline_snapshot_plugin_name)
"""
The pluggy hookspec marker for inline_snapshot.
"""

hookimpl = pluggy.HookimplMarker(inline_snapshot_plugin_name)
"""
The pluggy hookimpl marker for inline_snapshot.
"""

customize = partial(hookimpl, specname="customize")
"""
Decorator to mark a function as an implementation of the `customize` hook which can be used instead of `hookimpl(specname="customize")`.
"""


class InlineSnapshotPluginSpec:
    @hookspec(firstresult=True)
    def customize(
        self,
        value: Any,
        builder: Builder,
        local_vars: List[ContextVariable],
        global_vars: List[ContextVariable],
    ) -> Any:
        """
        The customize hook is called every time a snapshot value should be converted into code.

        This hook allows you to control how inline-snapshot represents objects in generated code.
        When multiple handlers are registered, they are called until one returns a non-None value.
        `customize` is also called for each attribute of the converted hook which is not a Custom node, which means that a hook for `int` does not only apply for `snapshot(5)` but also for `snaspshot([1,2,3])` 3 times.

        Arguments:
            value: The Python object that needs to be converted into source code representation.
                   This is the actual runtime value from your test.
            builder: A Builder instance providing methods to construct custom code representations.
                    Use methods like `create_call()`, `create_dict()`, `create_external()`, etc.
            local_vars: List of local variables available in the current scope, each containing
                       `name` and `value` attributes. Useful for referencing existing variables
                       instead of creating new literals.
            global_vars: List of global variables available in the current scope, each containing
                        `name` and `value` attributes.

        Returns:
            (Custom): created using [Builder][inline_snapshot.plugin.Builder] `create_*` methods.
            (None): if this handler doesn't apply to the given value.
            (Something else): when the next handler should process the value.

        Example:
            You can use @customize when you want to specify multiple handlers in the same class:


            === "with @customize"
                <!-- inline-snapshot-lib: conftest.py -->
                ``` python title="conftest.py"
                from inline_snapshot.plugin import customize


                class InlineSnapshotPlugin:
                    @customize
                    def binary_numbers(self, value, builder, local_vars, global_vars):
                        if isinstance(value, int):
                            return builder.create_code(value, bin(value))

                    @customize
                    def repeated_strings(self, value, builder):
                        if isinstance(value, str) and value == value[0] * len(value):
                            return builder.create_code(value, f"'{value[0]}'*{len(value)}")
                ```

            === "by method name"

                <!-- inline-snapshot-lib: conftest.py -->
                ``` python title="conftest.py"
                class InlineSnapshotPlugin:
                    def customize(self, value, builder, local_vars, global_vars):
                        if isinstance(value, int):
                            return builder.create_code(value, bin(value))

                        if isinstance(value, str) and value == value[0] * len(value):
                            return builder.create_code(value, f"'{value[0]}'*{len(value)}")
                ```


            <!-- inline-snapshot: create fix first_block outcome-passed=1 -->
            ``` python title="test_customizations.py"
            from inline_snapshot import snapshot


            def test_customizations():
                assert ["aaaaaaaaaaaaaaa", "bbbbbb"] == snapshot(["a" * 15, "b" * 6])
                assert 18856 == snapshot(0b100100110101000)
            ```



        """

    # @hookspec
    # def format_code(self, filename, str) -> str: ...
