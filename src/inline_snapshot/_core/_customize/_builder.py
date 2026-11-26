from __future__ import annotations

import ast
import importlib
import keyword
from dataclasses import dataclass
from types import ModuleType
from typing import Any
from typing import Callable
from typing import Literal

from inline_snapshot._core._code_repr import HasRepr
from inline_snapshot._core._code_repr import mock_repr
from inline_snapshot._core._code_repr import value_code_repr
from inline_snapshot._core._compare_context import compare_context
from inline_snapshot._core._customize._custom_sequence import CustomSequence
from inline_snapshot._core._customize._custom_unmanaged import CustomUnmanaged
from inline_snapshot._core._customize._uncustomized import Uncustomized
from inline_snapshot._core._exceptions import UsageError
from inline_snapshot._core._snapshot_context import SnapshotContext

from ._custom import Custom
from ._custom_call import CustomCall
from ._custom_call import CustomDefault
from ._custom_code import CustomCode
from ._custom_code import Import
from ._custom_code import ImportFrom
from ._custom_dict import CustomDict
from ._custom_external import CustomExternal
from ._custom_sequence import CustomList
from ._custom_sequence import CustomSet
from ._custom_sequence import CustomTuple
from ._custom_undefined import CustomUndefined


@dataclass
class Builder:
    _snapshot_context: SnapshotContext
    _build_new_value: bool = False

    def _convert_child(self, v) -> Custom:
        if isinstance(v, Custom):
            return v
        return Uncustomized(v)

    def _get_value(self, value):
        if isinstance(value, Custom):
            return value._eval()
        return value

    def _customize(self, v, snapshot_value: Custom) -> Custom:
        from inline_snapshot._core._global_state import state

        assert not isinstance(v, Custom)

        result = v

        while not isinstance(result, Custom):
            with compare_context():
                r = state().pm.hook.customize(
                    value=result,
                    builder=self,
                    local_vars=self._local_vars,
                    global_vars=self._global_vars,
                    snapshot_value=snapshot_value._eval(),
                )

            if r is None:

                with mock_repr(self._snapshot_context):
                    repr_str = value_code_repr(result)

                try:
                    ast.parse(repr_str)
                except SyntaxError:
                    result = self.create_call(HasRepr, [type(result), repr_str])
                else:
                    result = CustomCode(result, repr_str)
            else:
                result = r

        if self._build_new_value:
            is_same = False
            v_eval = result._eval()
            assert not isinstance(v_eval, Custom)

            if (
                hasattr(v, "__pydantic_generic_metadata__")
                and v.__pydantic_generic_metadata__["origin"] == v_eval
            ):
                is_same = True

            if not is_same and v_eval == v:
                is_same = True

            if not is_same:
                raise UsageError(f"""\
Customized value does not match original value:

original_value={v!r}

customized_value={result._eval()!r}
customized_representation={result!r}
""")

        return result

    def _customize_all(self, value):
        if isinstance(value, Uncustomized):
            value = self._customize(value._value, CustomUndefined())
        elif not isinstance(value, Custom):
            value = self._customize(value, CustomUndefined())

        if isinstance(value, CustomSequence):
            return type(value)([self._customize_all(child) for child in value.value])
        elif isinstance(value, CustomDict):
            return CustomDict(
                {
                    self._customize_all(k): self._customize_all(v)
                    for k, v in value.value.items()
                }
            )
        elif isinstance(value, CustomCall):
            return CustomCall(
                function=self._customize_all(value.function),
                args=[self._customize_all(c) for c in value.args],
                kwargs={k: self._customize_all(v) for k, v in value.kwargs.items()},
            )
        elif isinstance(value, CustomDefault):
            return CustomDefault(self._customize_all(value.value))
        elif isinstance(
            value, (CustomCode, CustomExternal, CustomUndefined, CustomUnmanaged)
        ):
            return value
        else:
            assert False, f"missing case for {value}"

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
        custom = [self._convert_child(v) for v in value]
        return CustomList(value=custom)

    def create_tuple(self, value: tuple) -> Custom:
        """
        Creates an intermediate node for a tuple-expression which can be used as a result for your customization function.

        `create_tuple((1, 2, 3))` becomes `(1, 2, 3)` in the code.
        Tuple elements don't have to be Custom nodes and are converted by inline-snapshot if needed.
        """
        custom = [self._convert_child(v) for v in value]
        return CustomTuple(value=custom)

    def create_set(self, value: set) -> Custom:
        """
        Creates an intermediate node for a set-expression which can be used as a result for your customization function.

        `create_set({1, 2, 3})` becomes `{1, 2, 3}` in the code.
        Set elements don't have to be Custom nodes and are converted by inline-snapshot if needed.
        """
        custom = [self._convert_child(v) for v in value]
        return CustomSet(value=custom)

    def with_default(self, value: Any, default: Any):
        """
        Creates an intermediate node for a default value which can be used as an argument for create_call.

        Arguments are not included in the generated code when they match the actual default.
        The value doesn't have to be a Custom node and is converted by inline-snapshot if needed.
        """
        if isinstance(default, Custom):
            raise UsageError("default value cannot be a Custom value")

        if self._get_value(value) == default:
            return CustomDefault(value=self._convert_child(value))
        return value

    def create_call(
        self, function: Custom | Callable, posonly_args=[], kwargs={}
    ) -> Custom:
        """
        Creates an intermediate node for a function call expression which can be used as a result for your customization function.

        `create_call(MyClass, [arg1, arg2], {'key': value})` becomes `MyClass(arg1, arg2, key=value)` in the code.
        Function, arguments, and keyword arguments don't have to be Custom nodes and are converted by inline-snapshot if needed.
        """
        function = self._convert_child(function)
        posonly_args = [self._convert_child(arg) for arg in posonly_args]
        kwargs = {k: self._convert_child(arg) for k, arg in kwargs.items()}

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
            self._convert_child(k): self._convert_child(v) for k, v in value.items()
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
                    import_vars[imp.asname or top_level] = importlib.import_module(
                        imp.module if imp.asname else top_level
                    )
                elif isinstance(imp, ImportFrom):
                    # from module import name
                    module = importlib.import_module(imp.module)
                    import_vars[imp.asname or imp.name] = getattr(module, imp.name)
                else:
                    assert False
        return import_vars

    def create_imported_name(
        self,
        module: str,
        name: str,
        *,
        style: Literal["import", "import-from"] | None = None,
        import_as: str | None = None,
    ) -> Custom:
        """Reference a module member, reusing imports visible at the snapshot.

        Existing references such as ``DF`` or ``pd.DataFrame`` are reused when
        neither ``style`` nor ``import_as`` is specified. Otherwise a
        ``from module import name`` statement is added as needed.

        Args:
            module: Absolute module path containing the requested member.
            name: Name of the member to reference.
            style: Enforce ``import module`` or ``from module import name``.
                Specifying a style bypasses automatic reference selection.
            import_as: Enforce an alias for the module with ``style="import"``,
                or for the member otherwise. Defaults to ``import-from`` style.

        Raises:
            UsageError: An option is invalid or the required name is already
                bound to a different value in the snapshot's scope.
        """
        if style not in (None, "import", "import-from"):
            raise UsageError("style must be 'import' or 'import-from'")
        for label, parts in (
            ("module", module.split(".")),
            ("name", [name]),
            ("import_as", [] if import_as is None else [import_as]),
        ):
            if any(
                not part.isidentifier() or keyword.iskeyword(part) for part in parts
            ):
                raise UsageError(f"{label} must be a valid Python name")

        value = getattr(importlib.import_module(module), name)
        namespace = {**self._global_vars, **self._local_vars}
        if style is None and import_as is None:
            missing = object()
            references = {}
            tree = self._snapshot_context.source.tree
            assert tree is not None
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    for alias in node.names:
                        reference = alias.asname or (
                            alias.name.split(".")[0]
                            if isinstance(node, ast.Import)
                            else alias.name
                        )
                        if reference in namespace:
                            candidate = namespace[reference]
                            if isinstance(node, ast.Import) and alias.asname is None:
                                for part in alias.name.split(".")[1:]:
                                    candidate = getattr(candidate, part, missing)
                                reference = alias.name
                            references[reference] = candidate
            for reference, candidate in references.items():
                if candidate is value:
                    return CustomCode(value, reference)

            for reference, candidate in references.items():
                if not isinstance(candidate, ModuleType):
                    continue
                if vars(candidate).get(name, missing) is value:
                    return CustomCode(value, f"{reference}.{name}")
                if module.startswith(candidate.__name__ + "."):
                    suffix = module[len(candidate.__name__) + 1 :] + "." + name
                    member: Any = candidate
                    for part in suffix.split("."):
                        member = getattr(member, part, missing)
                    if member is value:
                        return CustomCode(value, f"{reference}.{suffix}")

        imp: Import | ImportFrom
        if style == "import":
            binding = import_as or module.split(".")[0]
            reference = f"{import_as or module}.{name}"
            binding_value = importlib.import_module(module if import_as else binding)
            imp = Import(module, asname=import_as)
        else:
            binding = import_as or name
            reference = binding
            binding_value = value
            imp = ImportFrom(module, name, asname=import_as)

        if binding in namespace and namespace[binding] is not binding_value:
            raise UsageError(
                f"cannot import {module!r}: {binding!r} is already bound to a different value"
            )
        return CustomCode(value, reference, [imp], _exact_imports=True)

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
