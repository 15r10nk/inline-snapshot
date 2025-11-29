import ast
from typing import Iterator

from inline_snapshot._customize import Builder
from inline_snapshot._customize import CustomList
from inline_snapshot._customize import CustomUndefined

from .._change import Change
from .._change import Delete
from .._change import ListInsert
from .._change import Replace
from .._global_state import state
from .._utils import value_to_token
from .generic_value import GenericValue
from .generic_value import ignore_old_value


class CollectionValue(GenericValue):
    _current_op = "x in snapshot"

    def __contains__(self, item):
        if isinstance(self._old_value, CustomUndefined):
            state().missing_values += 1

        if isinstance(self._new_value, CustomUndefined):
            self._new_value = CustomList([Builder().get_handler(item)])
        else:
            if item not in self._new_value.eval():
                self._new_value.value.append(Builder().get_handler(item))

        if ignore_old_value() or isinstance(self._old_value, CustomUndefined):
            return True
        else:
            return self._return(item in self._old_value.eval())

    def _new_code(self):
        # TODO repr() ...
        return self._file._value_to_code(self._new_value.eval())

    def _get_changes(self) -> Iterator[Change]:
        assert isinstance(self._old_value, CustomList), self._old_value
        assert isinstance(self._new_value, CustomList), self._new_value

        if self._ast_node is None:
            elements = [None] * len(self._old_value.value)
        else:
            assert isinstance(self._ast_node, ast.List)
            elements = self._ast_node.elts

        for old_value, old_node in zip(self._old_value.value, elements):
            if old_value not in self._new_value.value:
                yield Delete(
                    flag="trim",
                    file=self._file,
                    node=old_node,
                    old_value=old_value,
                )
                continue

            # check for update
            new_token = value_to_token(old_value.eval())

            if (
                old_node is not None
                and self._file._token_of_node(old_node) != new_token
            ):
                new_code = self._file._token_to_code(new_token)

                yield Replace(
                    node=old_node,
                    file=self._file,
                    new_code=new_code,
                    flag="update",
                    old_value=old_value,
                    new_value=old_value,
                )

        new_values = [
            v.eval() for v in self._new_value.value if v not in self._old_value.value
        ]
        if new_values:
            yield ListInsert(
                flag="fix",
                file=self._file,
                node=self._ast_node,
                position=len(self._old_value.value),
                new_code=[self._file._value_to_code(v) for v in new_values],
                new_values=new_values,
            )
