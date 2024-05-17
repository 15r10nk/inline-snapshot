import os
import platform
import re
import subprocess as sp
from pathlib import Path
from tempfile import TemporaryDirectory


ansi_escape = re.compile(
    r"""
    \x1B  # ESC
    (?:   # 7-bit C1 Fe (except CSI)
        [@-Z\\-_]
    |     # or [ for CSI, followed by a control sequence
        \[
        [0-?]*  # Parameter bytes
        [ -/]*  # Intermediate bytes
        [@-~]   # Final byte
    )
""",
    re.VERBOSE,
)


class Example:
    def __init__(self, files):
        if isinstance(files, str):
            files = {"test_something.py": files}

        self.files = files

    def write_files(self, dir: Path):
        for name, content in self.files.items():
            (dir / name).write_text(content)

    def read_files(self, dir: Path):
        return {p.name: p.read_text() for p in dir.iterdir() if p.is_file()}

    def run_pytest(self, *args, changed_files=None, report=None, env={}):
        with TemporaryDirectory() as dir:
            dir = Path(dir)
            self.write_files(dir)

            cmd = ["pytest", *args]

            term_columns = 80

            command_env = dict(os.environ)
            command_env["TERM"] = "unknown"
            command_env["COLUMNS"] = str(
                term_columns + 1 if platform.system() == "Windows" else term_columns
            )
            command_env.pop("CI", None)

            command_env.update(env)

            result = sp.run(cmd, cwd=dir, capture_output=True, env=command_env)

            print("run>", *cmd)
            print("stdout:")
            print(result.stdout.decode())
            print("stderr:")
            print(result.stderr.decode())

            if report is not None:

                new_report = []
                record = False
                for line in result.stdout.decode().splitlines():
                    line = line.strip()
                    if line.startswith("===="):
                        record = False

                    if record and line:
                        new_report.append(line)

                    if line.startswith("====") and "inline snapshot" in line:
                        record = True

                new_report = "\n".join(new_report)

                new_report = ansi_escape.sub("", new_report)

                # fix windows problems
                new_report = new_report.replace("\u2500", "-")
                new_report = new_report.replace("\r", "")
                new_report = new_report.replace(" \n", " ⏎\n")

                assert new_report == report

            if changed_files is not None:
                current_files = {}

                for name, content in sorted(self.read_files(dir).items()):
                    if name not in self.files or self.files[name] != content:
                        current_files[name] = content
                assert changed_files == current_files

            return Example(self.read_files(dir))
