import ast
import os
import sys
import tokenize
from pathlib import Path
from typing import Dict
from typing import List

from executing import is_pytest_compatible
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.syntax import Syntax

from inline_snapshot._external._storage import default_storages

from . import _config
from ._change import ChangeBase
from ._change import apply_all
from ._code_repr import used_hasrepr
from ._external._external_location import ExternalLocation
from ._external._find_external import ensure_import
from ._external._find_external import used_externals_in
from ._flags import Flags
from ._global_state import state
from ._problems import raise_problem
from ._problems import report_problems
from ._rewrite_code import ChangeRecorder
from .fix_pytest_diff import fix_pytest_diff
from .pydantic_fix import pydantic_fix
from .version import is_insider

if sys.version_info >= (3, 13):
    # fixes #186
    try:
        import readline  # noqa
    except (ImportError, ModuleNotFoundError):  # pragma: no cover
        # should fix #189 and #245
        pass


categories = Flags.all().to_set()


def is_ci_run():
    if bool(os.environ.get("PYCHARM_HOSTED", False)):
        # pycharm exports TEAMCITY_VERSION but luckily also PYCHARM_HOSTED,
        # which allows to detect the incorrect ci detection
        return False

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
    return f"[italic blue link={link or text}]{text}[/]"


def category_link(category):
    return link(
        category,
        f"https://15r10nk.github.io/inline-snapshot/latest/categories/#{category}",
    )


def apply_changes(flag, console):
    if flag in state().flags:
        console().print(
            f"These changes will be applied, because you used {category_link(flag)}",
            highlight=False,
        )
        console().print()
        return True
    if "review" in state().flags:
        if is_insider and flag == "fix-assert":
            result = Confirm.ask(
                f"Do you want to {link('fix','https://15r10nk.github.io/inline-snapshot/fix_assert/')} these assertions?",
                default=False,
            )
        else:
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


def short_report(snapshot_changes, console):
    def report(flag, message, message_n):
        num = snapshot_changes[flag]

        if num and not getattr(state().update_flags, flag):
            console().print(
                message if num == 1 else message_n.format(num=num),
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


def filter_changes(changes, snapshot_changes, console):

    used_changes = []
    for flag in Flags.all():
        if not changes[flag]:
            continue

        if not {"review", "report", flag} & state().flags:
            continue

        @call_once
        def header():
            if is_insider and flag == "fix-assert":
                caption = "fix-assert"
            else:
                caption = flag.capitalize() + " snapshots"
            console().rule(f"[yellow bold]{caption}")

        if (
            flag == "update"
            and not state().config.show_updates
            and not "update" in state().flags
        ):
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
                name = file.filename.resolve().relative_to(Path.cwd().resolve())
                console().print(
                    Panel(
                        Syntax(diff, "diff", theme="ansi_light", word_wrap=True),
                        title=name.as_posix(),
                        box=(
                            box.ASCII
                            if os.environ.get("TERM", "") == "unknown"
                            else box.ROUNDED
                        ),
                    )
                )
                any_changes = True

        for change in changes[flag]:
            diff = change.rich_diff()
            if diff is not None:
                title, content = diff
                console().print(
                    Panel(
                        content,
                        title=title,
                        box=(
                            box.ASCII
                            if os.environ.get("TERM", "") == "unknown"
                            else box.ROUNDED
                        ),
                    )
                )
                any_changes = True

        if any_changes and apply_changes(flag, console):
            used_changes += changes[flag]

    return used_changes


class SnapshotSession:

    @staticmethod
    def test_enter():
        state().missing_values = 0
        state().incorrect_values = 0

    @staticmethod
    def test_exit(fail):
        missing_values = state().missing_values
        incorrect_values = state().incorrect_values

        extra = "\nIf you just created this value with --snapshot=create, the value is now created and you can ignore this message."

        if missing_values != 0:
            fail(
                (
                    "your snapshot is missing one value."
                    if missing_values == 1
                    else f"your snapshot is missing {missing_values} values."
                )
                + extra,
            )

        if incorrect_values != 0:
            fail(
                "some snapshots in this test have incorrect values." + extra,
            )

    def load_config(self, pyproject, cli_flags, parallel_run, error, project_root):

        # read config
        if pyproject is not None:
            _config.read_config(pyproject, state().config)

        if state().config.tests_dir is None:
            if (tests_dir := Path.cwd() / "tests").exists() and tests_dir.is_dir():
                state().config.tests_dir = tests_dir

        console = Console()

        if is_ci_run():
            default_flags = {"disable"}
            state().disable_reason = "ci"
        elif console.is_terminal:
            default_flags = state().config.default_flags_tui
        else:
            default_flags = state().config.default_flags

        # load flags from env var
        env_var = "INLINE_SNAPSHOT_DEFAULT_FLAGS"
        if env_var in os.environ:
            default_flags = os.environ[env_var].split(",")

        # load flags from command line argument
        if cli_flags is None:
            flags = set(default_flags)
        else:
            state().disable_reason = None
            flags = cli_flags
            if parallel_run and flags - {"disable"}:
                error(
                    f"--inline-snapshot={','.join(flags)} can not be combined with xdist"
                )

        state().flags = flags

        # check flags
        unknown_flags = (
            flags - categories - {"disable", "review", "report", "short-report"}
        )

        if unknown_flags:
            error(
                f"--inline-snapshot={','.join(sorted(unknown_flags))} is a unknown flag"
            )

        if "disable" in flags and flags != {"disable"}:
            error(
                f"--inline-snapshot=disable can not be combined with other flags ({', '.join(flags-{'disable'})})"
            )

        # disable inline-snapshot if it can not be used in the current context
        if parallel_run and "disable" not in flags:
            state().active = False
            state().disable_reason = "xdist"
        elif not is_implementation_supported() and "disable" not in flags:
            state().active = False
            state().disable_reason = "implementation"
        elif flags & {"review"}:
            state().active = True
            state().update_flags = Flags.all()
        else:
            state().active = "disable" not in flags
            state().update_flags = Flags(flags & categories)

        if state().config.storage_dir is None:
            state().config.storage_dir = project_root / ".inline-snapshot"

        state().all_storages = default_storages(state().config.storage_dir)

        if flags - {"short-report", "disable"} and not is_pytest_compatible():

            # hack to disable the assertion rewriting
            # I found no other way because the hook gets installed early
            sys.meta_path = [
                e for e in sys.meta_path if type(e).__name__ != "AssertionRewritingHook"
            ]

        self.fix_libraries()

    def fix_libraries(self):
        pydantic_fix()
        fix_pytest_diff()

    def show_report(self, con: Console):

        @call_once
        def console():
            con.print("\n")
            con.rule(
                "[blue]inline-snapshot" + (" (insider version)" if is_insider else ""),
                characters="═",
            )

            return con

        if not state().active:
            disable_info = "This means that tests with snapshots will continue to run, but snapshot(x) will only return x and inline-snapshot will not be able to fix snapshots or generate reports."
            if state().disable_reason == "xdist":
                console().print(
                    f"INFO: inline-snapshot was disabled because you used xdist. {disable_info}\n"
                )

            elif state().disable_reason == "ci":
                env_var = is_ci_run()
                console().print(
                    f'INFO: CI run was detected because environment variable "{env_var}" was defined. '
                    f"inline-snapshot runs with --inline-snapshot=disable by default in CI. {disable_info}"
                    " You can change this by using --inline-snapshot=report for example.\n"
                )

            elif state().disable_reason == "implementation":
                console().print(
                    f"INFO: inline-snapshot was disabled because {sys.implementation.name} is not supported. {disable_info}\n"
                )

            return

        # --inline-snapshot

        # auto mode
        changes: Dict[str, List[ChangeBase]] = {f: [] for f in Flags.all()}

        snapshot_changes = {f: 0 for f in Flags.all()}

        for snapshot in state().snapshots.values():
            all_categories = set()
            for change in snapshot._changes():
                changes[change.flag].append(change)
                all_categories.add(change.flag)

            for category in all_categories:
                snapshot_changes[category] += 1

        if "short-report" in state().flags:
            short_report(snapshot_changes, console)
            return

        used_changes = filter_changes(changes, snapshot_changes, console)

        cr = ChangeRecorder()
        apply_all(used_changes, cr)
        changed_files = {Path(f.filename): f for f in cr.files()}

        test_dir = state().config.tests_dir
        if not test_dir:
            raise_problem(
                "inline-snapshot can not trim your external snapshots,"
                " because there is no [i]tests/[/] folder in your repository root"
                " and no [i]test-dir[/] defined in your pyproject.toml."
            )
        else:

            all_files = {
                *map(Path, state().files_with_snapshots),
                *test_dir.rglob("*.py"),
            }

            used = []

            for file in all_files:
                if file in changed_files:
                    content = changed_files[file].new_code()
                    check_import = False
                else:
                    with tokenize.open(file) as f:
                        content = f.read()
                    check_import = True

                for e in used_externals_in(content, check_import=check_import):
                    try:
                        location = ExternalLocation.from_name(e)
                    except ValueError:
                        pass
                    else:
                        used.append(location)

            changes = {f: [] for f in Flags.all()}

            for name, storage in state().all_storages.items():
                for external_change in storage.sync_used_externals(
                    [e for e in used if e.storage == name]
                ):
                    changes[external_change.flag].append(external_change)

            used_changes += filter_changes(changes, snapshot_changes, console)

        report_problems(console)

        if used_changes:
            cr = ChangeRecorder()
            apply_all(used_changes, cr)

            for change in used_changes:
                change.apply_external_changes()

            for test_file in cr.files():
                tree = ast.parse(test_file.new_code())
                used_externals = used_externals_in(tree, check_import=False)

                required_imports = []

                if used_externals:
                    required_imports.append("external")

                if used_hasrepr(tree):
                    required_imports.append("HasRepr")

                if required_imports:
                    ensure_import(
                        test_file.filename,
                        {"inline_snapshot": required_imports},
                        cr,
                    )

            cr.fix_all()
