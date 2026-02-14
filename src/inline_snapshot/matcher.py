from .pydantic_compatibility import PydanticUndefined
from .pydantic_compatibility import get_fields


class IsPydanticAttributes:
    def __init__(self, typ, /, **attributes):
        self.typ = typ
        self.attributes = attributes

    def __eq__(self, other):

        other_type = type(other)

        if not (
            (
                hasattr(other_type, "__pydantic_generic_metadata__")
                and other_type.__pydantic_generic_metadata__["origin"] == self.typ
            )
            or type(other) is self.typ
        ):
            return NotImplemented

        for name, attribute in self.attributes.items():
            if not hasattr(other, name):
                return False
            if not getattr(other, name) == attribute:
                return False

        for name, field in get_fields(other).items():  # type: ignore
            if name in self.attributes:
                continue

            if not getattr(field, "repr", True):
                continue

            field_value = getattr(other, name)

            if field.default is not PydanticUndefined and field.default == field_value:
                continue

            elif (
                field.default_factory is not None
                and field.default_factory() == field_value
            ):
                continue
            return False

        return True

    def __repr__(self):
        args = ", ".join(f"{k} = {v!r}" for k, v in self.attributes.items())
        return f"IsPydantic[{self.typ!r}]({args})"


class IsPydanticMeta(type):
    def __getitem__(self, typ):
        return self(typ)


class IsPydantic(metaclass=IsPydanticMeta):
    def __init__(self, typ):
        self.typ = typ

    def __call__(self, **attributes) -> IsPydanticAttributes:
        return IsPydanticAttributes(self.typ, **attributes)

    def __repr__(self):
        return f"IsPydantic[{self.typ!r}]"
