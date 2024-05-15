from functools import wraps
from typing import Optional

from pandas import DataFrame
from pandas.testing import assert_frame_equal as real_assert_frame_equal


class Wrapper:
    def __init__(self, df, cmp):
        self.df = df
        self.cmp = cmp

    def __repr__(self):
        return f"DataFrame({self.df.to_dict()!r})"

    def __eq__(self, other):
        if not isinstance(other, DataFrame):
            return NotImplemented
        return self.cmp(self.df, other)


@wraps(real_assert_frame_equal)
def assert_frame_equal(df, df_snapshot, *args, **kargs):
    error: Optional[AssertionError] = None

    def cmp(a, b):
        nonlocal error
        try:
            real_assert_frame_equal(a, b, *args, **kargs)
        except AssertionError as e:
            error = e
            return False
        return True

    if not Wrapper(df, cmp) == df_snapshot:
        assert error is not None
        raise error
