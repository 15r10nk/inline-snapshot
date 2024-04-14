import ast
import sys
from pathlib import Path

import pytest
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Confirm

from . import _config
from . import _external
from . import _find_external
from . import _inline_snapshot
from ._change import apply_all
from ._find_external import ensure_import
from ._inline_snapshot import undefined
from ._inline_snapshot import used_externals
from ._rewrite_code import ChangeRecorder


def pytest_addoption(parser):
    group = parser.getgroup("inline-snapshot")

    group.addoption(
        "--inline-snapshot",
        metavar="(create,update,trim,fix)*",
        default="",
        nargs="?",
        dest="inline_snapshot",
        help="update specific snapshot values:\n"
        "create: creates snapshots which are currently not defined\n"
        "update: update snapshots even if they are defined\n"
        "trim: changes the snapshot in a way which will make the snapshot more precise.\n"
        "fix: change snapshots which currently break your tests\n",
    )

    group.addoption(
        "--inline-snapshot-disable",
        action="store_true",
        dest="inline_snapshot_disable",
        help="disable snapshot logic",
    )


def pytest_configure(config):
    if config.option.inline_snapshot is None:
        _inline_snapshot._active = True
        if config.option.inline_snapshot_disable:
            raise pytest.UsageError(
                f"--inline-snapshot-disable can not be combined with --inline-snapshot"
            )

        _inline_snapshot._update_flags = _inline_snapshot.Flags(
            {"fix", "create", "update", "trim"}
        )
    else:
        flags = config.option.inline_snapshot.split(",")
        flags = [flag for flag in flags if flag]

        if config.option.inline_snapshot_disable and flags:
            raise pytest.UsageError(
                f"--inline-snapshot-disable can not be combined with other flags ({','.join(flags)})"
            )

        _inline_snapshot._active = not config.option.inline_snapshot_disable

        _inline_snapshot._update_flags = _inline_snapshot.Flags(set(flags))

    snapshot_path = Path(config.rootpath) / ".inline-snapshot/external"

    _external.storage = _external.DiscStorage(snapshot_path)

    _config.config = _config.read_config(config.rootpath / "pyproject.toml")

    if config.option.inline_snapshot != "":

        # hack to disable the assertion rewriting
        # I found no other way because the hook gets installed early
        sys.meta_path = [
            e for e in sys.meta_path if type(e).__name__ != "AssertionRewritingHook"
        ]

    _external.storage.prune_new_files()


@pytest.fixture(autouse=True)
def snapshot_check():
    found = _inline_snapshot.found_snapshots = []
    yield
    missing_values = sum(snapshot._value._old_value is undefined for snapshot in found)
    if missing_values and not _inline_snapshot._update_flags.create:
        pytest.fail(
            "your snapshot is missing a value run pytest with --inline-snapshot=create to create the value",
            pytrace=False,
        )


def pytest_assertrepr_compare(config, op, left, right):
    results = []
    if isinstance(left, _inline_snapshot.GenericValue):
        results = config.hook.pytest_assertrepr_compare(
            config=config, op=op, left=left._visible_value(), right=right
        )

    if isinstance(right, _inline_snapshot.GenericValue):
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


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    if not _inline_snapshot._active:
        return

    terminalreporter.section("inline snapshot")

    capture = config.pluginmanager.getplugin("capturemanager")

    if config.option.inline_snapshot is None:
        # --inline-snapshot

        def apply_changes(flag):
            return Confirm.ask(
                f"[bold]do you want to [blue]{flag}[/] these snapshots?[/]",
                default=False,
            )

    else:

        def apply_changes(flag):
            if flag in _inline_snapshot._update_flags.to_set():
                console.print(
                    f"These changes will be applied, because you used [b]--inline-snapshot={flag}[/]",
                    highlight=False,
                )
                return True
            else:
                console.print(f"These changes are not applied.")
                console.print(
                    f"Use [b]--inline-snapshot={flag}[/] to apply theme, or use the interactive mode with --inline-snapshot",
                    highlight=False,
                )
                return False

    # auto mode
    changes = {
        "update": [],
        "fix": [],
        "trim": [],
        "create": [],
    }

    snapshot_changes = {
        "update": 0,
        "fix": 0,
        "trim": 0,
        "create": 0,
    }

    for snapshot in _inline_snapshot.snapshots.values():
        all_categories = set()
        for change in snapshot._changes():
            changes[change.flag].append(change)
            all_categories.add(change.flag)

        for category in all_categories:
            snapshot_changes[category] += 1

    capture.suspend_global_capture(in_=True)
    try:
        console = Console()
        if config.option.inline_snapshot == "":

            def report(flag, message):

                if snapshot_changes[flag] and not getattr(
                    _inline_snapshot._update_flags, flag
                ):
                    console.print(
                        message.format(num=snapshot_changes[flag]) + "\n",
                        highlight=False,
                    )

            report(
                "fix",
                "Error: {num} snapshots have incorrect values ([b]--inline-snapshot=fix[/])",
            )

            report(
                "trim",
                "Info: {num} snapshots can be trimmed ([b]--inline-snapshot=trim[/])",
            )

            report(
                "create",
                "Error: {num} snapshots are missing values ([b]--inline-snapshot=create[/])",
            )

            report(
                "update",
                "Info: {num} snapshots changed their representation ([b]--inline-snapshot=update[/])",
            )
            return

        assert not any(
            type(e).__name__ == "AssertionRewritingHook" for e in sys.meta_path
        )

        used_changes = []
        for flag in ("create", "fix", "trim", "update"):
            if not changes[flag]:
                continue

            console.rule(f"[yellow bold]{flag.capitalize()} snapshots")

            with ChangeRecorder().activate() as cr:
                apply_all(used_changes)
                cr.virtual_write()
                apply_all(changes[flag])

                for file in cr.files():
                    diff = file.diff()
                    if diff:
                        console.print()
                        name = file.filename.relative_to(Path.cwd())
                        console.print(f"[green]{name}:")
                        console.print(Markdown(f"```diff\n{diff}\n```"))

                if apply_changes(flag):
                    used_changes += changes[flag]

        if used_changes:
            with ChangeRecorder().activate() as cr:
                apply_all(used_changes)

                for test_file in cr.files():
                    tree = ast.parse(test_file.new_code())
                    used = used_externals(tree)

                    if used:
                        ensure_import(
                            test_file.filename, {"inline_snapshot": ["external"]}
                        )

                    for external_name in used:
                        _external.storage.persist(external_name)

                cr.fix_all()

        unused_externals = _find_external.unused_externals()

        if unused_externals and _inline_snapshot._update_flags.trim:
            for name in unused_externals:
                assert _external.storage
                _external.storage.remove(name)
            terminalreporter.write(
                f"removed {len(unused_externals)} unused externals\n"
            )

    finally:
        capture.resume_global_capture()

    return
