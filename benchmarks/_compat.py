"""Support benchmarking revisions before and after the core package move."""

from importlib import import_module
from importlib.util import find_spec


def global_state_module():
    if find_spec("inline_snapshot._core") is not None:
        return "inline_snapshot._core._global_state"
    return "inline_snapshot._global_state"


def snapshot_env():
    return import_module(global_state_module()).snapshot_env()
