from inline_snapshot._external._external_location import ExternalLocation
from inline_snapshot._inline_snapshot import snapshot
from inline_snapshot.testing._example import Example


def test_external_location():

    results = snapshot(
        {
            "hash:a.txt": ExternalLocation(
                storage="hash", stem="a", suffix=".txt", filename=None, qualname=None
            ),
            "hash:a.b.txt": ExternalLocation(
                storage="hash", stem="a", suffix=".b.txt", filename=None, qualname=None
            ),
            "hash:a": "ValueError: 'hash:a' is missing a suffix",
            "hash:.txt": ExternalLocation(
                storage="hash", stem="", suffix=".txt", filename=None, qualname=None
            ),
            "hash:.b.txt": ExternalLocation(
                storage="hash", stem="", suffix=".b.txt", filename=None, qualname=None
            ),
            "hash:": ExternalLocation(
                storage="hash", stem="", suffix="", filename=None, qualname=None
            ),
            "a.txt": ExternalLocation(
                storage="uuid", stem="a", suffix=".txt", filename=None, qualname=None
            ),
            "a.b.txt": ExternalLocation(
                storage="uuid", stem="a", suffix=".b.txt", filename=None, qualname=None
            ),
            "a": "ValueError: 'a' is missing a suffix",
            ".txt": ExternalLocation(
                storage="uuid", stem="", suffix=".txt", filename=None, qualname=None
            ),
            ".b.txt": ExternalLocation(
                storage="uuid", stem="", suffix=".b.txt", filename=None, qualname=None
            ),
            """""": ExternalLocation(
                storage="uuid", stem="", suffix="", filename=None, qualname=None
            ),
            "invalid:a.txt": "ValueError: storage has to be hash or uuid",
            "invalid:a.b.txt": "ValueError: storage has to be hash or uuid",
            "invalid:a": "ValueError: storage has to be hash or uuid",
            "invalid:.txt": "ValueError: storage has to be hash or uuid",
            "invalid:.b.txt": "ValueError: storage has to be hash or uuid",
            "invalid:": "ValueError: storage has to be hash or uuid",
        }
    )

    for h in ("hash:", "invalid:", ""):
        for n in ("a", ""):
            for s in (".txt", ".b.txt", ""):
                name = h + n + s
                try:
                    assert ExternalLocation.from_name(name) == results[name]
                except Exception as e:
                    assert results[name] == f"{type(e).__name__}: {e}"


def test_missing_suffix():
    Example(
        """
from inline_snapshot import external

def test_a():
    if False:
        assert "a" == external("a")
    else:
        assert "a" == external(".txt")
    """
    ).run_pytest(
        ["--inline-snapshot=create"],
        changed_files=snapshot(
            {
                "tests/__inline_snapshot__/test_something/test_a/e3e70682-c209-4cac-a29f-6fbed82c07cd.txt": "a",
                "tests/test_something.py": """\

from inline_snapshot import external

def test_a():
    if False:
        assert "a" == external("a")
    else:
        assert "a" == external("uuid:e3e70682-c209-4cac-a29f-6fbed82c07cd.txt")
    \
""",
            }
        ),
        returncode=1,
    )
