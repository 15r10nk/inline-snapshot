from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Any
from typing import Callable

from inline_snapshot._adapter_context import AdapterContext
from inline_snapshot._code_repr import HasRepr
from inline_snapshot._code_repr import mock_repr
from inline_snapshot._code_repr import value_code_repr
from inline_snapshot._compare_context import compare_context
from inline_snapshot._customize._custom_sequence import CustomSequence
from inline_snapshot._exceptions import UsageError
from inline_snapshot._utils import clone

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


class Missing:
    def __repr__(self):
        return "missing"


missing = Missing()


@dataclass
class Builder:
    _snapshot_context: AdapterContext
    _build_new_value: bool = False
    _recursive: bool = True

    def _get_handler_recursive(self, v) -> Custom:
        if self._recursive:
            return self._get_handler(v)
        else:
            return v

    def _get_value(self, value):
        if isinstance(value, Custom):
            return value._eval()
        return value

    def _get_handler(self, v, snapshot_value=None) -> Custom:

        from inline_snapshot._global_state import state

        if isinstance(v, Custom):
            original_value = v._eval()
        else:
            try:
                original_value = clone(v)
            except UsageError:
                original_value = v

        result = v

        while not isinstance(result, Custom):
            with compare_context():
                r = state().pm.hook.customize(
                    value=result,
                    builder=self,
                    local_vars=self._local_vars,
                    global_vars=self._global_vars,
                    snapshot_value=snapshot_value,
                )
            if r is None:

                with mock_repr(self._snapshot_context):
                    repr_str = value_code_repr(result)

                try:
                    ast.parse(repr_str)
                except SyntaxError:
                    result = self.create_call(HasRepr, [type(result), repr_str])
                    # self.repr_str = HasRepr(type(value), self.repr_str).__repr__()
                    # self._imports.append(ImportFrom("inline_snapshot", "HasRepr"))
                else:
                    result = CustomCode(result, repr_str)
            else:
                result = r

        result.__dict__["original_value"] = original_value

        if not isinstance(v, Custom) and self._build_new_value:
            is_same = False
            v_eval = result._eval()

            if (
                hasattr(v, "__pydantic_generic_metadata__")
                and v.__pydantic_generic_metadata__["origin"] == v_eval
            ):
                is_same = True

            if not is_same and v_eval == original_value:
                is_same = True

            if not is_same:
                raise UsageError(f"""\
Customized value does not match original value:

original_value={original_value!r}

customized_value={result._eval()!r}
customized_representation={result!r}
""")

        return result

    def _customize(self, value, snapshot_value=missing):
        return self._get_handler(value, snapshot_value)

    def _customize_all(self, value):
        if not isinstance(value, Custom):
            value = self._customize(value)

        def with_original(new_value: Custom, old_value: Custom) -> Custom:
            new_value.__dict__["original_value"] = getattr(
                old_value, "original_value", old_value._eval()
            )
            return new_value

        if isinstance(value, CustomSequence):
            return with_original(
                type(value)([self._customize_all(c) for c in value.value]), value
            )
        elif isinstance(value, CustomDict):
            return with_original(
                CustomDict(
                    {
                        self._customize_all(k): self._customize_all(v)
                        for k, v in value.value.items()
                    }
                ),
                value,
            )
        elif isinstance(value, CustomCall):
            return with_original(
                CustomCall(
                    function=self._customize_all(value.function),
                    args=[self._customize_all(c) for c in value.args],
                    kwargs={k: self._customize_all(v) for k, v in value.kwargs.items()},
                ),
                value,
            )
        elif isinstance(value, CustomDefault):
            return with_original(CustomDefault(self._customize_all(value.value)), value)

        return value

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
        custom = [self._get_handler_recursive(v) for v in value]
        return CustomList(value=custom)

    def create_tuple(self, value: tuple) -> Custom:
        """
        Creates an intermediate node for a tuple-expression which can be used as a result for your customization function.

        `create_tuple((1, 2, 3))` becomes `(1, 2, 3)` in the code.
        Tuple elements don't have to be Custom nodes and are converted by inline-snapshot if needed.
        """
        custom = [self._get_handler_recursive(v) for v in value]
        return CustomTuple(value=custom)

    def with_default(self, value: Any, default: Any):
        """
        Creates an intermediate node for a default value which can be used as an argument for create_call.

        Arguments are not included in the generated code when they match the actual default.
        The value doesn't have to be a Custom node and is converted by inline-snapshot if needed.
        """
        if isinstance(default, Custom):
            raise UsageError("default value cannot be a Custom value")

        if self._get_value(value) == default:
            return CustomDefault(value=self._get_handler_recursive(value))
        return value

    def create_call(
        self, function: Custom | Callable, posonly_args=[], kwargs={}
    ) -> Custom:
        """
        Creates an intermediate node for a function call expression which can be used as a result for your customization function.

        `create_call(MyClass, [arg1, arg2], {'key': value})` becomes `MyClass(arg1, arg2, key=value)` in the code.
        Function, arguments, and keyword arguments don't have to be Custom nodes and are converted by inline-snapshot if needed.
        """
        function = self._get_handler_recursive(function)
        posonly_args = [self._get_handler_recursive(arg) for arg in posonly_args]
        kwargs = {k: self._get_handler_recursive(arg) for k, arg in kwargs.items()}

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
        custom = {
            self._get_handler_recursive(k): self._get_handler_recursive(v)
            for k, v in value.items()
        }
        assert len(value) == len(custom)

        return CustomDict(value=custom)

    @property
    def _local_vars(self):
        """Get local vars from snapshot context."""
        return self._snapshot_context.local_vars

    @property
    def _global_vars(self):
        """Get global vars from snapshot context."""
        return self._snapshot_context.global_vars

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
            if code in self._local_vars:
                return CustomCode(self._local_vars[code], code, imports)

            # Build import vars only if needed
            import_vars = self._build_import_vars(imports)
            if code in import_vars:
                return CustomCode(import_vars[code], code, imports)

            if code in self._global_vars:
                return CustomCode(self._global_vars[code], code, imports)

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
                **self._global_vars,
                **import_vars,
                **self._local_vars,
            }
            return CustomCode(eval(code, eval_context), code, imports)
