import gc
import weakref

from inline_snapshot import Is
from inline_snapshot import snapshot_arg
from inline_snapshot._global_state import snapshot_env
from inline_snapshot.testing import Example


def test_unmanaged_snapshot_arg_does_not_retain_context():
    class Payload:
        pass

    def check(actual, expected):
        payload = Payload()
        payload_ref = weakref.ref(payload)
        value = snapshot_arg(expected)
        context_ref = weakref.ref(value._context)
        assert actual == value
        return payload_ref, context_ref

    with snapshot_env():
        payload_ref, context_ref = check(1, Is(1))
        gc.collect()

        assert payload_ref() is None
        assert context_ref() is None


def test_unmanaged_snapshot_arg_is_materialized_immediately():
    Example("""\
from inline_snapshot import Is
from inline_snapshot import snapshot_arg

def check(actual, expected):
    assert actual == snapshot_arg(expected)

def test_a():
    for value in (1, 2):
        check(value, Is(value))
""").run_inline(reported_categories=set())
