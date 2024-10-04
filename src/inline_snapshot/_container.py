from __future__ import annotations

import ast

from ._sentinels import undefined
from ._update_allowed import update_allowed


def get_handler(value) -> BaseHandler:
    if isinstance(value, list):
        return ListHandler(value)
    if isinstance(value, tuple):
        return TupleHandler(value)
    if isinstance(value, dict):
        return DictHandler(value)

    if not update_allowed(value):
        return UnmanagedValueHandler(value)

    return ValueHandler(value)


class BaseHandler:
    def assign(self, value):
        raise NotImplementedError

    def get_value(self):
        raise NotImplementedError

    def re_eval(self, value, node):
        raise NotImplementedError


class ValueHandler(BaseHandler):
    def __init__(self, value):
        self._old_value = value
        self._new_value = undefined

    def get_changes(self, node: ast.AST):
        pass

    def re_eval(self, value, node):
        assert self._old_value == value

    def try_assign(self, value):
        if self._new_value is undefined:
            self._new_value = value
            return True
        else:
            return self._new_value == value


class UnmanagedValueHandler(BaseHandler):
    def __init__(self, value):
        self._old_value = value
        self._new_value = undefined

    def get_changes(self, node: ast.AST):
        pass

    def re_eval(self, value, node):
        pass

    def try_assign(self, value):
        if self._new_value is undefined:
            self._new_value = value
            return True
        else:
            return self._new_value == value


class ListHandler(BaseHandler):

    def __init__(self, value: list):
        self._old_value = [get_handler(element) for element in value]

    def re_eval(self, value, node):
        assert isinstance(value, list)
        assert len(value) == len(self._old_value)
        assert isinstance(node, ast.List), node

        for v, handler, node in zip(value, self._old_value, node.elts):
            handler.re_eval(v, node)

    def assign(self, value):
        if isinstance(value, list):
            ...()
        return self

    def get_changes(self):
        ...()


class TupleHandler(BaseHandler):
    def __init__(self, value: tuple):
        self._old_value = [get_handler(element) for element in value]

    def re_eval(self, value, node):
        assert isinstance(value, tuple)
        assert len(value) == len(self._old_value)
        assert isinstance(node, ast.Tuple)

        for v, handler, node in zip(value, self._old_value, node.elts):
            handler.re_eval(v, node)


class DictHandler(BaseHandler):
    def __init__(self, value: dict):
        self._old_value = {key: get_handler(element) for key, element in value.items()}

    def re_eval(self, value, node):
        assert isinstance(value, dict)
        assert len(value) == len(self._old_value)
        assert isinstance(node, ast.Dict)

        for (key, element), element_node in zip(value.items(), node.values):
            handler = self._old_value[key]
            handler.re_eval(element, element_node)
