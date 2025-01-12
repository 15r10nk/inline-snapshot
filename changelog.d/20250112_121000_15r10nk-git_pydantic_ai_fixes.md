### Fixed

- snapshots with pydantic models can now be compared multiple times

    ``` python
    class A(BaseModel):
        a: int


    def test_something():
        for _ in [1, 2]:
            assert A(a=1) == snapshot(A(a=1))
    ```
