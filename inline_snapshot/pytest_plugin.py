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


def pytest_load_initial_conftests(args):
    if any(arg.startswith("--update-snapshots=") for arg in args):
        # executing has problems with assert rewriting
        args.append("--assert=plain")

    print("args:", args)


def pytest_cmdline_parse(pluginmanager, args):
    if any(arg.startswith("--update-snapshots=") for arg in args):
        # executing has problems with assert rewriting
        args.append("--assert=plain")

    print("args2:", args)


def pytest_cmdline_preparse(config, args):
    if any(arg.startswith("--update-snapshots=") for arg in args):
        # executing has problems with assert rewriting
        args.append("--assert=plain")

    print("args3:", args)


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    recorder = ChangeRecorder.current

    # plugin = config.pluginmanager.getplugin("_codecrumbs")
    # print(config.option.inline_snapshot_kind)

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

    terminalreporter.write(
        f"{new} snapshots are missing values (--update-snapshots=new)\n"
    )

    fix_reason = config.option.inline_snapshot_kind

    if fix_reason != "none":
        print("fix stuff")

        new = 0
        failing = 0

        for snapshot in _inline_snapshot.snapshots.values():
            print(snapshot._current_value, snapshot._new_value)
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
