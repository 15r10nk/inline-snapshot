import ast
from typing import Any
from typing import Iterator

from inline_snapshot._code_repr import mock_repr
from inline_snapshot._compare_context import compare_only
from inline_snapshot._customize._builder import Builder
from inline_snapshot._customize._custom import Custom
from inline_snapshot._customize._custom_call import CustomCall
from inline_snapshot._customize._custom_call import CustomDefault
from inline_snapshot._customize._custom_code import CustomCode
from inline_snapshot._customize._custom_dict import CustomDict
from inline_snapshot._customize._custom_sequence import CustomList
from inline_snapshot._customize._custom_sequence import CustomTuple
from inline_snapshot._customize._custom_subscript import CustomSubscript
from inline_snapshot._customize._custom_undefined import CustomUndefined
from inline_snapshot._customize._custom_unmanaged import CustomUnmanaged
from inline_snapshot._new_adapter import warn_star_expression
from inline_snapshot._unmanaged import is_unmanaged

from .._adapter_context import AdapterContext
from .._change import ChangeBase
from .generic_value import GenericValue


class AstToCustom:
    context: AdapterContext

    def __init__(self, context):
        self.eval = context.eval
        self.context = context

    def convert(self, value: Any, node: ast.expr):
        if is_unmanaged(value):
            return CustomUnmanaged(value)

        if warn_star_expression(node, self.context):
            return self.convert_generic(value, node)

        t = type(node).__name__
        return getattr(self, "convert_" + t, self.convert_generic)(value, node)

    def eval_convert(self, node):
        return self.convert(self.eval(node), node)

    def convert_generic(self, value: Any, node: ast.expr):
        if value is ...:
            return CustomUndefined()
        else:
            return CustomCode(value, ast.unparse(node))

    def convert_Call(self, value: Any, node: ast.Call):
        return CustomCall(
            self.eval_convert(node.func),
            [self.eval_convert(a) for a in node.args],
            {kw.arg: self.eval_convert(kw.value) for kw in node.keywords if kw.arg},
        )

    def convert_List(self, value: list, node: ast.List):

        return CustomList([self.convert(v, n) for v, n in zip(value, node.elts)])

    def convert_Tuple(self, value: tuple, node: ast.Tuple):
        return CustomTuple([self.convert(v, n) for v, n in zip(value, node.elts)])

    def convert_Dict(self, value: dict, node: ast.Dict):
        return CustomDict(
            {
                self.convert(k, k_node): self.convert(v, v_node)
                for (k, v), k_node, v_node in zip(value.items(), node.keys, node.values)
                if k_node is not None
            }
        )

    def convert_Subscript(self, value: Any, node: ast.Subscript):
        obj = self.eval_convert(node.value)
        index = self.eval_convert(node.slice)
        return CustomSubscript(obj=obj, index=index)


class ValueToCustom:
    """this implementation is for cpython <= 3.10 only.
    It works similar to AstToCustom but cannot handle calls
    """

    context: AdapterContext

    def __init__(self, context):
        self.context = context

    def convert(self, value: Any):
        if is_unmanaged(value):
            return CustomUnmanaged(value)

        if isinstance(value, CustomDefault):
            return self.convert(value.value)

        t = type(value).__name__
        return getattr(self, "convert_" + t, self.convert_generic)(value)

    def convert_generic(self, value: Any) -> Custom:
        if value is ...:
            return CustomUndefined()
        else:
            with mock_repr(self.context):
                result = Builder(self.context, _recursive=False)._get_handler(value)
            if isinstance(result, CustomCall) and result.function == type(value):
                function = self.convert(result.function)
                posonly_args = [self.convert(arg) for arg in result.args]
                kwargs = {k: self.convert(arg) for k, arg in result.kwargs.items()}

                return CustomCall(
                    function=function,
                    args=posonly_args,
                    kwargs=kwargs,
                )
            return result

    def convert_list(self, value: list):
        return CustomList([self.convert(v) for v in value])

    def convert_tuple(self, value: tuple):
        return CustomTuple([self.convert(v) for v in value])

    def convert_dict(self, value: dict):
        return CustomDict(
            {self.convert(k): self.convert(v) for (k, v) in value.items()}
        )


class UndecidedValue(GenericValue):
    def __init__(self, old_value, ast_node, context: AdapterContext):
        self._context = context
        self._ast_node = ast_node

        old_value = self.value_to_custom(old_value)

        assert isinstance(old_value, Custom)
        self._old_value = old_value
        self._new_value = CustomUndefined()

    def _change(self, cls):
        self.__class__ = cls

    def _new_code(self):
        assert False

    def _get_changes(self) -> Iterator[ChangeBase]:
        yield from ()
        return

    def __eq__(self, other):
        if compare_only():
            return False

        from .._snapshot.eq_value import EqValue

        self._change(EqValue)
        return self == other

    def __le__(self, other):
        from .._snapshot.min_max_value import MinValue

        self._change(MinValue)
        return self <= other

    def __ge__(self, other):
        from .._snapshot.min_max_value import MaxValue

        self._change(MaxValue)
        return self >= other

    def __contains__(self, item):
        from .._snapshot.collection_value import CollectionValue

        self._change(CollectionValue)
        return item in self

    def __getitem__(self, item):
        from .._snapshot.dict_value import DictValue

        self._change(DictValue)
        return self[item]
