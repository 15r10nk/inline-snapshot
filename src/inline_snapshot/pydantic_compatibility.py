try:
    import pydantic
except ImportError:  # pragma: no cover

    def get_fields(value):
        return []

    PydanticUndefined = None


else:
    # import pydantic
    if pydantic.version.VERSION.startswith("1."):
        # pydantic v1
        from pydantic.fields import Undefined as PydanticUndefined  # type: ignore[attr-defined,no-redef]

        def get_fields(value):
            return value.__fields__

    else:
        # pydantic v2
        from pydantic_core import PydanticUndefined

        def get_fields(value):
            return type(value).model_fields


__all__ = ("PydanticUndefined", "get_fields")
