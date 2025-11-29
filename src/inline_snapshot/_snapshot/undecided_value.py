import ast
from typing import Iterator

from inline_snapshot._customize import Builder
from inline_snapshot._customize import Custom
from inline_snapshot._customize import CustomCall
from inline_snapshot._customize import CustomDefault
from inline_snapshot._customize import CustomDict
from inline_snapshot._customize import CustomList
from inline_snapshot._customize import CustomTuple
from inline_snapshot._customize import CustomUndefined
from inline_snapshot._customize import CustomUnmanaged
from inline_snapshot._customize import CustomValue
from inline_snapshot._new_adapter import NewAdapter

from .._adapter.adapter import AdapterContext
from .._change import Change
from .generic_value import GenericValue


def verify(value: Custom, node: ast.AST, eval) -> Custom:
    """Verify that a Custom value matches its corresponding AST node structure."""
    if isinstance(value, CustomUnmanaged):
        return value
    if isinstance(value, CustomDefault):
        return CustomDefault(value=verify(value.value, node, eval))

    if isinstance(node, ast.List):
        return verify_list(value, node, eval)
    elif isinstance(node, ast.Tuple):
        return verify_tuple(value, node, eval)
    elif isinstance(node, ast.Dict):
        return verify_dict(value, node, eval)
    elif isinstance(node, ast.Call):
        return verify_call(value, node, eval)
    else:
        # For other types, return the value as-is
        return value


def verify_list(value: Custom, node: ast.List, eval) -> Custom:
    """Verify a CustomList matches its List AST node."""
    assert isinstance(value, CustomList)
    return CustomList([verify(v, n, eval) for v, n in zip(value.value, node.elts)])


def verify_tuple(value: Custom, node: ast.Tuple, eval) -> Custom:
    """Verify a CustomTuple matches its Tuple AST node."""
    assert isinstance(value, CustomTuple)
    return CustomTuple([verify(v, n, eval) for v, n in zip(value.value, node.elts)])


def verify_dict(value: Custom, node: ast.Dict, eval) -> Custom:
    """Verify a CustomDict matches its Dict AST node."""
    assert isinstance(value, CustomDict)
    if any(key is None for key in node.keys):
        return value

    verified_items = {}
    for (key, val), key_node, val_node in zip(
        value.value.items(), node.keys, node.values
    ):
        verified_key = verify(key, key_node, eval) if key_node else key
        verified_val = verify(val, val_node, eval)
        verified_items[verified_key] = verified_val
    return CustomDict(value=verified_items)


def verify_call(value: Custom, node: ast.Call, eval) -> Custom:
    """Verify a CustomCall matches its Call AST node."""

    if not isinstance(value, CustomCall) or eval(node.func) != value._function.eval():
        return CustomValue(eval(node), ast.unparse(node))

    # Verify function
    verified_function = verify(value._function, node.func, eval)

    # Verify positional arguments
    verified_args = []
    for arg, arg_node in zip(value._args, node.args):
        verified_args.append(verify(arg, arg_node, eval))

    # Verify keyword arguments
    verified_kwargs = {}
    keyword_map = {kw.arg: kw.value for kw in node.keywords if kw.arg}
    for key, val in value._kwargs.items():
        if key in keyword_map:
            verified_kwargs[key] = verify(val, keyword_map[key], eval)
        else:
            verified_kwargs[key] = val

    return CustomCall(
        _function=verified_function, _args=verified_args, _kwargs=verified_kwargs
    )


class UndecidedValue(GenericValue):
    def __init__(self, old_value, ast_node, context: AdapterContext):

        old_value = Builder().get_handler(old_value)
        old_value = verify(old_value, ast_node, context.eval)

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

        new_value = Builder().get_handler(self._old_value.eval())

        adapter = NewAdapter(self._context)

        for change in adapter.compare(self._old_value, self._ast_node, new_value):
            assert change.flag == "update"
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
