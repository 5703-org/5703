"""Load separately supplied private authored memory research inputs.

The runnable application does not import this module. Public distributions omit
these histories and evaluator labels; restore the approved research input bundle
to run its optional frozen studies.
"""

from copy import deepcopy
import json
from pathlib import Path

VERSION = "memory_trajectories_v2_20260921"
PRIVATE_CATALOGUE = Path(__file__).with_name("private") / "memory-catalogue.json"


def _load(key, count):
    if not PRIVATE_CATALOGUE.is_file():
        raise FileNotFoundError(
            "Private memory research inputs are unavailable. Restore the approved research bundle at evaluation/memory_v2/private/memory-catalogue.json."
        )
    value = json.loads(PRIVATE_CATALOGUE.read_text(encoding="utf-8"))
    rows = value.get(key)
    if (
        value.get("version") != VERSION
        or not isinstance(rows, list)
        or len(rows) != count
        or len({row["id"] for row in rows}) != count
    ):
        raise ValueError("Private memory research inventory differs from its registered version")
    return deepcopy(rows)


def trajectories():
    return _load("trajectories", 12)


def extraction_cases():
    return _load("extraction_cases", 24)


def gating_pairs():
    return _load("gating_pairs", 12)
