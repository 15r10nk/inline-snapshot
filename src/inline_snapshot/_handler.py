from ._align import add_x
from ._align import align


class HandlerMeta(type):

    def __getattr__(self, name):
        def m(*a, **ka):
            for cls in reversed(self.__subclasses__()):
                result = getattr(cls, name)(*a, **ka)
                if result is not NotImplemented:
                    return result

        return m


class Handler(metaclass=HandlerMeta):
    pass


class DefaultHandler(Handler):
    @classmethod
    def use_valid_old_values(cls, old_value, new_value):
        if new_value == old_value:
            return old_value
        else:
            return new_value


class TupleListHandler(Handler):

    @classmethod
    def use_valid_old_values(cls, old_value, new_value):
        if (
            isinstance(new_value, list)
            and isinstance(old_value, list)
            or isinstance(new_value, tuple)
            and isinstance(old_value, tuple)
        ):
            diff = add_x(align(old_value, new_value))
            old = iter(old_value)
            new = iter(new_value)
            result = []
            for c in diff:
                if c in "mx":
                    old_value_element = next(old)
                    new_value_element = next(new)
                    result.append(
                        cls.use_valid_old_values(old_value_element, new_value_element)
                    )
                elif c == "i":
                    result.append(next(new))
                elif c == "d":
                    pass
                else:
                    assert False

            return type(new_value)(result)
        else:
            return NotImplemented


class DictHandler(Handler):
    @classmethod
    def use_valid_old_values(cls, old_value, new_value):
        if isinstance(new_value, dict) and isinstance(old_value, dict):
            result = {}

            for key, new_value_element in new_value.items():
                if key in old_value:
                    result[key] = cls.use_valid_old_values(
                        old_value[key], new_value_element
                    )
                else:
                    result[key] = new_value_element

            return result
        else:
            return NotImplemented
