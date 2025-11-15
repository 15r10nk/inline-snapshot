"""Tests for the factory adapter handling."""

from collections import defaultdict

from inline_snapshot import snapshot


def test_factory_adapter_defaultdict():
    """Test that factory functions in defaultdict are handled correctly."""
    d = defaultdict(list)
    d["test"].append(1)
    d["other"].append(2)
    snapshot(d) == defaultdict(list, {"test": [1], "other": [2]})


def test_factory_adapter_subclass():
    """Test that custom factory functions are handled correctly."""

    class CustomFactory:
        def __call__(self):
            return 42

    d = defaultdict(CustomFactory())
    d["test"]  # Access to trigger factory
    snapshot(d) == defaultdict(CustomFactory(), {"test": 42})


def test_factory_adapter_lambda():
    """Test that lambda factory functions are handled correctly."""
    d = defaultdict(lambda: "default")
    d["test"]  # Access to trigger factory
    snapshot(d) == defaultdict(lambda: "default", {"test": "default"})


def test_factory_adapter_builtin_types():
    """Test that builtin type factories are handled correctly."""
    for factory in (list, dict, set, str, int, float):
        d = defaultdict(factory)
        d["test"]  # Access to trigger factory
        snapshot(d) == defaultdict(factory, {"test": factory()})
