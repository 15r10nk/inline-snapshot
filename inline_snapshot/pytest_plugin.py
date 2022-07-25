from . import _inline_snapshot
from ._rewrite_code import ChangeRecorder


def pytest_addoption(parser):
    group = parser.getgroup("inline-snapshot")
    group.addoption(
        "--update-snapshots",
        action="store",
        dest="inline_snapshot_kind",
        default="none",
        choices=("all", "failing", "new", "none"),
        help="update snapshot arguments in source code:\n [force] incorrect and correct snapshots\n [failing] incorrect snapshots\n [new] snapshots without a value",
    )

    # TODO --snapshots-value-required ... fail if there are pending updates


def pytest_configure(config):

    if config.option.inline_snapshot_kind == "failing":
        _inline_snapshot._ignore_value = True

    if config.option.inline_snapshot_kind != "none":
        _inline_snapshot._active = True

        import sys

        # hack to disable the assertion rewriting
        # I found no other way because the hook gets installed early
        sys.meta_path = [
            e for e in sys.meta_path if type(e).__name__ != "AssertionRewritingHook"
        ]


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    recorder = ChangeRecorder.current

    terminalreporter.section("inline snapshot")
    if exitstatus != 0:
        failing = sum(
            1
            for snapshot in _inline_snapshot.snapshots.values()
            if snapshot._reason == "failing"
        )

        if failing:
            terminalreporter.write(
                f"{failing} snapshots are causing problems (--update-snapshots=failing)\n"
            )

    new = sum(
        1
        for snapshot in _inline_snapshot.snapshots.values()
        if snapshot._reason == "new"
    )

    if new:
        terminalreporter.write(
            f"{new} snapshots are missing values (--update-snapshots=new)\n"
        )

    fix_reason = config.option.inline_snapshot_kind

    if fix_reason != "none":

        new = 0
        failing = 0

        for snapshot in _inline_snapshot.snapshots.values():
            if snapshot._reason == "new" == fix_reason:
                new += 1
                snapshot._change()
            elif snapshot._reason == "failing" == fix_reason:
                failing += 1
                snapshot._change()

        recorder.fix_all()
        if new:
            terminalreporter.write(f"defined values for {new} snapshots\n")
        if failing:
            terminalreporter.write(f"fixed {failing} snapshots\n")
