### Fixed

- fixed a crash when you changed the snapshot to use a custom constructor method for dataclass/pydantic models.

    example:
    ``` python
    from inline_snapshot import snapshot
    from pydantic import BaseModel


    class A(BaseModel):
        a: int

        @classmethod
        def from_str(cls, s):
            return cls(a=int(s))


    def test_something():
        assert A(a=2) == snapshot(A.from_str("1"))
    ```
