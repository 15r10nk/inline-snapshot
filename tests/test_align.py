from inline_snapshot import snapshot
from inline_snapshot._align import add_x
from inline_snapshot._align import align


def test_align():
    assert align("iabc", "abcd") == snapshot("dmmmi")

    assert align("abbc", "axyc") == snapshot("mddiim")
    assert add_x(align("abbc", "axyc")) == snapshot("mxxm")
