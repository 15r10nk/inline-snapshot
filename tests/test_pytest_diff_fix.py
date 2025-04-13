import pytest
from executing import is_pytest_compatible

from inline_snapshot import snapshot
from inline_snapshot.testing._example import Example


@pytest.mark.skipif(
    not is_pytest_compatible(),
    reason="pytest assert rewriting and report can not be used at the same time",
)
def test_pytest_diff_fix():

    Example(
        """\
from inline_snapshot import snapshot,Is


def test_dict_report():
    usd = snapshot({"name": "US Dollar", "code": "USD", "symbol": "$"})
    usd2 = Is([1,2])

    price = {
        "amount": 1,
        "currency": {
            "code": "USD",
            "name": "US Dollar",
            "symbol": "$",
        },
        "b":[1,2]
    }

    assert price == snapshot({
        "amount": 2,
        "currency": usd,
        "b":usd2
    })
"""
    ).run_pytest(
        ["--inline-snapshot=report", "-vv"],
        error=snapshot(
            """\
>       assert price == snapshot({
E       AssertionError: assert {'amount': 1, 'currency': {'code': 'USD', 'name': 'US Dollar', 'symbol': '$'}, 'b': [1, 2]} == {'amount': 2, 'currency': {'name': 'US Dollar', 'code': 'USD', 'symbol': '$'}, 'b': [1, 2]}
E         \n\
E         Common items:
E         {'b': [1, 2], 'currency': {'code': 'USD', 'name': 'US Dollar', 'symbol': '$'}}
E         Differing items:
E         {'amount': 1} != {'amount': 2}
E         \n\
E         Full diff:
E           {
E         -     'amount': 2,
E         ?               ^
E         +     'amount': 1,
E         ?               ^
E               'b': [
E                   1,
E                   2,
E               ],
E               'currency': {
E                   'code': 'USD',
E                   'name': 'US Dollar',
E                   'symbol': '$',
E               },
E           }
"""
        ),
        returncode=1,
    )
