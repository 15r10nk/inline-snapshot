import ast
from typing import Generator
from typing import Iterator
from typing import List
from typing import Union

from inline_snapshot._customize._custom import Custom
from inline_snapshot._customize._custom_sequence import CustomList
from inline_snapshot._customize._custom_undefined import CustomUndefined
from inline_snapshot._customize._uncustomized import Uncustomized
from inline_snapshot._generator_utils import split_gen
from inline_snapshot._new_adapter import NewAdapter

from .._change import ChangeBase
from .._change import Delete
from .._change import ListInsert
from .._global_state import state
from .generic_value import GenericValue
from .generic_value import ignore_old_value


class CollectionValue(GenericValue):
    _current_op = "x in snapshot"
    _ast_node: Union[ast.List, ast.Tuple]
    _new_value: CustomList
    _element_changes: List[ChangeBase]

    def _observe_item(self, item):
        old_value: Custom = CustomUndefined()
        old_node = None
        if not isinstance(self._old_value, CustomUndefined):
            if self._ast_node is None:
                elements = [None] * len(self._old_value.value)
            else:
                assert isinstance(self._ast_node, ast.List)
                elements = self._ast_node.elts
            for candidate, node in zip(self._old_value.value, elements):
                if candidate._eval() == item:
                    old_value = candidate
                    old_node = node
                    break

        if (
            state().active
            and old_node is not None
            and self._context.expr.node is not None
        ):
            result = split_gen(
                NewAdapter(self._context).compare(
                    old_value, old_node, Uncustomized(item)
                )
            )
            self._element_changes.extend(result.list)
            return result.value

        return self.to_custom(item, old_value, _build_new_value=True)

    def __contains__(self, item):
        if not hasattr(self, "_element_changes"):
            self._element_changes = []

        if isinstance(self._old_value, CustomUndefined):
            state().missing_values += 1

        if isinstance(self._new_value, CustomUndefined):
            self._new_value = CustomList([self._observe_item(item)])
        else:
            if item not in self._new_value._eval():
                self._new_value.value.append(self._observe_item(item))

        if ignore_old_value() or isinstance(self._old_value, CustomUndefined):
            return True
        else:
            return self._return(item in self._old_value._eval())

    def _new_code(self) -> Generator[ChangeBase, None, str]:
        code = yield from self._new_value._code_repr(self._context)
        return code

    def _get_changes(self) -> Iterator[ChangeBase]:
        assert isinstance(self._old_value, CustomList), self._old_value
        assert isinstance(self._new_value, CustomList), self._new_value

        if self._ast_node is None:
            elements = [None] * len(self._old_value.value)
        else:
            assert isinstance(self._ast_node, ast.List)
            elements = self._ast_node.elts

        yield from getattr(self, "_element_changes", [])

        for old_value, old_node in zip(self._old_value.value, elements):
            if old_value not in self._new_value.value:
                yield Delete(
                    flag="trim",
                    file=self._file,
                    node=old_node,
                )

        new_codes = []
        for v in self._new_value.value:
            if v not in self._old_value.value:
                new_code = yield from v._code_repr(self._context)
                new_codes.append(new_code)

        if new_codes:
            yield ListInsert(
                flag="fix",
                file=self._file,
                node=self._ast_node,
                position=len(self._old_value.value),
                new_code=new_codes,
            )
