import warnings

from black import main
from click.testing import CliRunner
from inline_snapshot._problems import raise_problem


def format_code(text, filename):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(
            main, ["--stdin-filename", str(filename), "-"], input=text
        )

    if result.exit_code != 0:
        raise_problem(
            """\
black could not format your code, which might be caused by this issue:
    [link=https://github.com/15r10nk/inline-snapshot/issues/138]https://github.com/15r10nk/inline-snapshot/issues/138[/link]\
"""
        )
        return text

    return result.stdout
