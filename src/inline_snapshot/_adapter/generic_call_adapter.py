from __future__ import annotations

import ast
import warnings
from typing import Any

import pytest

from inline_snapshot._customize import CustomCall
from inline_snapshot._customize import CustomDefault
from inline_snapshot._customize import unwrap_default

from .._change import CallArg
from .._change import Delete
from ..syntax_warnings import InlineSnapshotSyntaxWarning
from .adapter import Adapter
from .adapter import Item


def get_adapter_for_type(value_type):
    assert False, "unreachable"
    assert isinstance(value_type, CustomCall)
    return CallAdapter


class CallAdapter(Adapter):

    @classmethod
    def arguments(cls, value) -> CustomCall:
        pytest.skip()
        return value

    @classmethod
    def argument(cls, value, pos_or_name) -> Any:
        pytest.skip()
        return cls.arguments(value).argument(pos_or_name)

    @classmethod
    def repr(cls, value):
        pytest.skip()

        call = cls.arguments(value)

        arguments = [repr(value) for value in call.args] + [
            f"{key}={repr(value)}"
            for key, value in call.kwargs.items()
            if not isinstance(value, CustomDefault)
        ]

        return f"{repr(type(value))}({', '.join(arguments)})"

    @classmethod
    def map(cls, value, map_function):
        pytest.skip()
        return cls.arguments(value).map(map_function)

    @classmethod
    def items(cls, value, node):
        pytest.skip()

        args = cls.arguments(value)
        new_args = args.args
        new_kwargs = args.kwargs

        if node is not None:
            assert isinstance(node, ast.Call)
            assert all(kw.arg for kw in node.keywords)
            kw_arg_node = {kw.arg: kw.value for kw in node.keywords if kw.arg}.get

            def pos_arg_node(pos):
                return node.args[pos]

        else:

            def kw_arg_node(_):
                return None

            def pos_arg_node(_):
                return None

        return [
            Item(value=unwrap_default(arg), node=pos_arg_node(i))
            for i, arg in enumerate(new_args)
        ] + [
            Item(value=unwrap_default(kw), node=kw_arg_node(name))
            for name, kw in new_kwargs.items()
        ]

    def assign(self, old_value, old_node, new_value):
        pytest.skip()
        if old_node is None or not isinstance(old_node, ast.Call):
            result = yield from self.value_assign(old_value, old_node, new_value)
            return result

        call_type = self.context.eval(old_node.func)

        if not (isinstance(call_type, type) and self.check_type(call_type)):
            result = yield from self.value_assign(old_value, old_node, new_value)
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

        call = self.arguments(new_value)
        new_args = call.args
        new_kwargs = call.kwargs

        # positional arguments

        result_args = []

        for i, (new_value_element, node) in enumerate(zip(new_args, old_node.args)):
            old_value_element = self.argument(old_value, i)
            result = yield from self.get_adapter(
                old_value_element, unwrap_default(new_value_element)
            ).assign(old_value_element, node, unwrap_default(new_value_element))
            result_args.append(result)

        if len(old_node.args) > len(new_args):
            for arg_pos, node in list(enumerate(old_node.args))[len(new_args) :]:
                yield Delete(
                    "fix",
                    self.context.file._source,
                    node,
                    self.argument(old_value, arg_pos),
                )

        if len(old_node.args) < len(new_args):
            for insert_pos, value in list(enumerate(new_args))[len(old_node.args) :]:
                yield CallArg(
                    flag="fix",
                    file=self.context.file._source,
                    node=old_node,
                    arg_pos=insert_pos,
                    arg_name=None,
                    new_code=self.context.file._value_to_code(unwrap_default(value)),
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
                        if self.argument(old_value, kw.arg)
                        == self.argument(new_value, kw.arg)
                        else "fix"
                    ),
                    self.context.file._source,
                    kw.value,
                    self.argument(old_value, kw.arg),
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
                old_value_element = self.argument(old_value, key)
                result_kwargs[key] = yield from self.get_adapter(
                    old_value_element, new_value_element
                ).assign(old_value_element, node, new_value_element)

                if to_insert:
                    for key, value in to_insert:

                        yield CallArg(
                            flag="fix",
                            file=self.context.file._source,
                            node=old_node,
                            arg_pos=insert_pos,
                            arg_name=key,
                            new_code=self.context.file._value_to_code(value),
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
                    new_code=self.context.file._value_to_code(value),
                    new_value=value,
                )
        return type(old_value)(*result_args, **result_kwargs)
