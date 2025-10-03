import os
import sys
from pathlib import Path

import pytest
from executing import is_pytest_compatible
from rich.console import Console

from . import _config
from ._exceptions import UsageError
from ._fix_assert import fix_assert
from ._flags import Flags
from ._get_snapshot_value import unwrap
from ._global_state import enter_snapshot_context
from ._global_state import leave_snapshot_context
from ._global_state import snapshot_env
from ._global_state import state
from ._snapshot_session import SnapshotSession
from .version import is_insider

pytest.register_assert_rewrite("inline_snapshot.extra")
pytest.register_assert_rewrite("inline_snapshot.testing._example")

if sys.version_info >= (3, 13):
    # fixes #186
    try:
        import readline  # noqa
    except (ImportError, ModuleNotFoundError):  # pragma: no cover
        # should fix #189 and #245
        pass


def pytest_addoption(parser, pluginmanager):
    group = parser.getgroup("inline-snapshot")

    group.addoption(
        "--inline-snapshot",
        metavar="(disable,short-report,report,review,create,update,trim,fix)*",
        dest="inline_snapshot",
        help="update specific snapshot values:\n"
        "disable: disable the snapshot logic\n"
        "short-report: show a short report\n"
        "report: show a longer report with a diff report\n"
        "review: allow to approve the changes interactive\n"
        "create: creates snapshots which are currently not defined\n"
        "update: update snapshots even if they are defined\n"
        "trim: changes the snapshot in a way which will make the snapshot more precise.\n"
        "fix: change snapshots which currently break your tests\n"
        "fix-assert: fix assertions which currently break your tests (insider only)\n",
    )

    config_path = Path("pyproject.toml")
    if config_path.exists():
        try:
            config = _config.read_config(config_path)
        except UsageError as e:
            raise pytest.UsageError(str(e))

        for name, value in config.shortcuts.items():
            value = ",".join(value)
            group.addoption(
                f"--{name}",
                action="store_const",
                const=value,
                dest="inline_snapshot",
                help=f'shortcut for "--inline-snapshot={value}"',
            )


categories = Flags.all().to_set()


def xdist_running(config):
    if "PYTEST_XDIST_WORKER" in os.environ:
        return True

    return (
        hasattr(config.option, "numprocesses")
        and config.option.numprocesses is not None
        and config.option.numprocesses != 0
    )


def is_relative_to(base, relative):
    try:
        relative.relative_to(base)
    except ValueError:
        return False
    return True


def find_pyproject(pytest_root, cwd):
    if is_relative_to(pytest_root, Path.cwd()):
        directory = Path.cwd()
    else:
        directory = pytest_root

    while not (pyproject_pytest := directory / "pyproject.toml").exists():
        if directory == directory.parent:
            break
        directory = directory.parent
    else:
        return pyproject_pytest


def is_xfail(request):
    if not "xfail" in request.keywords:
        return False
    xfail = request.keywords["xfail"]
    if xfail.args and xfail.args[0] == False:
        return False
    return True


@pytest.fixture(autouse=True)
def snapshot_check(request):
    SnapshotSession.test_enter()
    try:
        if is_xfail(request):
            with snapshot_env() as local_state:
                local_state.active = False
                yield
            return
        else:
            yield
    finally:
        SnapshotSession.test_exit(lambda message: pytest.fail(message, pytrace=False))


class InlineSnapshotPlugin:

    def __init__(self):
        self.session = SnapshotSession()

    @pytest.hookimpl
    def pytest_configure(self, config):
        enter_snapshot_context()

        # setup default flags
        if is_pytest_compatible():
            state().config.default_flags_tui = ["create", "review"]
            state().config.default_flags = ["report"]

        pyproject = find_pyproject(config.rootpath, Path.cwd())

        if config.option.inline_snapshot is not None:
            cli_flags = config.option.inline_snapshot.split(",")
            cli_flags = {flag for flag in cli_flags if flag}
        else:
            cli_flags = None

        def error(message):
            raise pytest.UsageError(message)

        self.session.load_config(
            pyproject,
            cli_flags=cli_flags,
            parallel_run=xdist_running(config),
            error=error,
            project_root=config.rootpath,
        )

    @pytest.hookimpl(trylast=True)
    def pytest_sessionfinish(self, session, exitstatus):
        config = session.config

        capture = config.pluginmanager.getplugin("capturemanager")

        suspend_capture = (
            capture._global_capturing is not None
            and capture._global_capturing.in_ is not None
            and capture._global_capturing.in_._state == "started"
        )

        if suspend_capture:
            capture._global_capturing.in_.suspend()

        try:

            self.session.show_report(Console(highlight=False))

        finally:
            if suspend_capture:
                capture._global_capturing.in_.resume()

    @pytest.hookimpl
    def pytest_unconfigure(self, config):
        leave_snapshot_context()

    @pytest.hookimpl
    def pytest_assertrepr_compare(self, config, op, left, right):

        if is_insider and state().active:
            import inspect

            frame = inspect.currentframe()
            frame = frame.f_back

            while inspect.getmodule(frame).__name__.startswith(("pluggy.", "_pytest.")):
                frame = frame.f_back

            fix_assert(frame, left, right)

        results = []
        left, left_unwrapped = unwrap(left)
        right, right_unwrapped = unwrap(right)

        if left_unwrapped or right_unwrapped:
            results = config.hook.pytest_assertrepr_compare(
                config=config, op=op, left=left, right=right
            )

        if results:
            return results[0]


@pytest.hookimpl
def pytest_configure(config):
    config.pluginmanager.register(InlineSnapshotPlugin(), "inline-snapshot-plugin")
