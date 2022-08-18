from . import _inline_snapshot
from ._rewrite_code import ChangeRecorder


def pytest_addoption(parser):
    group = parser.getgroup("inline-snapshot")

    group.addoption(
        "--inline-snapshot-create",
        action="store_true",
        dest="inline_snapshot_create",
        help="record missing snapshot values",
    )

    group.addoption(
        "--inline-snapshot-recreate",
        action="store_true",
        dest="inline_snapshot_recreate",
        help="recreate all snapshot values",
    )

    group.addoption(
        "--inline-snapshot-fix",
        action="store_true",
        dest="inline_snapshot_fix",
        help="fix snapshots which have incorrect values",
    )

    group.addoption(
        "--inline-snapshot-fit",
        action="store_true",
        dest="inline_snapshot_fit",
        help="reduce snapshots to the minimal required value (affects '<=', '>=' and 'in')",
    )

    group.addoption(
        "--inline-snapshot-disable",
        action="store_true",
        dest="inline_snapshot_disable",
        help="snapshot(x) will just return x",
    )


def pytest_configure(config):

    _inline_snapshot._active = not config.option.inline_snapshot_disable
    _inline_snapshot._update_reasons = set()

    if config.option.inline_snapshot_create:
        _inline_snapshot._update_reasons.add("new")

    if config.option.inline_snapshot_fix:
        _inline_snapshot._update_reasons.add("failing")

    if config.option.inline_snapshot_fit:
        _inline_snapshot._update_reasons.add("fit")

    if config.option.inline_snapshot_recreate:
        _inline_snapshot._update_reasons.add("recreate")

    fix_something = (
        config.option.inline_snapshot_fix
        or config.option.inline_snapshot_create
        or config.option.inline_snapshot_recreate
        or config.option.inline_snapshot_fit
    )

    if fix_something:
        import sys

        # hack to disable the assertion rewriting
        # I found no other way because the hook gets installed early
        sys.meta_path = [
            e for e in sys.meta_path if type(e).__name__ != "AssertionRewritingHook"
        ]


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    if config.option.inline_snapshot_disable:
        return

    recorder = ChangeRecorder.current

    terminalreporter.section("inline snapshot")

    def report(reason, message):
        num = sum(
            1
            for snapshot in _inline_snapshot.snapshots.values()
            if reason in snapshot._reason
        )

        if num:
            terminalreporter.write(message.format(num=num))

    if exitstatus != 0:
        report(
            "failing", "{num} snapshots are causing problems (--inline-snapshot-fix)\n"
        )

    report("new", "{num} snapshots are missing values (--inline-snapshot-create)\n")

    report("fit", "{num} snapshots can be reduced (--inline-snapshot-fit)\n")

    fix_reasons = []
    if config.option.inline_snapshot_create:
        fix_reasons.append("new")

    if config.option.inline_snapshot_fix:
        fix_reasons.append("fix")

    if config.option.inline_snapshot_fit:
        fix_reasons.append("fit")

    if fix_reasons:

        count = {"new": 0, "failing": 0, "fit": 0}

        for snapshot in _inline_snapshot.snapshots.values():
            for r in snapshot._reason:
                assert r in ("new", "fix", "fit")
                count[r] += 1
                snapshot._change()

        recorder.fix_all()

        def report(reason, msg):
            if count[reason]:
                terminalreporter.write(msg.format(num=count[reason]))

        report("new", "defined values for {num} snapshots\n")
        report("failing", "fixed {num} snapshots\n")
        report("fit", "fitted {num} snapshots\n")
