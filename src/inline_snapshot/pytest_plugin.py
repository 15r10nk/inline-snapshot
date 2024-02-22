import argparse
from pathlib import Path

import pytest

from . import _config
from . import _external
from . import _find_external
from . import _inline_snapshot
from ._find_external import ensure_import
from ._inline_snapshot import undefined
from ._rewrite_code import ChangeRecorder


def pytest_addoption(parser):
    group = parser.getgroup("inline-snapshot")

    group.addoption(
        "--inline-snapshot",
        metavar="(create,update,trim,fix)*",
        default="",
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

    # deprecated option
    group.addoption(
        "--update-snapshots",
        action="store",
        dest="inline_snapshot_deprecated",
        default="none",
        choices=("all", "failing", "new", "none"),
        help=argparse.SUPPRESS,
    )


def pytest_configure(config):
    flags = config.option.inline_snapshot.split(",")
    flags = [flag for flag in flags if flag]

    if config.option.inline_snapshot_disable and flags:
        raise pytest.UsageError(
            f"--inline-snapshot-disable can not be combined with other flags ({','.join(flags)})"
        )

    _inline_snapshot._active = not config.option.inline_snapshot_disable

    _inline_snapshot._update_flags = _inline_snapshot.Flags(set(flags))

    old_flag = config.option.inline_snapshot_deprecated

    snapshot_path = Path(config.rootpath) / ".inline-snapshot/external"
    _external.storage = _external.DiscStorage(snapshot_path)

    _config.config = _config.read_config(config.rootpath / "pyproject.toml")

    if old_flag != "none":
        msg_prefix = f"--update-snapshots={old_flag} is deprecated, please use "

        if _inline_snapshot._update_flags.change_something():
            raise pytest.UsageError(msg_prefix + "only --inline-snapshot")

        elif old_flag == "failing":
            raise pytest.UsageError(msg_prefix + "--inline-snapshot=fix")

        elif old_flag == "new":
            raise pytest.UsageError(msg_prefix + "--inline-snapshot=create")

        elif old_flag == "all":
            raise pytest.UsageError(msg_prefix + "--inline-snapshot=create,fix")
        else:
            assert False

    if _inline_snapshot._update_flags.change_something():
        import sys

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

    recorder = ChangeRecorder.current

    terminalreporter.section("inline snapshot")

    unused_externals = _find_external.unused_externals()

    def report(flag, message):
        num = sum(
            1
            for snapshot in _inline_snapshot.snapshots.values()
            if flag in snapshot._flags
        )

        if flag == "trim":
            num += len(unused_externals)

        if num and not getattr(_inline_snapshot._update_flags, flag):
            terminalreporter.write(message.format(num=num) + "\n")

    if exitstatus != 0:
        report(
            "fix",
            "Error: {num} snapshots have incorrect values (--inline-snapshot=fix)",
        )

    report("trim", "Info: {num} snapshots can be trimmed (--inline-snapshot=trim)")

    report(
        "create",
        "Error: {num} snapshots are missing values (--inline-snapshot=create)",
    )

    report(
        "update",
        "Info: {num} snapshots changed their representation (--inline-snapshot=update)",
    )

    if _inline_snapshot._update_flags.change_something():
        count = {"create": 0, "fix": 0, "trim": 0, "update": 0}

        for snapshot in _inline_snapshot.snapshots.values():
            for flag in snapshot._flags:
                assert flag in ("create", "fix", "trim", "update"), flag
                count[flag] += 1
            snapshot._change()

        ensure_external = set()
        for snapshot in _inline_snapshot.snapshots.values():
            if snapshot._uses_externals:
                ensure_external.add(snapshot._filename)

            for external_name in snapshot._uses_externals:
                _external.storage.persist(external_name)

        for filename in ensure_external:
            ensure_import(filename, {"inline_snapshot": ["external"]})

        recorder.fix_all()

        def report_change(flags, msg):
            if count[flags]:
                terminalreporter.write(msg.format(num=count[flags]) + "\n")

        report_change("create", "defined values for {num} snapshots")
        report_change("fix", "fixed {num} snapshots")
        report_change("trim", "trimmed {num} snapshots")

        # update does not work currently, because executing has limitations with pytest
        report_change("update", "updated {num} snapshots")

        if unused_externals and _inline_snapshot._update_flags.trim:
            for name in unused_externals:
                assert _external.storage
                _external.storage.remove(name)
            terminalreporter.write(
                f"removed {len(unused_externals)} unused externals\n"
            )
