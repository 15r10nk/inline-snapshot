import sys

import pytest


@pytest.fixture(params=["mypy", "pyright"])
def check_typing(pytester, request):
    prog = request.param

    def f(code):
        pytester.makefile(".py", test_something=code)
        pytester.makefile(
            ".toml",
            pyproject="""

[tool.pyright]
typeCheckingMode = 'strict'

[tool.mypy]
strict=true

        """,
        )

        result = pytester.run(sys.executable, "-m", prog, "test_something.py")

        print(result.stdout)
        assert result.ret == 0

    yield f


def test_typing(check_typing):
    check_typing(
        """
from inline_snapshot import snapshot
snapshot([])
snapshot({})
    """
    )
