from typing import Iterator

from inline_snapshot._adapter.adapter import adapter_map

from .._adapter.adapter import AdapterContext
from .._adapter.adapter import get_adapter_type
from .._change import Change
from .._change import Replace
from .._sentinels import undefined
from .._unmanaged import Unmanaged
from .._unmanaged import map_unmanaged
from .._utils import value_to_token
from .generic_value import GenericValue


class UndecidedValue(GenericValue):
    def __init__(self, old_value, ast_node, context: AdapterContext):

        old_value = adapter_map(old_value, map_unmanaged)
        self._old_value = old_value
        self._new_value = undefined
        self._ast_node = ast_node
        self._context = context

    def _change(self, cls):
        self.__class__ = cls

    def _new_code(self):
        assert False

    def _get_changes(self) -> Iterator[Change]:

        def handle(node, obj):

            adapter = get_adapter_type(obj)
            if adapter is not None and hasattr(adapter, "items"):
                for item in adapter.items(obj, node):
                    yield from handle(item.node, item.value)
                return

            if not isinstance(obj, Unmanaged) and node is not None:
                new_token = value_to_token(obj)
                if self._file._token_of_node(node) != new_token:
                    new_code = self._file._token_to_code(new_token)

                    yield Replace(
                        node=self._ast_node,
                        file=self._file,
                        new_code=new_code,
                        flag="update",
                        old_value=self._old_value,
                        new_value=self._old_value,
                    )

        if self._file._source is not None:
            yield from handle(self._ast_node, self._old_value)

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
