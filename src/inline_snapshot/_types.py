"""The following types are for type checking only."""

from typing import TYPE_CHECKING
from typing import Generic
from typing import Literal
from typing import TypeVar

if TYPE_CHECKING:

    from typing_extensions import TypeAlias

    T = TypeVar("T")

    Snapshot: TypeAlias = T

else:
    T = TypeVar("T")

    class Snapshot(Generic[T]):
        """Can be used to annotate function arguments which accept snapshot
        values.

        You can annotate function arguments with `Snapshot[T]` to declare that a snapshot-value can be passed as function argument.
        `Snapshot[T]` is a type alias for `T`, which allows you to pass `int` values instead of `int` snapshots.


        Example:
        <!-- inline-snapshot: create fix trim first_block outcome-passed=2 -->
        ``` python
        from typing import Optional
        from inline_snapshot import snapshot, Snapshot

        # required snapshots


        def check_in_bounds(value, lower: Snapshot[int], upper: Snapshot[int]):
            assert lower <= value <= upper


        def test_numbers():
            for c in "hello world":
                check_in_bounds(ord(c), snapshot(32), snapshot(119))

            # use with normal values
            check_in_bounds(5, 0, 10)


        # optional snapshots


        def check_container(
            value,
            *,
            value_repr: Optional[Snapshot[str]] = None,
            length: Optional[Snapshot[int]] = None
        ):
            if value_repr is not None:
                assert repr(value) == value_repr

            if length is not None:
                assert len(value) == length


        def test_container():
            check_container([1, 2], value_repr=snapshot("[1, 2]"), length=snapshot(2))

            check_container({1, 1}, length=snapshot(1))
        ```
        """


Category = Literal["update", "fix", "create", "trim"]
"""See [categories](categories.md)"""
