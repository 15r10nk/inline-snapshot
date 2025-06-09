from inline_snapshot._external._external_location import ExternalLocation
from inline_snapshot._inline_snapshot import snapshot


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
                storage="hash", stem=None, suffix=None, filename=None, qualname=None
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
                storage="uuid", stem=None, suffix=None, filename=None, qualname=None
            ),
        }
    )

    for h in ("hash:", ""):
        for n in ("a", ""):
            for s in (".txt", ".b.txt", ""):
                name = h + n + s
                try:
                    assert ExternalLocation.from_name(name) == results[name]
                except Exception as e:
                    assert results[name] == f"{type(e).__name__}: {e}"
