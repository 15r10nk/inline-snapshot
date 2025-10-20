from __future__ import annotations

from inline_snapshot._customize import Custom
from inline_snapshot._customize import CustomDict
from inline_snapshot._customize import CustomList
from inline_snapshot._customize import CustomUnmanaged
from inline_snapshot._customize import CustomValue


def reeval(c1: Custom, c2: Custom) -> Custom:
    if type(c1) is not type(c2):
        return CustomUnmanaged(c2.raw_value)

    function_name = f"reeval_{type(c1).__name__}"
    return globals()[function_name](c1, c2)


def reeval_CustomList(c1: CustomList, c2: CustomList):
    assert len(c1.value) == len(c2.value)
    return CustomList(..., [reeval(a, b) for a, b in zip(c1.value, c2.value)])


def reeval_CustomUnmanaged(c1: CustomUnmanaged, c2: CustomUnmanaged):
    pass


def reeval_CustomValue(c1: CustomValue, c2: CustomValue):
    return c2


def compare(old_value: Custom, new_value: Custom) -> Custom:
    if isinstance(old_value, CustomUnmanaged):
        return old_value

    if isinstance(new_value, CustomUnmanaged):
        raise UsageError("unmanaged values can not be compared with snapshots")

    if type(old_value) is not type(new_value):
        return new_value

    function_name = f"compare_{type(old_value).__name__}"
    return globals()[function_name](old_value, new_value)


def compare_CustomValue(old_value: CustomValue, new_value: CustomValue) -> Custom:
    return new_value


def update_code(old_value: Custom, ast_node, new_value: Custom):

    function_name = f"update_code_{type(old_value).__name__}"
    return globals()[function_name](old_value, new_value)


class MergeCustom:

    def merge(self, c1: Custom, c2: Custom) -> Custom:
        if type(c1) is not type(c2):
            return CustomUnmanaged(c2.raw_value)

        function_name = f"reeval_{type(c1).__name__}"
        return globals()[function_name](c1, c2)

    def merge_X(self, c1: Custom, c2: Custom) -> Custom:
        raise NotImplementedError

    def merge_CustomList(self, c1: CustomList, c2: CustomList):
        assert len(c1.value) == len(c2.value)
        return CustomList(..., [self.merge(a, b) for a, b in zip(c1.value, c2.value)])

    def merge_CustomDict(self, c1: CustomDict, c2: CustomDict):
        assert c1.value.keys() == c2.value.keys()
        return {k: self.merge(c1.value[k], c2.value[k]) for k in c1.value.keys()}

    def merge_CustomUnmanaged(self, c1: CustomUnmanaged, c2: CustomUnmanaged):
        raise NotImplementedError

    def merge_CustomValue(self, c1: CustomValue, c2: CustomValue):
        raise NotImplementedError
