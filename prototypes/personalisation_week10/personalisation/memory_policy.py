"""Shared bounded loading of the explicitly configured memory-selection policy."""

import json
from pathlib import Path

from .memory_v2 import MemoryPreparationUnavailable
from . import memory_v3, memory_v4, memory_v5


def selector_for_policy(value):
    if isinstance(value, dict) and value.get("version") == memory_v5.POLICY_VERSION:
        memory_v5.validate_policy(value)
        return memory_v5
    if isinstance(value, dict) and value.get("version") == memory_v4.POLICY_VERSION:
        memory_v4.validate_policy(value)
        return memory_v4
    memory_v3.validate_policy(value)
    return memory_v3


MAX_POLICY_BYTES = 64 * 1024


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate memory policy key")
        value[key] = item
    return value


def _reject_constant(value):
    raise ValueError("Non-finite memory policy number")


def load_policy(path=None):
    """Default to semantic off; invalid configured files stay unavailable."""
    if not path:
        return memory_v5.freeze_policy()
    try:
        # Bound the actual read, including a file that grows after it is opened.
        with Path(path).open("rb") as stream:
            raw = stream.read(MAX_POLICY_BYTES + 1)
        if len(raw) > MAX_POLICY_BYTES:
            raise ValueError("Oversized memory policy")
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
        if not isinstance(value, dict):
            raise ValueError("Memory policy file must contain an object")
        return selector_for_policy(value).validate_policy(value)
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        raise MemoryPreparationUnavailable("MEMORY_POLICY_UNAVAILABLE") from exc
