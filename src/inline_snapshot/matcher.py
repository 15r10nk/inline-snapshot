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

        equal_attributes = {}

        for name, attribute in self.attributes.items():
            if not hasattr(other, name):
                return False
            other_attr = getattr(other, name)
            if not other_attr == attribute:
                return False
            equal_attributes[name] = other_attr

        from pydantic import ValidationError

        try:
            new_other = self.typ(**equal_attributes)
        except ValidationError:
            # cases like missing non-default arguments
            return False

        # check that all attributes which are not equal are equal to the default values
        return new_other == other

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
