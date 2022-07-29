from . import _inline_snapshot
from ._rewrite_code import ChangeRecorder


def pytest_addoption(parser):
    group = parser.getgroup("inline-snapshot")

    group.addoption(
        "--inline-snapshot-create",
        action="store_true",
        dest="inline_snapshot_create",
        help="record the snapshots where they are missing",
    )

    group.addoption(
        "--inline-snapshot-fix",
        action="store_true",
        dest="inline_snapshot_fix",
        help="fix snapshots which have incorrect values",
    )

    group.addoption(
        "--inline-snapshot-shrink",
        action="store_true",
        dest="inline_snapshot_shrink",
        help="shrink snapshots if possible",
    )

    group.addoption(
        "--inline-snapshot-report",
        action="store_true",
        dest="inline_snapshot_report",
        help="creates a report for all snapshots",
    )


def pytest_configure(config):

    if (
        config.option.inline_snapshot_fix
        or config.option.inline_snapshot_create
        or config.option.inline_snapshot_shrink
    ):
        config.option.inline_snapshot_report = True

    if config.option.inline_snapshot_report:
        _inline_snapshot._active = True

        import sys

        # hack to disable the assertion rewriting
        # I found no other way because the hook gets installed early
        sys.meta_path = [
            e for e in sys.meta_path if type(e).__name__ != "AssertionRewritingHook"
        ]


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    if not config.option.inline_snapshot_report:
        return

    recorder = ChangeRecorder.current

    terminalreporter.section("inline snapshot")

    def report(reason, message):
        num = sum(
            1
            for snapshot in _inline_snapshot.snapshots.values()
            if snapshot._reason == reason
        )

        if num:
            terminalreporter.write(message.format(num=num))

    if exitstatus != 0:
        report(
            "failing", "{num} snapshots are causing problems (--inline-snapshot-fix)\n"
        )

    report("new", "{num} snapshots are missing values (--inline-snapshot-create)\n")

    report("shrink", "{num} snapshots can be reduced (--inline-snapshot-shrink)\n")

    fix_reasons = []
    if config.option.inline_snapshot_create:
        fix_reasons.append("new")

    if config.option.inline_snapshot_fix:
        fix_reasons.append("failing")

    if config.option.inline_snapshot_shrink:
        fix_reasons.append("shrink")

    if fix_reasons:

        count = {"new": 0, "failing": 0, "shrink": 0}

        for snapshot in _inline_snapshot.snapshots.values():
            for r in ("new", "failing", "shrink"):
                if snapshot._reason == r in fix_reasons:
                    count[r] += 1
                    snapshot._change()

        recorder.fix_all()

        def report(reason, msg):
            if count[reason]:
                terminalreporter.write(msg.format(num=count[reason]))

        report("new", "defined values for {num} snapshots\n")
        report("failing", "fixed {num} snapshots\n")
        report("shrink", "shrinked {num} snapshots\n")
