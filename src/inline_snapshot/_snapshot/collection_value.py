import ast
from typing import Generator
from typing import Iterator

from inline_snapshot._customize._custom_sequence import CustomList
from inline_snapshot._customize._custom_undefined import CustomUndefined

from .._change import ChangeBase
from .._change import Delete
from .._change import ListInsert
from .._change import Replace
from .._global_state import state
from .generic_value import GenericValue
from .generic_value import ignore_old_value


class CollectionValue(GenericValue):
    _current_op = "x in snapshot"
    _ast_node: ast.List | ast.Tuple
    _new_value: CustomList

    def __contains__(self, item):
        if isinstance(self._old_value, CustomUndefined):
            state().missing_values += 1

        if isinstance(self._new_value, CustomUndefined):
            self._new_value = CustomList([self.to_custom(item)])
        else:
            if item not in self._new_value.eval():
                self._new_value.value.append(self.to_custom(item))

        if ignore_old_value() or isinstance(self._old_value, CustomUndefined):
            return True
        else:
            return self._return(item in self._old_value.eval())

    def _new_code(self) -> Generator[ChangeBase, None, str]:
        code = yield from self._new_value.repr(self._context)
        return code

    def _get_changes(self) -> Iterator[ChangeBase]:
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
            new_code = yield from self.to_custom(old_value.eval()).repr(self._context)

            if self._file.code_changed(old_node, new_code):

                yield Replace(
                    node=old_node,
                    file=self._file,
                    new_code=new_code,
                    flag="update",
                    old_value=old_value,
                    new_value=old_value,
                )

        new_codes = []
        new_values = []
        for v in self._new_value.value:
            if v not in self._old_value.value:
                new_code = yield from v.repr(self._context)
                new_codes.append(new_code)
                new_values.append(v.eval())

        if new_codes:
            yield ListInsert(
                flag="fix",
                file=self._file,
                node=self._ast_node,
                position=len(self._old_value.value),
                new_code=new_codes,
                new_values=new_values,
            )
