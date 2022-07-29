from inline_snapshot._inline_snapshot import snapshots_disabled


def new_test(source, failing=0, new=0, usage_error=0, shrink=0):
    def w(pytester):
        testdir = pytester

        code = f"""
            from inline_snapshot import snapshot
            def test_something():
                {source}
        """
        print("code:")
        print(code)
        print(f"reason: failing={failing} new={new} shrink={shrink}")

        # create a temporary pytest test module
        testdir.makepyfile(test_file=code)

        # test errors
        print("pytest output:")
        with snapshots_disabled():
            result = testdir.runpytest_subprocess("-v")

        print("pytest result:", result.ret)

        assert (result.ret != 0) == (failing or new or usage_error)

        if new:
            result.stdout.fnmatch_lines(
                [
                    "*AssertionError: your snapshot is missing a value run pytest with --inline-snapshot-create"
                ]
            )

        # test code fixes
        if new:
            with snapshots_disabled():
                result = testdir.runpytest_subprocess("--inline-snapshot-create", "-v")

            result.stdout.fnmatch_lines(
                [
                    f"defined values for {new} snapshots",
                ]
            )
            assert (result.ret == 0) == (not (failing or usage_error))

        if failing:
            testdir.plugins = ["inline_snapshot"]
            result = testdir.runpytest_subprocess("--inline-snapshot-fix", "-v")

            result.stdout.fnmatch_lines(
                [
                    f"fixed {failing} snapshots",
                ]
            )
            assert (result.ret == 0) == (not usage_error)

        if usage_error:
            # nothing helps when you did something wrong
            with snapshots_disabled():
                result = testdir.runpytest_subprocess("--update-snapshots=all", "-v")
            with snapshots_disabled():
                result = testdir.runpytest_subprocess("-v")
            assert result.ret != 0

    return w


test_1 = new_test("assert 5 == snapshot(5)")
test_2 = new_test("assert 3 == snapshot(5)", failing=1)
test_3 = new_test("assert 3 == snapshot()", new=1)
test_4 = new_test("for e in (1,2,3): assert e == snapshot()", usage_error=1)


def test_help_message(testdir):
    result = testdir.runpytest(
        "--help",
    )
    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines(
        [
            "inline-snapshot:",
            "*--inline-snapshot-report*",
        ]
    )
