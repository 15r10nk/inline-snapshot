from __future__ import annotations

import ast
import warnings
from collections import defaultdict
from typing import Generator
from typing import Sequence

from inline_snapshot._adapter_context import AdapterContext
from inline_snapshot._align import add_x
from inline_snapshot._align import align
from inline_snapshot._change import CallArg
from inline_snapshot._change import ChangeBase
from inline_snapshot._change import Delete
from inline_snapshot._change import DictInsert
from inline_snapshot._change import ListInsert
from inline_snapshot._change import Replace
from inline_snapshot._change import RequiredImports
from inline_snapshot._compare_context import compare_context
from inline_snapshot._customize._custom import Custom
from inline_snapshot._customize._custom_call import CustomCall
from inline_snapshot._customize._custom_call import CustomDefault
from inline_snapshot._customize._custom_code import CustomCode
from inline_snapshot._customize._custom_dict import CustomDict
from inline_snapshot._customize._custom_sequence import CustomList
from inline_snapshot._customize._custom_sequence import CustomSequence
from inline_snapshot._customize._custom_undefined import CustomUndefined
from inline_snapshot._customize._custom_unmanaged import CustomUnmanaged
from inline_snapshot._exceptions import UsageError
from inline_snapshot._generator_utils import only_value
from inline_snapshot.syntax_warnings import InlineSnapshotInfo
from inline_snapshot.syntax_warnings import InlineSnapshotSyntaxWarning


def warn_star_expression(node, context):
    if isinstance(node, ast.Call):
        for pos_arg in node.args:
            if isinstance(pos_arg, ast.Starred):
                warnings.warn_explicit(
                    "star-expressions are not supported inside snapshots",
                    filename=context.file._source.filename,
                    lineno=pos_arg.lineno,
                    category=InlineSnapshotSyntaxWarning,
                )
                return True

        # keyword arguments
        for kw in node.keywords:
            if kw.arg is None:
                warnings.warn_explicit(
                    "star-expressions are not supported inside snapshots",
                    filename=context.file._source.filename,
                    lineno=kw.value.lineno,
                    category=InlineSnapshotSyntaxWarning,
                )
                return True

    if isinstance(node, (ast.Tuple, ast.List)):

        for e in node.elts:
            if isinstance(e, ast.Starred):
                warnings.warn_explicit(
                    "star-expressions are not supported inside snapshots",
                    filename=context.file.filename,
                    lineno=e.lineno,
                    category=InlineSnapshotSyntaxWarning,
                )
                return True
    if isinstance(node, ast.Dict):

        for key1, value in zip(node.keys, node.values):
            if key1 is None:
                warnings.warn_explicit(
                    "star-expressions are not supported inside snapshots",
                    filename=context.file._source.filename,
                    lineno=value.lineno,
                    category=InlineSnapshotSyntaxWarning,
                )
                return True

    return False


def reeval(old_value: Custom, value: Custom) -> Custom:
    function_name = f"reeval_{type(old_value).__name__}"
    result = globals()[function_name](old_value, value)
    assert isinstance(result, Custom)

    return result


def reeval_CustomList(old_value: CustomList, value: CustomList):
    assert len(old_value.value) == len(value.value)
    return CustomList([reeval(a, b) for a, b in zip(old_value.value, value.value)])


reeval_CustomTuple = reeval_CustomList


def reeval_CustomUnmanaged(old_value: CustomUnmanaged, value: CustomUnmanaged):
    old_value.value = value.value
    return old_value


def reeval_CustomUndefined(old_value, value):
    return value


def reeval_CustomCode(old_value: CustomCode, value: CustomCode):

    if not old_value._eval() == value._eval():
        raise UsageError(
            "snapshot value should not change. Use Is(...) for dynamic snapshot parts."
        )

    return value


def reeval_CustomCall(old_value: CustomCall, value: CustomCall):
    return CustomCall(
        reeval(old_value._function, value._function),
        [reeval(a, b) for a, b in zip(old_value._args, value._args)],
        {k: reeval(old_value._kwargs[k], value._kwargs[k]) for k in old_value._kwargs},
        {k: reeval(old_value._kwonly[k], value._kwonly[k]) for k in old_value._kwonly},
    )


def reeval_CustomDict(old_value, value):
    assert len(old_value.value) == len(value.value)
    return CustomDict(
        {
            reeval(k1, k2): reeval(v1, v2)
            for (k1, v1), (k2, v2) in zip(old_value.value.items(), value.value.items())
        }
    )


class NewAdapter:

    def __init__(self, context: AdapterContext):
        self.context = context

    def compare(
        self, old_value: Custom, old_node, new_value: Custom
    ) -> Generator[ChangeBase, None, Custom]:

        if isinstance(old_value, CustomUnmanaged):
            return old_value

        if isinstance(new_value, CustomUnmanaged):
            raise UsageError("unmanaged values can not be compared with snapshots")

        if (
            type(old_value) is type(new_value)
            and (
                isinstance(old_node, new_value.node_type)
                if old_node is not None
                else True
            )
            and (
                isinstance(old_value, (CustomCall, CustomSequence))
                if old_node is None
                else True
            )
        ):
            function_name = f"compare_{type(old_value).__name__}"
            result = yield from getattr(self, function_name)(
                old_value, old_node, new_value
            )
        else:
            result = yield from self.compare_CustomCode(old_value, old_node, new_value)
        return result

    def compare_CustomCode(
        self, old_value: Custom, old_node: ast.expr, new_value: Custom
    ) -> Generator[ChangeBase, None, Custom]:

        assert isinstance(old_value, Custom)
        assert isinstance(new_value, Custom)
        assert isinstance(old_node, (ast.expr, type(None))), old_node

        if old_node is None:
            new_code = ""
        else:
            new_code = yield from new_value._code_repr(self.context)

        if (
            isinstance(old_node, ast.JoinedStr)
            and isinstance(new_value, CustomCode)
            and isinstance(new_value.value, str)
        ):
            if not old_value._eval() == new_value._eval():

                value = only_value(new_value._code_repr(self.context))
                warnings.warn_explicit(
                    f"inline-snapshot will be able to fix f-strings in the future.\nThe current string value is:\n   {value}",
                    filename=self.context.file._source.filename,
                    lineno=old_node.lineno,
                    category=InlineSnapshotInfo,
                )
            return old_value

        if not old_value._eval() == new_value.original_value:
            if isinstance(old_value, CustomUndefined):
                flag = "create"
            else:
                flag = "fix"
        elif not isinstance(
            old_value, CustomUnmanaged
        ) and self.context.file.code_changed(old_node, new_code):
            flag = "update"
        else:
            # equal and equal repr
            return old_value

        yield Replace(
            node=old_node,
            file=self.context.file,
            new_code=new_code,
            flag=flag,
            old_value=old_value._eval(),
            new_value=new_value,
        )

        def needed_imports(value: Custom):
            imports: dict[str, set] = defaultdict(set)
            module_imports: set[str] = set()
            for import_info in value._needed_imports():
                if len(import_info) == 2:
                    module, name = import_info
                    imports[module].add(name)
                elif len(import_info) == 1:
                    module_imports.add(import_info[0])
            return imports, module_imports

        imports, module_imports = needed_imports(new_value)
        if imports or module_imports:
            yield RequiredImports(flag, self.context.file, imports, module_imports)

        return new_value

    def compare_CustomSequence(
        self, old_value: CustomSequence, old_node: ast.AST, new_value: CustomSequence
    ) -> Generator[ChangeBase, None, CustomSequence]:

        if old_node is not None:
            assert isinstance(
                old_node, ast.List if isinstance(old_value._eval(), list) else ast.Tuple
            )
            assert isinstance(old_node, (ast.List, ast.Tuple))

        else:
            pass  # pragma: no cover

        with compare_context():
            diff = add_x(align(old_value.value, new_value.value))
        old = zip(
            old_value.value,
            old_node.elts if old_node is not None else [None] * len(old_value.value),
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
                new_code = yield from new_value_element._code_repr(self.context)
                result.append(new_value_element)
                to_insert[old_position].append((new_code, new_value_element))
            elif c == "d":
                old_value_element, old_node_element = next(old)
                yield Delete(
                    "fix",
                    self.context.file,
                    old_node_element,
                    old_value_element,
                )
                old_position += 1
            else:
                assert False

        for position, code_values in to_insert.items():
            yield ListInsert(
                "fix",
                self.context.file,
                old_node,
                position,
                *zip(*code_values),  # type:ignore
            )

        return type(new_value)(result)

    compare_CustomTuple = compare_CustomSequence
    compare_CustomList = compare_CustomSequence

    def compare_CustomDict(
        self, old_value: CustomDict, old_node: ast.Dict, new_value: CustomDict
    ) -> Generator[ChangeBase, None, Custom]:
        assert isinstance(old_value, CustomDict)
        assert isinstance(new_value, CustomDict)

        if old_node is not None:

            for value2, node in zip(old_value.value.keys(), old_node.keys):
                assert node is not None
                try:
                    # this is just a sanity check, dicts should be ordered
                    node_value = ast.literal_eval(node)
                except Exception:
                    continue
                assert node_value == value2._eval()
        else:
            pass  # pragma: no cover

        result = {}
        for key2, node2 in zip(
            old_value.value.keys(),
            (
                old_node.values
                if old_node is not None
                else [None] * len(old_value.value)
            ),
        ):
            if key2 not in new_value.value:
                # delete entries
                yield Delete("fix", self.context.file, node2, old_value.value[key2])

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
                    assert False
                    node = None
                # check values with same keys
                result[key] = yield from self.compare(
                    old_value.value[key], node, new_value.value[key]
                )

                if to_insert:
                    new_code = []
                    for k, v in to_insert:
                        new_code_key = yield from k._code_repr(self.context)
                        new_code_value = yield from v._code_repr(self.context)
                        new_code.append((new_code_key, new_code_value))

                    yield DictInsert(
                        "fix",
                        self.context.file,
                        old_node,
                        insert_pos,
                        new_code,
                        to_insert,
                    )
                    to_insert = []

                insert_pos += 1

        if to_insert:
            new_code = []
            for k, v in to_insert:
                new_code_key = yield from k._code_repr(self.context)
                new_code_value = yield from v._code_repr(self.context)
                new_code.append(
                    (
                        new_code_key,
                        new_code_value,
                    )
                )

            yield DictInsert(
                "fix",
                self.context.file,
                old_node,
                len(old_value.value),
                new_code,
                to_insert,
            )

        return CustomDict(value=result)

    def compare_CustomCall(
        self, old_value: CustomCall, old_node: ast.Call, new_value: CustomCall
    ) -> Generator[ChangeBase, None, Custom]:

        call = new_value
        new_args = call.args
        new_kwargs = call.kwargs

        # positional arguments

        result_args = []

        flag = "update" if old_value._eval() == new_value.original_value else "fix"

        if flag == "update":

            def intercept(stream):
                while True:
                    try:
                        change = next(stream)
                        if change.flag == "fix":
                            change.flag = "update"
                        yield change
                    except StopIteration as stop:
                        return stop.value

        else:
            intercept = lambda a: a

        old_node_args: Sequence[ast.expr | None]
        if old_node:
            old_node_args = old_node.args
        else:
            old_node_args = [None] * len(new_args)

        for i, (new_value_element, node) in enumerate(zip(new_args, old_node_args)):
            old_value_element = old_value.argument(i)
            result = yield from intercept(
                self.compare(old_value_element, node, new_value_element)
            )
            result_args.append(result)

        old_args_len = len(old_node.args if old_node else old_value.args)

        if old_node is not None:
            if old_args_len > len(new_args):
                for arg_pos, node in list(enumerate(old_node.args))[len(new_args) :]:
                    yield Delete(
                        flag,
                        self.context.file,
                        node,
                        old_value.argument(arg_pos),
                    )

        if old_args_len < len(new_args):
            for insert_pos, value in list(enumerate(new_args))[old_args_len:]:
                new_code = yield from value._code_repr(self.context)
                yield CallArg(
                    flag=flag,
                    file=self.context.file,
                    node=old_node,
                    arg_pos=insert_pos,
                    arg_name=None,
                    new_code=new_code,
                    new_value=value,
                )

        # keyword arguments
        result_kwargs = {}
        if old_node is None:
            old_keywords = {key: None for key in old_value._kwargs.keys()}
        else:
            old_keywords = {kw.arg: kw.value for kw in old_node.keywords}

        for kw_arg, kw_value in old_keywords.items():
            missing = kw_arg not in new_kwargs
            if missing or isinstance(new_kwargs[kw_arg], CustomDefault):
                # delete entries
                yield Delete(
                    (
                        "update"
                        if not missing
                        and old_value.argument(kw_arg) == new_value.argument(kw_arg)
                        else flag
                    ),
                    self.context.file,
                    kw_value,
                    old_value.argument(kw_arg),
                )

        to_insert = []
        insert_pos = 0
        for key, new_value_element in new_kwargs.items():
            if isinstance(new_value_element, CustomDefault):
                continue
            if key not in old_keywords:
                # add new values
                to_insert.append((key, new_value_element))
                result_kwargs[key] = new_value_element
            else:
                node = old_keywords[key]

                # check values with same keys
                old_value_element = old_value.argument(key)
                result_kwargs[key] = yield from intercept(
                    self.compare(old_value_element, node, new_value_element)
                )

                if to_insert:
                    for key, value in to_insert:
                        new_code = yield from value._code_repr(self.context)
                        yield CallArg(
                            flag=flag,
                            file=self.context.file,
                            node=old_node,
                            arg_pos=insert_pos,
                            arg_name=key,
                            new_code=new_code,
                            new_value=value,
                        )
                    to_insert = []

                insert_pos += 1

        if to_insert:

            for key, value in to_insert:
                new_code = yield from value._code_repr(self.context)

                yield CallArg(
                    flag=flag,
                    file=self.context.file,
                    node=old_node,
                    arg_pos=insert_pos,
                    arg_name=key,
                    new_code=new_code,
                    new_value=value,
                )

        return CustomCall(
            (
                yield from intercept(
                    self.compare(
                        old_value._function,
                        old_node.func if old_node else None,
                        new_value._function,
                    )
                )
            ),
            result_args,
            result_kwargs,
        )
