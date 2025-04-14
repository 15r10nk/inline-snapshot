import ast
import os
import sys
from pathlib import Path

import pytest
from executing import is_pytest_compatible
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.syntax import Syntax

from inline_snapshot.fix_pytest_diff import fix_pytest_diff

from . import _config
from . import _external
from . import _find_external
from ._change import apply_all
from ._code_repr import used_hasrepr
from ._find_external import ensure_import
from ._flags import Flags
from ._global_state import enter_snapshot_context
from ._global_state import leave_snapshot_context
from ._global_state import snapshot_env
from ._global_state import state
from ._inline_snapshot import used_externals
from ._problems import report_problems
from ._rewrite_code import ChangeRecorder
from ._snapshot.generic_value import GenericValue
from .pydantic_fix import pydantic_fix

pytest.register_assert_rewrite("inline_snapshot.extra")
pytest.register_assert_rewrite("inline_snapshot.testing._example")

if sys.version_info >= (3, 13):
    # fixes #186
    try:
        import readline  # noqa
    except ModuleNotFoundError:  # pragma: no cover
        # should fix #189
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
        "fix: change snapshots which currently break your tests\n",
    )

    config_path = Path("pyproject.toml")
    if config_path.exists():
        config = _config.read_config(config_path)
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
    return (
        hasattr(config.option, "numprocesses")
        and config.option.numprocesses is not None
        and config.option.numprocesses != 0
    )


def is_ci_run():
    ci_env_vars = (
        "CI",
        "bamboo.buildKey",
        "BUILD_ID",
        "BUILD_NUMBER",
        "BUILDKITE",
        "CIRCLECI",
        "CONTINUOUS_INTEGRATION",
        "GITHUB_ACTIONS",
        "HUDSON_URL",
        "JENKINS_URL",
        "TEAMCITY_VERSION",
        "TRAVIS",
    )
    for var in ci_env_vars:
        if os.environ.get(var, False):
            return var
    return False


def is_implementation_supported():
    return sys.implementation.name == "cpython"


def pytest_configure(config):
    enter_snapshot_context()

    directory = config.rootpath
    while not (pyproject := directory / "pyproject.toml").exists():
        if directory == directory.parent:
            break
        directory = directory.parent
    _config.config = _config.Config()

    if is_pytest_compatible():
        _config.config.default_flags_tui = ["create", "review"]
        _config.config.default_flags = ["report"]

    _config.read_config(pyproject, _config.config)

    console = Console()
    if console.is_terminal:
        default_flags = _config.config.default_flags_tui
    else:
        default_flags = _config.config.default_flags

    env_var = "INLINE_SNAPSHOT_DEFAULT_FLAGS"
    if env_var in os.environ:
        default_flags = os.environ[env_var].split(",")

    if config.option.inline_snapshot is None:
        flags = set(default_flags)
    else:
        flags = config.option.inline_snapshot.split(",")
        flags = {flag for flag in flags if flag}
        if xdist_running(config) and flags - {"disable"}:
            raise pytest.UsageError(
                f"--inline-snapshot={','.join(flags)} can not be combined with xdist"
            )
    state().flags = flags

    unknown_flags = flags - categories - {"disable", "review", "report", "short-report"}
    if unknown_flags:
        raise pytest.UsageError(
            f"--inline-snapshot={','.join(sorted(unknown_flags))} is a unknown flag"
        )

    if "disable" in flags and flags != {"disable"}:
        raise pytest.UsageError(
            f"--inline-snapshot=disable can not be combined with other flags ({', '.join(flags-{'disable'})})"
        )

    if xdist_running(config) or not is_implementation_supported() or is_ci_run():
        state().active = False

    elif flags & {"review"}:
        state().active = True

        state().update_flags = Flags.all()
    else:

        state().active = "disable" not in flags

        state().update_flags = Flags(flags & categories)

    external_storage = (
        _config.config.storage_dir or config.rootpath / ".inline-snapshot"
    ) / "external"

    state().storage = _external.DiscStorage(external_storage)

    if flags - {"short-report", "disable"} and not is_pytest_compatible():

        # hack to disable the assertion rewriting
        # I found no other way because the hook gets installed early
        sys.meta_path = [
            e for e in sys.meta_path if type(e).__name__ != "AssertionRewritingHook"
        ]

    pydantic_fix()

    fix_pytest_diff()

    state().storage.prune_new_files()


def is_xfail(request):
    if not "xfail" in request.keywords:
        return False
    xfail = request.keywords["xfail"]
    if xfail.args and xfail.args[0] == False:
        return False
    return True


@pytest.fixture(autouse=True)
def snapshot_check(request):
    state().missing_values = 0
    state().incorrect_values = 0

    if is_xfail(request):
        with snapshot_env() as local_state:
            local_state.active = False
            yield
        return
    else:
        yield

    missing_values = state().missing_values
    incorrect_values = state().incorrect_values

    if missing_values != 0:
        pytest.fail(
            (
                "your snapshot is missing one value."
                if missing_values == 1
                else f"your snapshot is missing {missing_values} values."
            ),
            pytrace=False,
        )

    if incorrect_values != 0:
        pytest.fail(
            "some snapshots in this test have incorrect values.",
            pytrace=False,
        )


def pytest_assertrepr_compare(config, op, left, right):

    results = []
    if isinstance(left, GenericValue):
        results = config.hook.pytest_assertrepr_compare(
            config=config, op=op, left=left._visible_value(), right=right
        )

    if isinstance(right, GenericValue):
        results = config.hook.pytest_assertrepr_compare(
            config=config, op=op, left=left, right=right._visible_value()
        )

    external_used = False
    if isinstance(right, _external.external):
        external_used = True
        if right._suffix == ".txt":
            right = right._load_value().decode()
        else:
            right = right._load_value()

    if isinstance(left, _external.external):
        external_used = True
        if left._suffix == ".txt":
            left = left._load_value().decode()
        else:
            left = left._load_value()

    if external_used:
        results = config.hook.pytest_assertrepr_compare(
            config=config, op=op, left=left, right=right
        )

    if results:
        return results[0]


def call_once(f):
    called = False
    result = None

    def w():
        nonlocal called
        nonlocal result
        if not called:
            result = f()
            called = True
        return result

    return w


def link(text, link=None):
    if link is None:
        link = text
    return f"[italic blue link={link}]{text}[/]"


def category_link(category):
    return link(
        category,
        f"https://15r10nk.github.io/inline-snapshot/latest/categories/#{category}",
    )


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    try:
        config = session.config

        @call_once
        def console():
            con = Console(highlight=False)
            con.print("\n")
            con.rule("[blue]inline-snapshot", characters="═")

            return con

        if xdist_running(config):
            if state().flags != {"disable"}:
                console().print(
                    "INFO: inline-snapshot was disabled because you used xdist\n"
                )
            return

        if env_var := is_ci_run():
            if state().flags != {"disable"}:
                console().print(
                    f'INFO: CI run was detected because environment variable "{env_var}" was defined.\n'
                    + "INFO: inline-snapshot runs with --inline-snapshot=disabled by default in CI.\n"
                )
            return

        if not is_implementation_supported():
            if state().flags != {"disable"}:
                console().print(
                    f"INFO: inline-snapshot was disabled because {sys.implementation.name} is not supported\n"
                )
            return

        if not state().active:
            return

        capture = config.pluginmanager.getplugin("capturemanager")

        # --inline-snapshot

        def apply_changes(flag):
            if flag in state().flags:
                console().print(
                    f"These changes will be applied, because you used {category_link(flag)}",
                    highlight=False,
                )
                console().print()
                return True
            if "review" in state().flags:
                result = Confirm.ask(
                    f"Do you want to {category_link(flag)} these snapshots?",
                    default=False,
                )
                console().print()
                return result
            else:
                console().print("These changes are not applied.")
                console().print(
                    f"Use [bold]--inline-snapshot={category_link(flag)} to apply them, "
                    "or use the interactive mode with [b]--inline-snapshot=[italic blue link=https://15r10nk.github.io/inline-snapshot/latest/pytest/#-inline-snapshotreview]review[/][/]",
                    highlight=False,
                )
                console().print()
                return False

        # auto mode
        changes = {f: [] for f in Flags.all()}

        snapshot_changes = {f: 0 for f in Flags.all()}

        for snapshot in state().snapshots.values():
            all_categories = set()
            for change in snapshot._changes():
                changes[change.flag].append(change)
                all_categories.add(change.flag)

            for category in all_categories:
                snapshot_changes[category] += 1

        capture.suspend_global_capture(in_=True)
        try:

            if "short-report" in state().flags:

                def report(flag, message, message_n):
                    num = snapshot_changes[flag]

                    if num and not getattr(state().update_flags, flag):
                        console().print(
                            message if num == 1 else message.format(num=num),
                            highlight=False,
                        )

                report(
                    "fix",
                    "Error: one snapshot has incorrect values ([b]--inline-snapshot=fix[/])",
                    "Error: {num} snapshots have incorrect values ([b]--inline-snapshot=fix[/])",
                )

                report(
                    "trim",
                    "Info: one snapshot can be trimmed ([b]--inline-snapshot=trim[/])",
                    "Info: {num} snapshots can be trimmed ([b]--inline-snapshot=trim[/])",
                )

                report(
                    "create",
                    "Error: one snapshot is missing a value ([b]--inline-snapshot=create[/])",
                    "Error: {num} snapshots are missing values ([b]--inline-snapshot=create[/])",
                )

                report(
                    "update",
                    "Info: one snapshot changed its representation ([b]--inline-snapshot=update[/])",
                    "Info: {num} snapshots changed their representation ([b]--inline-snapshot=update[/])",
                )

                if sum(snapshot_changes.values()) != 0:
                    console().print(
                        "\nYou can also use [b]--inline-snapshot=review[/] to approve the changes interactively",
                        highlight=False,
                    )

                return

            if not is_pytest_compatible():
                assert not any(
                    type(e).__name__ == "AssertionRewritingHook" for e in sys.meta_path
                )

            used_changes = []
            for flag in Flags.all():
                if not changes[flag]:
                    continue

                if not {"review", "report", flag} & state().flags:
                    continue

                @call_once
                def header():
                    console().rule(f"[yellow bold]{flag.capitalize()} snapshots")

                if (
                    flag == "update"
                    and _config.config.skip_snapshot_updates_for_now
                    and not "update" in state().flags
                ):
                    console().print(
                        f"{len(changes[flag])} updates are hidden. "
                        f"Please report why you do not want these updates so that inline-snapshot can create better snapshots in the future."
                    )
                    console().print("You can find more information about updates here:")
                    console().print(
                        link(
                            "https://15r10nk.github.io/inline-snapshot/latest/categories/#update"
                        )
                    )
                    continue

                cr = ChangeRecorder()
                apply_all(used_changes, cr)
                cr.virtual_write()
                apply_all(changes[flag], cr)

                any_changes = False

                for file in cr.files():
                    diff = file.diff()
                    if diff:
                        header()
                        name = file.filename.relative_to(Path.cwd())
                        console().print(
                            Panel(
                                Syntax(diff, "diff", theme="ansi_light"),
                                title=str(name),
                                box=(
                                    box.ASCII
                                    if os.environ.get("TERM", "") == "unknown"
                                    else box.ROUNDED
                                ),
                            )
                        )
                        any_changes = True

                if any_changes and apply_changes(flag):
                    used_changes += changes[flag]

            report_problems(console)

            if used_changes:
                cr = ChangeRecorder()
                apply_all(used_changes, cr)

                for test_file in cr.files():
                    tree = ast.parse(test_file.new_code())
                    used = used_externals(tree)

                    required_imports = []

                    if used:
                        required_imports.append("external")

                    if used_hasrepr(tree):
                        required_imports.append("HasRepr")

                    if required_imports:
                        ensure_import(
                            test_file.filename,
                            {"inline_snapshot": required_imports},
                            cr,
                        )

                    for external_name in used:
                        state().storage.persist(external_name)

                cr.fix_all()

            unused_externals = _find_external.unused_externals()

            if unused_externals and state().update_flags.trim:
                for name in unused_externals:
                    assert state().storage
                    state().storage.remove(name)
                console().print(f"removed {len(unused_externals)} unused externals\n")
        finally:
            capture.resume_global_capture()

        return
    finally:
        leave_snapshot_context()
