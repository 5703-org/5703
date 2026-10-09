"""Lazy access to the preserved evaluator-only September 20 formal catalogue.

The public application and software tests do not need this private research
asset. Restore the exact private catalogue to prepare or replay the study;
there is deliberately no development-fixture fallback.
"""

import hashlib
import json
from pathlib import Path


CATALOGUE_PATH = Path(__file__).with_name("private") / "formal-catalogue.json"
CATALOGUE_SHA256 = "dd3e10cac2dbac595e75afa4dd7775d046f348ce0d7432ff952066e66d00ea0f"


def formal_tasks(path: Path | None = None):
    source = path if path is not None else CATALOGUE_PATH
    if not source.is_file():
        raise ValueError(
            "Restore the private September 20 formal catalogue before preparing a study"
        )
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != CATALOGUE_SHA256:
        raise ValueError("Private formal catalogue differs from the preserved source identity")
    payload = json.loads(raw)
    if payload.get("schema") != "enhancement_formal_catalogue_private_v1":
        raise ValueError("Unsupported private formal catalogue version")
    rows = payload["tasks"]
    if len(rows) != 60 or len({row["id"] for row in rows}) != 60:
        raise ValueError("Private formal catalogue must retain all 60 distinct tasks")
    return rows
