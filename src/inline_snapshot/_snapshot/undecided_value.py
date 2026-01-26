import ast
from typing import Any
from typing import Iterator

from inline_snapshot._compare_context import compare_only
from inline_snapshot._customize._custom import Custom
from inline_snapshot._customize._custom_call import CustomCall
from inline_snapshot._customize._custom_code import CustomCode
from inline_snapshot._customize._custom_dict import CustomDict
from inline_snapshot._customize._custom_sequence import CustomList
from inline_snapshot._customize._custom_sequence import CustomTuple
from inline_snapshot._customize._custom_undefined import CustomUndefined
from inline_snapshot._customize._custom_unmanaged import CustomUnmanaged
from inline_snapshot._new_adapter import NewAdapter
from inline_snapshot._new_adapter import warn_star_expression
from inline_snapshot._unmanaged import is_unmanaged

from .._adapter_context import AdapterContext
from .._change import ChangeBase
from .generic_value import GenericValue


class AstToCustom:

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
        assert isinstance(self._new_value, CustomUndefined)

        new_value = self.to_custom(self._old_value._eval())

        adapter = NewAdapter(self._context)

        for change in adapter.compare(self._old_value, self._ast_node, new_value):
            assert change.flag == "update", change
            yield change

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
