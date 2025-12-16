import ast
from typing import Any
from typing import Iterator

from inline_snapshot._customize import Builder
from inline_snapshot._customize import Custom
from inline_snapshot._customize import CustomCall
from inline_snapshot._customize import CustomDict
from inline_snapshot._customize import CustomList
from inline_snapshot._customize import CustomTuple
from inline_snapshot._customize import CustomUndefined
from inline_snapshot._customize import CustomUnmanaged
from inline_snapshot._customize import CustomValue
from inline_snapshot._new_adapter import NewAdapter
from inline_snapshot._new_adapter import warn_star_expression
from inline_snapshot._unmanaged import is_unmanaged

from .._adapter_context import AdapterContext
from .._change import Change
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
            return CustomValue(value, ast.unparse(node))

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

        if not isinstance(old_value, Custom):
            if ast_node is not None:
                old_value = AstToCustom(context).convert(old_value, ast_node)
            else:
                old_value = Builder()._get_handler(old_value)

        assert isinstance(old_value, Custom)
        self._old_value = old_value
        self._new_value = CustomUndefined()
        self._ast_node = ast_node
        self._context = context

    def _change(self, cls):
        self.__class__ = cls

    def _new_code(self):
        assert False

    def _get_changes(self) -> Iterator[Change]:
        assert isinstance(self._new_value, CustomUndefined)

        new_value = Builder()._get_handler(self._old_value.eval())

        adapter = NewAdapter(self._context)

        for change in adapter.compare(self._old_value, self._ast_node, new_value):
            assert change.flag == "update", change
            yield change

        # def handle(node, obj):

        #     adapter = get_adapter_type(obj)
        #     if adapter is not None and hasattr(adapter, "items"):
        #         for item in adapter.items(obj, node):
        #             yield from handle(item.node, item.value)
        #         return

        #     if not isinstance(obj, CustomUnmanaged) and node is not None:
        #         new_token = value_to_token(obj.eval())
        #         if self._file._token_of_node(node) != new_token:
        #             new_code = self._file._token_to_code(new_token)

        #             yield Replace(
        #                 node=self._ast_node,
        #                 file=self._file,
        #                 new_code=new_code,
        #                 flag="update",
        #                 old_value=self._old_value,
        #                 new_value=self._old_value,
        #             )

        # yield from handle(self._ast_node, self._old_value)

    # functions which determine the type

    def __eq__(self, other):
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

    def __contains__(self, other):
        from .._snapshot.collection_value import CollectionValue

        self._change(CollectionValue)
        return other in self

    def __getitem__(self, item):
        from .._snapshot.dict_value import DictValue

        self._change(DictValue)
        return self[item]
