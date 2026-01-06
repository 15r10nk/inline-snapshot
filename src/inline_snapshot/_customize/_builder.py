from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from inline_snapshot._adapter_context import AdapterContext
from inline_snapshot._compare_context import compare_context
from inline_snapshot.plugin._context_value import ContextValue

from ._custom import Custom
from ._custom_call import CustomCall
from ._custom_call import CustomDefault
from ._custom_dict import CustomDict
from ._custom_external import CustomExternal
from ._custom_sequence import CustomList
from ._custom_sequence import CustomTuple
from ._custom_value import CustomValue


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
            local_vars = [
                ContextValue(var_name, var_value)
                for var_name, var_value in frame.locals.items()
                if "@" not in var_name
            ]
            global_vars = [
                ContextValue(var_name, var_value)
                for var_name, var_value in frame.globals.items()
                if "@" not in var_name
            ]
        else:
            local_vars = []
            global_vars = []

        result = v

        snapshot_value = (
            self._snapshot_context.snapshot_value
            if self._snapshot_context is not None
            else None
        )

        while not isinstance(result, Custom):
            with compare_context():
                r = state().pm.hook.customize(
                    value=result,
                    builder=self,
                    local_vars=local_vars,
                    global_vars=global_vars,
                    snapshot_value=snapshot_value,
                )
            if r is None:
                result = CustomValue(result)
            else:
                result = r

        result.__dict__["original_value"] = v
        return result

    def create_external(
        self, value: Any, format: str | None = None, storage: str | None = None
    ):

        return CustomExternal(value, format=format, storage=storage)

    def create_list(self, value) -> Custom:
        """
        Creates an intermediate node for a list-expression which can be used as a result for your customization function.

        `create_list([1,2,3])` becomes `[1,2,3]` in the code.
        List elements are recursively converted into CustomNodes.
        """
        custom = [self._get_handler(v) for v in value]
        return CustomList(value=custom)

    def create_tuple(self, value) -> Custom:
        """
        Creates an intermediate node for a tuple-expression which can be used as a result for your customization function.

        `create_tuple((1, 2, 3))` becomes `(1, 2, 3)` in the code.
        Tuple elements are recursively converted into CustomNodes.
        """
        custom = [self._get_handler(v) for v in value]
        return CustomTuple(value=custom)

    def create_call(
        self, function, posonly_args=[], kwargs={}, kwonly_args={}
    ) -> Custom:
        """
        Creates an intermediate node for a function call expression which can be used as a result for your customization function.

        `create_call(MyClass, [arg1, arg2], {'key': value})` becomes `MyClass(arg1, arg2, key=value)` in the code.
        Function, arguments, and keyword arguments are recursively converted into CustomNodes.
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

    def create_default(self, value) -> Custom:
        """
        Creates an intermediate node for a default value which can be used as a result for your customization function.

        Default values are not included in the generated code when they match the actual default.
        The value is recursively converted into a CustomNode.
        """
        return CustomDefault(value=self._get_handler(value))

    def create_dict(self, value) -> Custom:
        """
        Creates an intermediate node for a dict-expression which can be used as a result for your customization function.

        `create_dict({'key': 'value'})` becomes `{'key': 'value'}` in the code.
        Dict keys and values are recursively converted into CustomNodes.
        """
        custom = {self._get_handler(k): self._get_handler(v) for k, v in value.items()}
        return CustomDict(value=custom)

    def create_value(self, value, repr: str | None = None) -> CustomValue:
        """
        Creates an intermediate node for a value with a custom representation which can be used as a result for your customization function.

        `create_value(my_obj, 'MyClass')` becomes `MyClass` in the code.
        Use this when you want to control the exact string representation of a value.
        """
        return CustomValue(value, repr)
