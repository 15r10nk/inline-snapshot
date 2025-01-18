import ast
from typing import Iterator

from .._change import Change
from .._change import Delete
from .._change import ListInsert
from .._change import Replace
from .._global_state import state
from .._sentinels import undefined
from .._utils import value_to_token
from .generic_value import GenericValue
from .generic_value import clone
from .generic_value import ignore_old_value


class CollectionValue(GenericValue):
    _current_op = "x in snapshot"

    def __contains__(self, item):
        if self._old_value is undefined:
            state().missing_values += 1

        if self._new_value is undefined:
            self._new_value = [clone(item)]
        else:
            if item not in self._new_value:
                self._new_value.append(clone(item))

        if ignore_old_value() or self._old_value is undefined:
            return True
        else:
            return self._return(item in self._old_value)

    def _new_code(self):
        return self._file._value_to_code(self._new_value)

    def _get_changes(self) -> Iterator[Change]:

        if self._ast_node is None:
            elements = [None] * len(self._old_value)
        else:
            assert isinstance(self._ast_node, ast.List)
            elements = self._ast_node.elts

        for old_value, old_node in zip(self._old_value, elements):
            if old_value not in self._new_value:
                yield Delete(
                    flag="trim",
                    file=self._file,
                    node=old_node,
                    old_value=old_value,
                )
                continue

            # check for update
            new_token = value_to_token(old_value)

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

        new_values = [v for v in self._new_value if v not in self._old_value]
        if new_values:
            yield ListInsert(
                flag="fix",
                file=self._file,
                node=self._ast_node,
                position=len(self._old_value),
                new_code=[self._file._value_to_code(v) for v in new_values],
                new_values=new_values,
            )
