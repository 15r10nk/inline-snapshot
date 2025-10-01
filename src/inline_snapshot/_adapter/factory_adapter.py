"""Factory function adapter for handling factory functions like list() cleanly."""

from .adapter import Adapter


class FactoryAdapter(Adapter):
    """Adapter for factory functions used in defaultdict."""

    @classmethod
    def check_type(cls, value_type):
        # Check if value is a factory function (type/class or callable)
        if isinstance(value_type, type):
            return True
        return callable(value_type)

    @classmethod
    def repr(cls, value):
        # Return clean name for builtin types
        value_str = repr(value)
        if value_str.startswith("<class '"):
            return value_str[8:-2]  # Remove <class '...'> wrapper
        return value_str

    @classmethod
    def map(cls, value, map_function):
        return value

    def assign(self, old_value, old_node, new_value):
        # Preserve factory function identity
        return old_value
