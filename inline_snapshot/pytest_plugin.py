from ._rewrite_code import ChangeRecorder


def pytest_addoption(parser):
    group = parser.getgroup("inline-snapshot")
    group.addoption(
        "--update-snapshot",
        action="store",
        dest="inline_snapshot_kind",
        default="new",
        choices=("force", "failing", "new"),
        help="update snapshot arguments in source code:\n [force] incorrect and correct snapshots\n [failing] incorrect snapshots\n [new] snapshots without a value",
    )

    # TODO --fail-updates ... fail if there are pending updates


def pytest_load_initial_conftests(args):
    if any(arg.startswith("--update-snapshot=") for arg in args):
        # executing has problems with assert rewriting
        args.append("--assert=plain")


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    recorder = ChangeRecorder.current

    # plugin = config.pluginmanager.getplugin("_codecrumbs")

    if exitstatus == 0 and config.option.inline_snapshot_kind:

        num_fixes = recorder.num_fixes()
        recorder.fix_all()
        terminalreporter.section("inline snapshot")
        terminalreporter.write(f"{num_fixes} snapshots where fixed\n")
