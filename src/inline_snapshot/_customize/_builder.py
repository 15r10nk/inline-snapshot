from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Callable

from inline_snapshot._adapter_context import AdapterContext
from inline_snapshot._compare_context import compare_context
from inline_snapshot._exceptions import UsageError

from ._custom import Custom
from ._custom_call import CustomCall
from ._custom_call import CustomDefault
from ._custom_code import CustomCode
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

        if (
            self._snapshot_context is not None
            and (frame := self._snapshot_context.frame) is not None
        ):
            local_vars = {
                var_name: var_value
                for var_name, var_value in frame.locals.items()
                if "@" not in var_name
            }
            global_vars = {
                var_name: var_value
                for var_name, var_value in frame.globals.items()
                if "@" not in var_name
            }
        else:
            local_vars = {}
            global_vars = {}

        result = v

        while not isinstance(result, Custom):
            with compare_context():
                r = state().pm.hook.customize(
                    value=result,
                    builder=self,
                    local_vars=local_vars,
                    global_vars=global_vars,
                )
            if r is None:
                result = CustomCode(result)
            else:
                result = r

        result.__dict__["original_value"] = v
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
        self, function: Custom | Callable, posonly_args=[], kwargs={}, kwonly_args={}
    ) -> Custom:
        """
        Creates an intermediate node for a function call expression which can be used as a result for your customization function.

        `create_call(MyClass, [arg1, arg2], {'key': value})` becomes `MyClass(arg1, arg2, key=value)` in the code.
        Function, arguments, and keyword arguments don't have to be Custom nodes and are converted by inline-snapshot if needed.
        """
        function = self._get_handler(function)
        posonly_args = [self._get_handler(arg) for arg in posonly_args]
        kwargs = {k: self._get_handler(arg) for k, arg in kwargs.items()}
        kwonly_args = {k: self._get_handler(arg) for k, arg in kwonly_args.items()}

        return CustomCall(
            _function=function,
            _args=posonly_args,
            _kwargs=kwargs,
            _kwonly=kwonly_args,
        )

    def create_dict(self, value: dict) -> Custom:
        """
        Creates an intermediate node for a dict-expression which can be used as a result for your customization function.

        `create_dict({'key': 'value'})` becomes `{'key': 'value'}` in the code.
        Dict keys and values don't have to be Custom nodes and are converted by inline-snapshot if needed.
        """
        custom = {self._get_handler(k): self._get_handler(v) for k, v in value.items()}
        return CustomDict(value=custom)

    def create_code(self, value: Any, repr: str | None = None) -> CustomCode:
        """
        Creates an intermediate node for a value with a custom representation which can be used as a result for your customization function.

        `create_code(value, '{value-1!r}+1')` becomes `4+1` in the code for a given `value=5`.
        Use this when you need to control the exact string representation of a value.

        You can use [`.with_import(module,name)`][inline_snapshot.plugin.CustomCode.with_import] to create an import in the code.
        """
        return CustomCode(value, repr)
