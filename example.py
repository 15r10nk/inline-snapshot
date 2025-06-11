from inline_snapshot import external
from inline_snapshot import register_format_alias

register_format_alias(".html", ".txt")


def test2():
    assert "<html></html>" == external("uuid:88055e4a-968d-4cdf-b593-2b14d7cadccd.txt")
