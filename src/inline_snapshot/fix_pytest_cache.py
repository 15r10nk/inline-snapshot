import types
from pathlib import Path
from typing import Callable
from typing import Optional

import _pytest.assertion.rewrite

fixed = False


def fix_pytest_cache():
    # keep this fix until https://github.com/pytest-dev/pytest/pull/14551 is merged
    global fixed

    if fixed:
        return

    _original_read_pyc = _pytest.assertion.rewrite._read_pyc

    def _read_pyc(
        source: Path, pyc: Path, trace: Callable[[str], None] = lambda x: None
    ) -> Optional[types.CodeType]:

        co = _original_read_pyc(source, pyc, trace)

        if co is not None:
            source_str = str(source)
            if co.co_filename != source_str:
                co = _replace_code_filenames(co, source_str)
        return co

    _pytest.assertion.rewrite._read_pyc = _read_pyc
    fixed = True


def _replace_code_filenames(co: types.CodeType, filename: str) -> types.CodeType:
    return co.replace(
        co_filename=filename,
        co_consts=tuple(
            (
                _replace_code_filenames(const, filename)
                if isinstance(const, types.CodeType)
                else const
            )
            for const in co.co_consts
        ),
    )
