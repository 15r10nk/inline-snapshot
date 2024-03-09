from inline_snapshot import snapshot


def test_fix_list(check_update):
    assert check_update(
        """assert [1,2]==snapshot([0+1,3])""", reported_flags="update,fix", flags="fix"
    ) == snapshot("""assert [1,2]==snapshot([0+1,2])""")


def test_fix_dict_change(check_update):
    assert check_update(
        """assert {1:1, 2:2}==snapshot({1:0+1, 2:3})""",
        reported_flags="update,fix",
        flags="fix",
    ) == snapshot("""assert {1:1, 2:2}==snapshot({1:0+1, 2:2})""")


def test_fix_dict_remove(check_update):
    assert check_update(
        """assert {1:1}==snapshot({0:0, 1:0+1, 2:2})""",
        reported_flags="update,fix",
        flags="fix",
    ) == snapshot("assert {1:1}==snapshot({ 1:0+1})")

    assert check_update(
        """assert {}==snapshot({0:0})""",
        reported_flags="fix",
        flags="fix",
    ) == snapshot("assert {}==snapshot({})")
