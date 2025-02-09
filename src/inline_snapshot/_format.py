import subprocess as sp
import threading
import warnings

from rich.markup import escape

from . import _config
from ._problems import raise_problem


def enforce_formatting():
    return _config.config.format_command is not None


format_lock = threading.Lock()


def format_code(text, filename):
    with format_lock:
        if _config.config.format_command is not None:
            format_command = _config.config.format_command.format(filename=filename)
            result = sp.run(
                format_command,
                shell=True,
                input=text.encode("utf-8"),
                capture_output=True,
            )
            if result.returncode != 0:
                raise_problem(
                    f"""\
[b]The format_command '{escape(format_command)}' caused the following error:[/b]
"""
                    + result.stdout.decode("utf-8")
                    + result.stderr.decode("utf-8")
                )
                return text
            return result.stdout.decode("utf-8")

        try:
            from black import FileMode
            from black import find_pyproject_toml
            from black import format_str
            from black import parse_pyproject_toml
        except ImportError:
            raise_problem(
                f"""\
[b]inline-snapshot is not able to format your code.[/b]
This issue can be solved by:
 * installing {escape('inline-snapshot[black]')} which gives you the same formatting like in older versions
 * adding a `format-command` to your pyproject.toml (see [link=https://15r10nk.github.io/inline-snapshot/latest/configuration/#format-command]https://15r10nk.github.io/inline-snapshot/latest/configuration/#format-command[/link] for more information).
"""
            )
            return text

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            mode = FileMode()
            pyproject_path = find_pyproject_toml((), filename)
            if pyproject_path is not None:
                config = parse_pyproject_toml(pyproject_path)

                # TODO support all config parameters
                if "line_length" in config:
                    mode.line_length = int(config["line_length"])

            try:
                return format_str(text, mode=mode)
            except:
                raise_problem(
                    """\
[b]black could not format your code, which might be caused by this issue:[/b]
    [link=https://github.com/15r10nk/inline-snapshot/issues/138]https://github.com/15r10nk/inline-snapshot/issues/138[/link]\
"""
                )
                return text
