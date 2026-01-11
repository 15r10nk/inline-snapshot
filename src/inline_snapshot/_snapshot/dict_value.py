import ast
from typing import Generator
from typing import Iterator

from inline_snapshot._customize._custom_dict import CustomDict
from inline_snapshot._customize._custom_undefined import CustomUndefined

from .._adapter_context import AdapterContext
from .._change import ChangeBase
from .._change import Delete
from .._change import DictInsert
from .._global_state import state
from .generic_value import GenericValue
from .undecided_value import UndecidedValue


class DictValue(GenericValue):
    _current_op = "snapshot[key]"

    _new_value: CustomDict
    _old_value: CustomDict
    _ast_node: ast.Dict

    def __getitem__(self, index):
        if isinstance(self._new_value, CustomUndefined):
            self._new_value = CustomDict({})

        index = self.to_custom(index)

        if index not in self._new_value.value:
            if isinstance(self._old_value, CustomUndefined):
                state().missing_values += 1
                old_value = {}
            else:
                old_value = self._old_value.value

            child_node = None
            if self._ast_node is not None:
                assert isinstance(self._ast_node, ast.Dict)
                old_keys = [k for k in old_value.keys()]
                if index in old_keys:
                    pos = old_keys.index(index)
                    child_node = self._ast_node.values[pos]

            self._new_value.value[index] = UndecidedValue(
                old_value.get(index, CustomUndefined()), child_node, self._context
            )

        return self._new_value.value[index]

    def _re_eval(self, value, context: AdapterContext):
        super()._re_eval(value, context)

        if not isinstance(self._new_value, CustomUndefined) and not isinstance(
            self._old_value, CustomUndefined
        ):
            for key, s in self._new_value.value.items():
                if key in self._old_value.value:
                    s._re_eval(self._old_value.value[key], context)  # type:ignore

    def _new_code(self) -> Generator[ChangeBase, None, str]:
        values = []
        for k, v in self._new_value.value.items():
            if not isinstance(v, UndecidedValue):
                new_code = yield from v._new_code()  # type:ignore
                new_key = yield from k.repr(self._context)
                values.append(f"{new_key}: {new_code}")

        return "{" + ", ".join(values) + "}"

    def _get_changes(self) -> Iterator[ChangeBase]:

        assert not isinstance(self._old_value, CustomUndefined)

        if self._ast_node is None:
            values = [None] * len(self._old_value.value)
        else:
            assert isinstance(self._ast_node, ast.Dict)
            values = self._ast_node.values

        for key, node in zip(self._old_value.value.keys(), values):
            if key in self._new_value.value:
                # check values with same keys
                yield from self._new_value.value[key]._get_changes()  # type:ignore
            else:
                # delete entries
                yield Delete("trim", self._file, node, self._old_value.value[key])

        to_insert = []
        to_insert_values = []
        for key, new_value_element in self._new_value.value.items():
            if key not in self._old_value.value and not isinstance(
                new_value_element, UndecidedValue
            ):
                # add new values
                new_value = yield from new_value_element._new_code()  # type:ignore
                new_key = yield from key.repr(self._context)

                to_insert.append((new_key, new_value))
                to_insert_values.append((key, new_value_element))

        if to_insert:
            yield DictInsert(
                "create",
                self._file,
                self._ast_node,
                len(self._old_value.value),
                to_insert,
                to_insert_values,
            )
