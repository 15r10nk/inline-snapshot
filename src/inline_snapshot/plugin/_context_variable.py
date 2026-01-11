from dataclasses import dataclass
from typing import Any


@dataclass
class ContextVariable:
    """
    Representation of a value in the local or global context of a snapshot.

    This type can be returned from a customize function to reference an existing variable
    instead of creating a new literal value. Inline-snapshot includes a built-in handler
    that converts ContextVariable instances into [Custom][inline_snapshot.plugin.Custom]
    objects, generating code that references the variable by name.

    ContextVariable instances are provided via the `local_vars` and `global_vars` parameters
    of the [customize hook][inline_snapshot.plugin.InlineSnapshotPluginSpec.customize].
    """

    name: str
    "the name of the variable"

    value: Any
    "the value of the variable"
