from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from inline_snapshot._adapter_context import AdapterContext
from inline_snapshot._code_repr import mock_repr
from inline_snapshot._compare_context import compare_context
from inline_snapshot._customize._custom_sequence import CustomSequence
from inline_snapshot.plugin._context_value import ContextValue

from ._custom import Custom
from ._custom_call import CustomCall
from ._custom_call import CustomDefault
from ._custom_dict import CustomDict
from ._custom_external import CustomExternal
from ._custom_sequence import CustomList
from ._custom_sequence import CustomTuple
from ._custom_value import CustomValue


class Missing:
    def __repr__(self):
        return "missing"


missing = Missing()


@dataclass
class Builder:
    _snapshot_context: AdapterContext
    _build_new_value: bool = False

    def _get_handler(self, v, snapshot_value=None) -> Custom:

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

    def _customize(self, value, snapshot_value=missing):
        with mock_repr(self._snapshot_context):
            return self._get_handler(value, snapshot_value)

    def _customize_all(self, value):
        if not isinstance(value, Custom):
            value = self._customize(value)

        if isinstance(value, CustomSequence):
            value.value = [self._customize_all(c) for c in value.value]
        elif isinstance(value, CustomDict):
            value.value = {
                self._customize_all(k): self._customize_all(v)
                for k, v in value.value.items()
            }
        elif isinstance(value, CustomCall):
            value._function = self._customize_all(value._function)
            value._args = [self._customize_all(c) for c in value._args]
            value._kwargs = {
                k: self._customize_all(v) for k, v in value._kwargs.items()
            }
            value._kwonly = {
                k: self._customize_all(v) for k, v in value._kwonly.items()
            }
        elif isinstance(value, CustomDefault):
            value.value = self._customize_all(value.value)

        return value

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
        return CustomList(value=list(value))

    def create_tuple(self, value) -> Custom:
        """
        Creates an intermediate node for a tuple-expression which can be used as a result for your customization function.

        `create_tuple((1, 2, 3))` becomes `(1, 2, 3)` in the code.
        Tuple elements are recursively converted into CustomNodes.
        """
        return CustomTuple(value=list(value))

    def create_call(
        self, function, posonly_args=[], kwargs={}, kwonly_args={}
    ) -> Custom:
        """
        Creates an intermediate node for a function call expression which can be used as a result for your customization function.

        `create_call(MyClass, [arg1, arg2], {'key': value})` becomes `MyClass(arg1, arg2, key=value)` in the code.
        Function, arguments, and keyword arguments are recursively converted into CustomNodes.
        """
        return CustomCall(
            _function=function,
            _args=list(posonly_args),
            _kwargs=dict(kwargs),
            _kwonly=dict(kwonly_args),
        )

    def create_default(self, value) -> Custom:
        """
        Creates an intermediate node for a default value which can be used as a result for your customization function.

        Default values are not included in the generated code when they match the actual default.
        The value is recursively converted into a CustomNode.
        """
        return CustomDefault(value=value)

    def create_dict(self, value) -> Custom:
        """
        Creates an intermediate node for a dict-expression which can be used as a result for your customization function.

        `create_dict({'key': 'value'})` becomes `{'key': 'value'}` in the code.
        Dict keys and values are recursively converted into CustomNodes.
        """
        return CustomDict(value=dict(value))

    def create_value(self, value, repr: str | None = None) -> CustomValue:
        """
        Creates an intermediate node for a value with a custom representation which can be used as a result for your customization function.

        `create_value(my_obj, 'MyClass')` becomes `MyClass` in the code.
        Use this when you want to control the exact string representation of a value.
        """
        return CustomValue(value, repr)
