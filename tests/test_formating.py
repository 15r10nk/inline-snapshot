import platform
import re
import sys

from inline_snapshot import snapshot
from inline_snapshot.testing import Example
from tests._is_normalized import normalization

executable = sys.executable.replace("\\", "\\\\")


def test_black_formatting_error(mocker):
    def custom_format_str(*a, **ka):
        raise Exception()

    mocker.patch("black.format_str", custom_format_str)

    Example(
        """\
from inline_snapshot import snapshot

def test_something():
    assert 1==snapshot()
    assert 1==snapshot(2)
    assert list(range(20)) == snapshot()
"""
    ).run_inline(
        ["--inline-snapshot=fix,create"],
        changed_files=snapshot(
            {
                "test_something.py": """\
from inline_snapshot import snapshot

def test_something():
    assert 1==snapshot(1)
    assert 1==snapshot(1)
    assert list(range(20)) == snapshot([0 ,1 ,2 ,3 ,4 ,5 ,6 ,7 ,8 ,9 ,10 ,11 ,12 ,13 ,14 ,15 ,16 ,17 ,18 ,19 ])
"""
            }
        ),
        report=snapshot(
            """\
----------------------------------- Problems -----------------------------------
black could not format your code, which might be caused by this issue:
    https://github.com/15r10nk/inline-snapshot/issues/138

"""
        ),
    )


def test_fstring_139():
    Example(
        """
from inline_snapshot import snapshot
snapshot(f'')
snapshot(rf'')
snapshot(Rf'')
snapshot(F'')
snapshot(rF'')
snapshot(RF'')


def test_a():
    return None
    """
    ).run_pytest(returncode=0)


def test_format_command():
    Example(
        {
            "fmt_cmd.py": """\
from sys import stdin
import re

text=stdin.read()
text=re.sub("#.*","",text)
print(text)
""",
            "pyproject.toml": f"""\
[tool.inline-snapshot]
format-command="{executable} fmt_cmd.py {{filename}}"
""",
            "test_a.py": """\
from inline_snapshot import snapshot
# some comment
def test_a():
    assert "5" == snapshot('''3''')# abc
""",
        }
    ).run_pytest(
        ["--inline-snapshot=fix"],
        changed_files=snapshot(
            {
                "test_a.py": """\
from inline_snapshot import snapshot

def test_a():
    assert "5" == snapshot('5')

"""
            }
        ),
        returncode=1,
    )


def test_format_command_fail():

    @normalization
    def NoPaths(text):
        path_re = "/[^ ]*/" if platform.system() != "Windows" else r".:\\[^ ]*\\"
        text = re.sub(
            "The.format_command.*following.error:",
            lambda m: re.sub(" *\n *", " ", m[0]),
            text,
            flags=re.MULTILINE | re.DOTALL,
        )
        text = re.sub(path_re, "/.../", text, flags=re.MULTILINE)

        text = re.sub(r"python(\.exe|\d\.\d*|\d)", "python", text)

        return text

    Example(
        {
            "fmt_cmd.py": """
import sys
print("some problem")
sys.exit(1)
""",
            "pyproject.toml": f"""\
[tool.inline-snapshot]
format-command="{executable} fmt_cmd.py {{filename}}"
""",
            "test_a.py": """
from inline_snapshot import snapshot

def test_a():
    assert "5" ==            snapshot('''3''')
""",
        }
    ).run_pytest(
        ["--inline-snapshot=fix"],
        term_columns=200,
        changed_files=snapshot(
            {
                "test_a.py": """\

from inline_snapshot import snapshot

def test_a():
    assert "5" ==            snapshot('5')
"""
            }
        ),
        report=NoPaths(
            snapshot(
                """\
-------------------------------------------------------------------------------------------- Fix snapshots ---------------------------------------------------------------------------------------------
+--------------------------------------------------------------------------------------------- test_a.py ----------------------------------------------------------------------------------------------+
| @@ -2,4 +2,4 @@                                                                                                                                                                                      |
|                                                                                                                                                                                                      |
|  from inline_snapshot import snapshot                                                                                                                                                                |
|                                                                                                                                                                                                      |
|  def test_a():                                                                                                                                                                                       |
| -    assert "5" ==            snapshot('''3''')                                                                                                                                                      |
| +    assert "5" ==            snapshot('5')                                                                                                                                                          |
+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
These changes will be applied, because you used fix
----------------------------------------------------------------------------------------------- Problems -----------------------------------------------------------------------------------------------
The format_command '/.../python fmt_cmd.py /.../test_a.py' caused the following error:
some problem\
"""
            )
        ),
        returncode=1,
    )


def test_no_black(mocker):

    mocker.patch.dict(sys.modules, {"black": None})

    Example(
        {
            "test_a.py": """
from inline_snapshot import snapshot

def test_a():
    assert "5" ==            snapshot('''3''')
""",
        }
    ).run_inline(
        ["--inline-snapshot=fix"],
        changed_files=snapshot(
            {
                "test_a.py": """\

from inline_snapshot import snapshot

def test_a():
    assert "5" ==            snapshot('5')
"""
            }
        ),
        report=snapshot(
            """\
----------------------------------- Problems -----------------------------------
inline-snapshot is not able to format your code.
This issue can be solved by:
 * installing inline-snapshot[black] which gives you the same formatting like in
older versions
 * adding a `format-command` to your pyproject.toml (see \n\
https://15r10nk.github.io/inline-snapshot/latest/configuration/#format-command \n\
for more information).


"""
        ),
    )


def test_black_config():

    Example(
        {
            "pyproject.toml": """
[tool.black]
skip_magic_trailing_comma=true
skip_string_normalization=true
preview=true
""",
            "test_a.py": """
from inline_snapshot import snapshot

def test_a():
    assert 1+1 == snapshot(3)
""",
        }
    ).run_pytest(
        ["--inline-snapshot=fix"],
        changed_files=snapshot(
            {
                "test_a.py": """\

from inline_snapshot import snapshot

def test_a():
    assert 1+1 == snapshot(2)
"""
            }
        ),
        returncode=1,
    )
