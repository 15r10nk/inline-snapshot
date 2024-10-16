from __future__ import annotations

import ast

from .adapter import Adapter
from .adapter import Item


class DataclassAdapter(Adapter):

    def items(self, value, node):

        assert isinstance(node, ast.Call)
        assert len(value) == len(node.keywords)
        assert not node.args
        assert all(kw.arg for kw in node.keywords)

        return [
            Item(value=getattr(value, kw.arg), node=kw.value)
            for kw in node.keywords
            if kw.arg
        ]

    def assign(self, old_value, old_node, new_value):
        return old_value
        yield
