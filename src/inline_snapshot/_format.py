import subprocess as sp
import warnings

from rich.markup import escape

from . import _config
from ._problems import raise_problem


def enforce_formatting():
    return _config.config.format_command is not None


def format_code(text, filename):
    if _config.config.format_command is not None:
        format_command = _config.config.format_command.format(filename=filename)
        result = sp.run(
            format_command, shell=True, input=text.encode("utf-8"), capture_output=True
        )
        if result.returncode != 0:
            raise_problem(
                f"""\
The format_command '{format_command}' caused the following error:
"""
                + result.stdout.decode("utf-8")
                + result.stderr.decode("utf-8")
            )
            return text
        return result.stdout.decode("utf-8")

    try:
        from black import main
        from click.testing import CliRunner
    except ImportError:
        raise_problem(
            escape(
                """\
You did not specify a format-command in you config and you did not installed inline-snapshot[black] for black support.
"""
            )
        )
        return text

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
