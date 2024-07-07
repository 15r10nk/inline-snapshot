from inline_snapshot._code_repr import HasRepr


def test_hasrepr_eq():

    assert float("nan") == HasRepr(float, "nan")

    class Thing:
        def __repr__(self):
            return "<something>"

    assert Thing() == HasRepr(Thing, "<something>")
