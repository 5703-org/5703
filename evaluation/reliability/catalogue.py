"""Lazy access to preserved research cases, separate from public software tests.

The original source, all reference labels and all four historical frozen plans
remain in the private research asset. Importing this module never loads them.
"""

import hashlib
import json
from pathlib import Path


CATALOGUE_PATH = Path(__file__).with_name("private") / "catalogue.json"
CATALOGUE_SHA256 = "274d70cb0c34a5b79712490773d84e4bcf1fde88fbc28d1fafdd8c7d0780c3b0"


def inventory(path: Path | None = None):
    source = path if path is not None else CATALOGUE_PATH
    if not source.is_file():
        raise ValueError(
            "Restore the private September 16 reliability catalogue before preparing a study"
        )
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != CATALOGUE_SHA256:
        raise ValueError("Private reliability catalogue differs from the preserved source identity")
    payload = json.loads(raw)
    if payload.get("schema") != "reliability_catalogue_private_v1":
        raise ValueError("Unsupported private reliability catalogue version")
    value = payload["catalogue"]
    if len(value["cases"]) != 120 or len({r["id"] for r in value["cases"]}) != 120:
        raise ValueError("Private reliability catalogue must retain all 120 distinct cases")
    if len(value["topics"]) != 30:
        raise ValueError("Private reliability catalogue must retain all 30 source topics")
    return value


def cases(path: Path | None = None):
    return inventory(path)["cases"]


def __getattr__(name):
    """Preserve explicit research imports without eager private reads."""
    if name == "TOPICS":
        return [tuple(row) for row in inventory()["topics"]]
    if name in {"SECTIONS", "OUTSIDE"}:
        return inventory()[name.lower()]
    raise AttributeError(name)


def validate_frozen_plan(plan):
    """Verify research plan invariants; also exercised with public synthetic data."""
    rows, sources = plan["cases"], plan["source_topics"]
    if len(rows) != 120 or len({r["id"] for r in rows}) != 120:
        raise ValueError("A complete frozen reliability plan requires 120 distinct cases")
    groups = {}
    for row in rows:
        if row["split"] not in {"development", "holdout"}:
            raise ValueError("Unknown research split")
        groups.setdefault(row["group"], set()).add(row["split"])
        if row["independent_review"] is not None:
            raise ValueError("New frozen cases must not invent an independent review")
        if any(topic not in sources for topic in row["source_topics"]):
            raise ValueError("A case refers to an absent frozen source topic")
    if any(len(splits) != 1 for splits in groups.values()):
        raise ValueError("Related question families cross development and holdout splits")
    books = set()
    for value in sources.values():
        for passage in value["passages"]:
            books.add(passage["title"])
            if hashlib.sha256(passage["text"].encode()).hexdigest() != passage["text_hash"]:
                raise ValueError("Frozen source passage hash mismatch")
            if not passage["pages"] or not passage["source_url"].startswith(
                "https://assets.openstax.org/"
            ):
                raise ValueError("Frozen source locator is incomplete")
    if books != {"Biology 2e", "Chemistry 2e", "Concepts of Biology", "Anatomy and Physiology 2e"}:
        raise ValueError("Frozen full reliability plan must bind all four declared books")
    return plan
