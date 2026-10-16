import ast
from typing import Generator
from typing import Iterator
from typing import Union
from typing import cast

from inline_snapshot._customize._custom import Custom
from inline_snapshot._customize._custom_sequence import CustomList
from inline_snapshot._customize._custom_undefined import CustomUndefined
from inline_snapshot._generator_utils import split_gen
from inline_snapshot._new_adapter import NewAdapter

from ..._change import ChangeBase
from ..._change import Delete
from ..._change import ListInsert
from ..._global_state import state
from ..snapshot_data import SnapshotOperation
from ..snapshot_value import ignore_old_value


class CollectionOperation(SnapshotOperation):
    requested = "in"
    current = "x in snapshot"

    def __init__(self):
        self.element_changes: list[ChangeBase] = []

    def _observe_item(self, value, item):
        old_value: Custom = CustomUndefined()
        old_node = None
        if not isinstance(value._old_value, CustomUndefined):
            if value._ast_node is None:
                elements = [None] * len(value._old_value.value)
            else:
                assert isinstance(value._ast_node, ast.List)
                elements = value._ast_node.elts
            for candidate, node in zip(value._old_value.value, elements):
                if candidate._eval() == item:
                    old_value = candidate
                    old_node = node
                    break

        if (
            state().active
            and old_node is not None
            and value._context.expr.node is not None
        ):
            result = split_gen(
                NewAdapter(value._context).compare(old_value, old_node, item)
            )
            self.element_changes.extend(result.list)
            return result.value

        return value.to_custom(item, _build_new_value=True)

    def contains(self, value, item):
        if isinstance(value._old_value, CustomUndefined):
            state().missing_values += 1

        if isinstance(value._new_value, CustomUndefined):
            value._new_value = CustomList([self._observe_item(value, item)])
        else:
            if item not in value._new_value._eval():
                value._new_value.value.append(self._observe_item(value, item))

        if ignore_old_value() or isinstance(value._old_value, CustomUndefined):
            result = True
        else:
            result = value._return(item in value._old_value._eval())
        value._refresh_changes()
        return result

    def _new_code(self, value) -> Generator[ChangeBase, None, str]:
        code = yield from value._new_value._code_repr(value._context)
        return code

    def _get_changes(self, value) -> Iterator[ChangeBase]:
        assert isinstance(value._old_value, CustomList), value._old_value
        assert isinstance(value._new_value, CustomList), value._new_value

        if value._ast_node is None:
            elements: list[ast.expr | None] = [None] * len(value._old_value.value)
        else:
            assert isinstance(value._ast_node, ast.List)
            elements = cast(list[ast.expr | None], value._ast_node.elts)

        yield from self.element_changes

        for old_value, old_node in zip(value._old_value.value, elements):
            if old_value not in value._new_value.value:
                yield Delete(
                    flag="trim",
                    file=value._file,
                    node=old_node,
                )

        new_codes = []
        for v in value._new_value.value:
            if v not in value._old_value.value:
                new_code = yield from v._code_repr(value._context)
                new_codes.append(new_code)

        if new_codes:
            yield ListInsert(
                flag="fix",
                file=value._file,
                node=cast(Union[ast.List, ast.Tuple], value._ast_node),
                position=len(value._old_value.value),
                new_code=new_codes,
            )
