from __future__ import annotations

import ast
import warnings
from collections import defaultdict
from typing import Generator

from inline_snapshot._align import add_x
from inline_snapshot._align import align
from inline_snapshot._change import CallArg
from inline_snapshot._change import Change
from inline_snapshot._change import Delete
from inline_snapshot._change import DictInsert
from inline_snapshot._change import ListInsert
from inline_snapshot._change import Replace
from inline_snapshot._compare_context import compare_context
from inline_snapshot._customize import Custom
from inline_snapshot._customize import CustomCall
from inline_snapshot._customize import CustomDefault
from inline_snapshot._customize import CustomDict
from inline_snapshot._customize import CustomList
from inline_snapshot._customize import CustomSequence
from inline_snapshot._customize import CustomTuple
from inline_snapshot._customize import CustomUndefined
from inline_snapshot._customize import CustomUnmanaged
from inline_snapshot._customize import CustomValue
from inline_snapshot._utils import value_to_token
from inline_snapshot.syntax_warnings import InlineSnapshotInfo
from inline_snapshot.syntax_warnings import InlineSnapshotSyntaxWarning


def reeval(old_value: Custom, value: Custom) -> Custom:

    if isinstance(old_value, CustomDefault):
        return reeval(old_value.value, value)

    if isinstance(value, CustomDefault):
        return CustomDefault(reeval(old_value, value.value))

    if type(old_value) is not type(value):
        return CustomUnmanaged(value.eval())

    function_name = f"reeval_{type(old_value).__name__}"
    result = globals()[function_name](old_value, value)
    assert isinstance(result, Custom)
    assert result == value
    return result


def reeval_CustomList(old_value: CustomList, value: CustomList):
    assert len(old_value.value) == len(value.value)
    return CustomList([reeval(a, b) for a, b in zip(old_value.value, value.value)])


def reeval_CustomUnmanaged(old_value: CustomUnmanaged, value: CustomUnmanaged):
    old_value.value = value.value
    return old_value


def reeval_CustomUndefined(old_value, value):
    return value


def reeval_CustomValue(old_value: CustomValue, value: CustomValue):
    return value


def reeval_CustomCall(old_value: CustomCall, value: CustomCall):
    return CustomCall(
        _function=reeval(old_value._function, value._function),
        _args=[reeval(a, b) for a, b in zip(old_value._args, value._args)],
        _kwargs={
            k: reeval(old_value._kwargs[k], value._kwargs[k]) for k in old_value._kwargs
        },
        _kwonly={
            k: reeval(old_value._kwonly[k], value._kwonly[k]) for k in old_value._kwonly
        },
    )


def reeval_CustomTuple(old_value, value):
    assert len(old_value.value) == len(value.value)
    return CustomTuple([reeval(a, b) for a, b in zip(old_value.value, value.value)])


def reeval_CustomDict(old_value, value):
    assert len(old_value.value) == len(value.value)
    return CustomDict(
        {
            reeval(k1, k2): reeval(v1, v2)
            for (k1, v1), (k2, v2) in zip(old_value.value.items(), value.value.items())
        }
    )


class NewAdapter:

    def __init__(self, context):
        self.context = context

    def compare(
        self, old_value: Custom, old_node, new_value: Custom
    ) -> Generator[Change, None, Custom]:

        if isinstance(old_value, CustomUnmanaged):
            return old_value

        if isinstance(new_value, CustomUnmanaged):
            raise UsageError("unmanaged values can not be compared with snapshots")

        print("compare", old_value, new_value)

        if type(old_value) is not type(new_value) or not isinstance(
            old_node, new_value.node_type
        ):
            result = yield from self.compare_CustomValue(old_value, old_node, new_value)
            return result

        function_name = f"compare_{type(old_value).__name__}"
        result = yield from getattr(self, function_name)(old_value, old_node, new_value)

        return result

    def compare_CustomValue(
        self, old_value: Custom, old_node: ast.AST, new_value: Custom
    ) -> Generator[Change, None, Custom]:

        assert isinstance(old_value, Custom)
        assert isinstance(new_value, Custom)

        # because IsStr() != IsStr()
        if isinstance(old_value, CustomUnmanaged):
            return old_value

        if old_node is None:
            new_token = []
        else:
            new_token = value_to_token(new_value.eval())

        if (
            isinstance(old_node, ast.JoinedStr)
            and isinstance(new_value, CustomValue)
            and isinstance(new_value.value, str)
        ):
            if not old_value.eval() == new_value.eval():
                warnings.warn_explicit(
                    f"inline-snapshot will be able to fix f-strings in the future.\nThe current string value is:\n   {new_value!r}",
                    filename=self.context.file._source.filename,
                    lineno=old_node.lineno,
                    category=InlineSnapshotInfo,
                )
            return old_value

        if not old_value == new_value:
            if isinstance(old_value, CustomUndefined):
                flag = "create"
            else:
                flag = "fix"
        elif (
            old_node is not None
            and not isinstance(old_value, CustomUnmanaged)
            and self.context.file._token_of_node(old_node) != new_token
        ):
            flag = "update"
        else:
            # equal and equal repr
            return old_value

        new_code = self.context.file._token_to_code(new_token)

        yield Replace(
            node=old_node,
            file=self.context.file._source,
            new_code=new_code,
            flag=flag,
            old_value=old_value.eval(),
            new_value=new_value,
        )

        return new_value

    def compare_CustomSequence(
        self, old_value: CustomSequence, old_node: ast.AST, new_value: CustomSequence
    ) -> Generator[Change, None, CustomList]:

        if old_node is not None:
            if not isinstance(
                old_node, ast.List if isinstance(old_value.eval(), list) else ast.Tuple
            ):
                breakpoint()
                assert False

            for e in old_node.elts:
                if isinstance(e, ast.Starred):
                    warnings.warn_explicit(
                        "star-expressions are not supported inside snapshots",
                        filename=self.context.file.filename,
                        lineno=e.lineno,
                        category=InlineSnapshotSyntaxWarning,
                    )
                    return old_value

        with compare_context():
            diff = add_x(align(old_value.value, new_value.value))
        old = zip(
            old_value.value,
            old_node.elts if old_node is not None else [None] * len(old_value),
        )
        new = iter(new_value.value)
        old_position = 0
        to_insert = defaultdict(list)
        result = []
        for c in diff:
            if c in "mx":
                old_value_element, old_node_element = next(old)
                new_value_element = next(new)
                v = yield from self.compare(
                    old_value_element, old_node_element, new_value_element
                )
                result.append(v)
                old_position += 1
            elif c == "i":
                new_value_element = next(new)
                new_code = self.context.file._value_to_code(new_value_element)
                result.append(new_value_element)
                to_insert[old_position].append((new_code, new_value_element))
            elif c == "d":
                old_value_element, old_node_element = next(old)
                yield Delete(
                    "fix",
                    self.context.file._source,
                    old_node_element,
                    old_value_element,
                )
                old_position += 1
            else:
                assert False

        for position, code_values in to_insert.items():
            yield ListInsert(
                "fix", self.context.file._source, old_node, position, *zip(*code_values)
            )

        return type(new_value)(result)

    compare_CustomTuple = compare_CustomSequence
    compare_CustomList = compare_CustomSequence

    def compare_CustomDict(
        self, old_value: CustomDict, old_node: ast.AST, new_value: CustomDict
    ) -> Generator[Change, None, CustomDict]:
        assert isinstance(old_value, CustomDict)
        assert isinstance(new_value, CustomDict)

        if old_node is not None:
            if not (
                isinstance(old_node, ast.Dict)
                and len(old_value.value) == len(old_node.keys)
            ):
                result = yield from self.compare_CustomValue(
                    old_value, old_node, new_value
                )
                return result

            for key, value in zip(old_node.keys, old_node.values):
                if key is None:
                    warnings.warn_explicit(
                        "star-expressions are not supported inside snapshots",
                        filename=self.context.file._source.filename,
                        lineno=value.lineno,
                        category=InlineSnapshotSyntaxWarning,
                    )
                    return old_value

            for value, node in zip(old_value.value.keys(), old_node.keys):

                try:
                    # this is just a sanity check, dicts should be ordered
                    node_value = ast.literal_eval(node)
                except:
                    continue
                assert node_value == value.eval()

        result = {}
        for key, node in zip(
            old_value.value.keys(),
            (
                old_node.values
                if old_node is not None
                else [None] * len(old_value.value)
            ),
        ):
            if key not in new_value.value:
                # delete entries
                yield Delete(
                    "fix", self.context.file._source, node, old_value.value[key]
                )

        to_insert = []
        insert_pos = 0
        for key, new_value_element in new_value.value.items():
            if key not in old_value.value:
                # add new values
                to_insert.append((key, new_value_element))
                result[key] = new_value_element
            else:
                if isinstance(old_node, ast.Dict):
                    node = old_node.values[list(old_value.value.keys()).index(key)]
                else:
                    node = None
                # check values with same keys
                result[key] = yield from self.compare(
                    old_value.value[key], node, new_value.value[key]
                )

                if to_insert:
                    new_code = [
                        (
                            self.context.file._value_to_code(k),
                            self.context.file._value_to_code(v),
                        )
                        for k, v in to_insert
                    ]
                    yield DictInsert(
                        "fix",
                        self.context.file._source,
                        old_node,
                        insert_pos,
                        new_code,
                        to_insert,
                    )
                    to_insert = []

                insert_pos += 1

        if to_insert:
            new_code = [
                (
                    self.context.file._value_to_code(k),
                    self.context.file._value_to_code(v),
                )
                for k, v in to_insert
            ]
            yield DictInsert(
                "fix",
                self.context.file._source,
                old_node,
                len(old_value.value),
                new_code,
                to_insert,
            )

        return CustomDict(result)

    def compare_CustomCall(
        self, old_value: CustomCall, old_node: ast.AST, new_value: CustomCall
    ) -> Generator[Change, None, CustomCall]:

        if old_node is None or not isinstance(old_node, ast.Call):
            result = yield from self.compare_CustomValue(old_value, old_node, new_value)
            return result

        # positional arguments
        for pos_arg in old_node.args:
            if isinstance(pos_arg, ast.Starred):
                warnings.warn_explicit(
                    "star-expressions are not supported inside snapshots",
                    filename=self.context.file._source.filename,
                    lineno=pos_arg.lineno,
                    category=InlineSnapshotSyntaxWarning,
                )
                return old_value

        # keyword arguments
        for kw in old_node.keywords:
            if kw.arg is None:
                warnings.warn_explicit(
                    "star-expressions are not supported inside snapshots",
                    filename=self.context.file._source.filename,
                    lineno=kw.value.lineno,
                    category=InlineSnapshotSyntaxWarning,
                )
                return old_value

        call = new_value
        new_args = call.args
        new_kwargs = call.kwargs

        # positional arguments

        result_args = []

        for i, (new_value_element, node) in enumerate(zip(new_args, old_node.args)):
            old_value_element = old_value.argument(i)
            result = yield from self.compare(old_value_element, node, new_value_element)
            result_args.append(result)

        if len(old_node.args) > len(new_args):
            for arg_pos, node in list(enumerate(old_node.args))[len(new_args) :]:
                yield Delete(
                    "fix",
                    self.context.file._source,
                    node,
                    old_value.argument(arg_pos),
                )

        if len(old_node.args) < len(new_args):
            for insert_pos, value in list(enumerate(new_args))[len(old_node.args) :]:
                yield CallArg(
                    flag="fix",
                    file=self.context.file._source,
                    node=old_node,
                    arg_pos=insert_pos,
                    arg_name=None,
                    new_code=value.repr(),
                    new_value=value,
                )

        # keyword arguments
        result_kwargs = {}
        for kw in old_node.keywords:
            if kw.arg not in new_kwargs or isinstance(
                new_kwargs[kw.arg], CustomDefault
            ):
                # delete entries
                yield Delete(
                    (
                        "update"
                        if old_value.argument(kw.arg) == new_value.argument(kw.arg)
                        else "fix"
                    ),
                    self.context.file._source,
                    kw.value,
                    old_value.argument(kw.arg),
                )

        old_node_kwargs = {kw.arg: kw.value for kw in old_node.keywords}

        to_insert = []
        insert_pos = 0
        for key, new_value_element in new_kwargs.items():
            if isinstance(new_value_element, CustomDefault):
                continue
            if key not in old_node_kwargs:
                # add new values
                to_insert.append((key, new_value_element))
                result_kwargs[key] = new_value_element
            else:
                node = old_node_kwargs[key]

                # check values with same keys
                old_value_element = old_value.argument(key)
                result_kwargs[key] = yield from self.compare(
                    old_value_element, node, new_value_element
                )

                if to_insert:
                    for key, value in to_insert:

                        yield CallArg(
                            flag="fix",
                            file=self.context.file._source,
                            node=old_node,
                            arg_pos=insert_pos,
                            arg_name=key,
                            new_code=value.repr(),
                            new_value=value,
                        )
                    to_insert = []

                insert_pos += 1

        if to_insert:

            for key, value in to_insert:

                yield CallArg(
                    flag="fix",
                    file=self.context.file._source,
                    node=old_node,
                    arg_pos=insert_pos,
                    arg_name=key,
                    new_code=value.repr(),
                    new_value=value,
                )
        print(new_value._function)
        return CustomCall(
            _function=(
                yield from self.compare(
                    old_value._function, old_node.func, new_value._function
                )
            ),
            _args=result_args,
            _kwargs=result_kwargs,
        )
