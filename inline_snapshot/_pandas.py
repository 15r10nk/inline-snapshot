from functools import wraps
from typing import Optional

from pandas import DataFrame
from pandas import Index
from pandas import Series
from pandas.testing import assert_frame_equal as real_assert_frame_equal
from pandas.testing import assert_index_equal as real_assert_index_equal
from pandas.testing import assert_series_equal as real_assert_series_equal


def make_assert_equals(data_type, assert_equals, repr_function):

    class Wrapper:
        def __init__(self, df, cmp):
            self.df = df
            self.cmp = cmp

        def __repr__(self):
            return f"{data_type.__name__}({repr(repr_function(self.df))})"

        def __eq__(self, other):
            if not isinstance(other, data_type):
                return NotImplemented
            return self.cmp(self.df, other)

    @wraps(assert_equals)
    def result(df, df_snapshot, *args, **kargs):
        error: Optional[AssertionError] = None

        def cmp(a, b):
            nonlocal error
            try:
                assert_equals(a, b, *args, **kargs)
            except AssertionError as e:
                error = e
                return False
            return True

        if not Wrapper(df, cmp) == df_snapshot:
            assert error is not None
            raise error

    return result


assert_frame_equal = make_assert_equals(
    DataFrame, real_assert_frame_equal, lambda df: df.to_dict("records")
)
assert_series_equal = make_assert_equals(
    Series, real_assert_series_equal, lambda df: df.to_dict()
)
assert_index_equal = make_assert_equals(
    Index, real_assert_index_equal, lambda df: df.to_list()
)
