from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import Any
from typing import Callable

from inline_snapshot._adapter_context import AdapterContext
from inline_snapshot._sentinels import undefined

missing = undefined
from inline_snapshot._compare_context import compare_context
from inline_snapshot._exceptions import UsageError

from ._custom import Custom
from ._custom_call import CustomCall
from ._custom_call import CustomDefault
from ._custom_code import CustomCode
from ._custom_code import Import
from ._custom_code import ImportFrom
from ._custom_dict import CustomDict
from ._custom_external import CustomExternal
from ._custom_sequence import CustomList
from ._custom_sequence import CustomTuple


@dataclass
class Builder:
    _snapshot_context: AdapterContext
    _build_new_value: bool = False

    def _get_handler(self, v) -> Custom:

        from inline_snapshot._global_state import state

        result = v

        while not isinstance(result, Custom):
            with compare_context():
                r = state().pm.hook.customize(
                    value=result,
                    builder=self,
                    local_vars=self._get_local_vars,
                    global_vars=self._get_global_vars,
                )
            if r is None:
                result = CustomCode(result)
            else:
                result = r

        result.__dict__["original_value"] = v

        if not isinstance(v, Custom) and self._build_new_value:
            if result._eval() != v:
                raise UsageError(
                    f"""\
Customized value does not match original value:

original_value={v!r}

customized_value={result._eval()!r}
customized_representation={result!r}
"""
                )

        return result

    def create_external(
        self, value: Any, format: str | None = None, storage: str | None = None
    ):
        """
        Creates a new `external()` with the given format and storage.
        """

        return CustomExternal(value, format=format, storage=storage)

    def create_list(self, value: list) -> Custom:
        """
        Creates an intermediate node for a list-expression which can be used as a result for your customization function.

        `create_list([1,2,3])` becomes `[1,2,3]` in the code.
        List elements don't have to be Custom nodes and are converted by inline-snapshot if needed.
        """
        custom = [self._get_handler(v) for v in value]
        return CustomList(value=custom)

    def create_tuple(self, value: tuple) -> Custom:
        """
        Creates an intermediate node for a tuple-expression which can be used as a result for your customization function.

        `create_tuple((1, 2, 3))` becomes `(1, 2, 3)` in the code.
        Tuple elements don't have to be Custom nodes and are converted by inline-snapshot if needed.
        """
        custom = [self._get_handler(v) for v in value]
        return CustomTuple(value=custom)

    def with_default(self, value: Any, default: Any):
        """
        Creates an intermediate node for a default value which can be used as an argument for create_call.

        Arguments are not included in the generated code when they match the actual default.
        The value doesn't have to be a Custom node and is converted by inline-snapshot if needed.
        """
        if isinstance(default, Custom):
            raise UsageError("default value can not be an Custom value")

        if value == default:
            return CustomDefault(value=self._get_handler(value))
        return value

    def create_call(
        self, function: Custom | Callable, posonly_args=[], kwargs={}
    ) -> Custom:
        """
        Creates an intermediate node for a function call expression which can be used as a result for your customization function.

        `create_call(MyClass, [arg1, arg2], {'key': value})` becomes `MyClass(arg1, arg2, key=value)` in the code.
        Function, arguments, and keyword arguments don't have to be Custom nodes and are converted by inline-snapshot if needed.
        """
        function = self._get_handler(function)
        posonly_args = [self._get_handler(arg) for arg in posonly_args]
        kwargs = {k: self._get_handler(arg) for k, arg in kwargs.items()}

        return CustomCall(
            function=function,
            args=posonly_args,
            kwargs=kwargs,
        )

    def create_dict(self, value: dict) -> Custom:
        """
        Creates an intermediate node for a dict-expression which can be used as a result for your customization function.

        `create_dict({'key': 'value'})` becomes `{'key': 'value'}` in the code.
        Dict keys and values don't have to be Custom nodes and are converted by inline-snapshot if needed.
        """
        custom = {self._get_handler(k): self._get_handler(v) for k, v in value.items()}
        return CustomDict(value=custom)

    @cached_property
    def _get_local_vars(self):
        """Get local vars from snapshot context."""
        if (
            self._snapshot_context is not None
            and (frame := self._snapshot_context.frame) is not None
        ):
            return {
                var_name: var_value
                for var_name, var_value in frame.locals.items()
                if "@" not in var_name
            }
        return {}

    @cached_property
    def _get_global_vars(self):
        """Get global vars from snapshot context."""
        if (
            self._snapshot_context is not None
            and (frame := self._snapshot_context.frame) is not None
        ):
            return {
                var_name: var_value
                for var_name, var_value in frame.globals.items()
                if "@" not in var_name
            }
        return {}

    def _build_import_vars(self, imports):
        """Build import vars from imports parameter."""
        import_vars = {}
        if imports:
            import importlib

            for imp in imports:
                if isinstance(imp, Import):
                    # import module - makes top-level package available
                    importlib.import_module(imp.module)
                    top_level = imp.module.split(".")[0]
                    import_vars[top_level] = importlib.import_module(top_level)
                elif isinstance(imp, ImportFrom):
                    # from module import name
                    module = importlib.import_module(imp.module)
                    import_vars[imp.name] = getattr(module, imp.name)
                else:
                    assert False
        return import_vars

    def create_code(
        self, code: str, *, imports: list[Import | ImportFrom] = []
    ) -> Custom:
        """
        Creates an intermediate node for a value with a custom representation which can be used as a result for your customization function.

        `create_code('{value-1!r}+1')` becomes `4+1` in the code.
        Use this when you need to control the exact string representation of a value.

        Arguments:
            code: Custom string representation to evaluate. This is required and will be evaluated using the snapshot context.
            imports: Optional list of Import and ImportFrom objects to add required imports to the generated code.
                     Example: `imports=[Import("os"), ImportFrom("pathlib", "Path")]`
        """
        import_vars = None

        # Try direct variable lookup for simple identifiers (fastest)
        if code.isidentifier():
            # Direct lookup with proper precedence: local > import > global
            if code in self._get_local_vars:
                return CustomCode(self._get_local_vars[code], code, imports)

            # Build import vars only if needed
            import_vars = self._build_import_vars(imports)
            if code in import_vars:
                return CustomCode(import_vars[code], code, imports)

            if code in self._get_global_vars:
                return CustomCode(self._get_global_vars[code], code, imports)

        # Try ast.literal_eval for simple literals (fast and safe)
        try:
            import ast

            return CustomCode(ast.literal_eval(code), code, imports)
        except (ValueError, SyntaxError):
            # Fall back to eval with context for complex expressions
            # Build evaluation context with proper precedence: global < import < local
            if import_vars is None:
                import_vars = self._build_import_vars(imports)
            eval_context = {
                **self._get_global_vars,
                **import_vars,
                **self._get_local_vars,
            }
            return CustomCode(eval(code, eval_context), code, imports)
