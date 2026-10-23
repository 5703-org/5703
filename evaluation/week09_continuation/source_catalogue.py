"""Development-only cases anchored to the prior real OpenStax retrieval record."""

from __future__ import annotations

import json
from pathlib import Path

from . import PROTOCOL_VERSION
from .protocol import OFFICIAL_BOOKS, canonical, digest_bytes, validate_catalogue


def build_development_anchor_catalogue(retrieval_record: Path, output: Path) -> dict:
    """Import inspected old questions as development cases, never reserved labels."""
    if output.exists():
        raise ValueError("Preserve prior development catalogues")
    raw = retrieval_record.read_bytes()
    record = json.loads(raw)
    if record.get("status") != "passed_source_and_vector_checks" or not record.get("release_id"):
        raise ValueError("The actual retrieval proof did not pass or lacks a release ID")
    cases = []
    for index, question in enumerate(record.get("questions", []), 1):
        anchors = []
        for hit in question.get("hits", [])[:3]:
            if hit.get("source_title") not in OFFICIAL_BOOKS:
                raise ValueError("Unknown official book in a retrieval record")
            anchor = {
                "source_kind": "official_openstax",
                "source_title": hit["source_title"],
                "source_url": hit["source_url"],
                "original_sha256": OFFICIAL_BOOKS[hit["source_title"]],
                "release_id": record["release_id"],
                "chunk_id": hit["chunk_id"],
                "text_hash": hit["text_hash"],
                "text": hit["text"],
                "section": hit.get("section"),
                "pages": hit["pages"],
                "source_position": "retrieval_hit_without_semantic_relevance_label",
            }
            if digest_bytes(anchor["text"].encode("utf-8")) != anchor["text_hash"]:
                raise ValueError("The historical retrieved passage hash is inconsistent")
            anchors.append(anchor)
        if not anchors:
            # A recorded no-hit query remains an explicit out-of-scope development case.
            continue
        cases.append(
            {
                "id": f"W9C-DEV-REAL-{index:03d}",
                "family": "textbook_qa",
                "split": "development",
                "concept_group": "historical-inspected-"
                + digest_bytes(question["question"].encode())[:16],
                "task": {"question": question["question"], "answer_mode": "textbook"},
                "source_anchors": anchors,
                "required_points": [],
                "unsupported_conclusions": [],
                "label_provenance": "unlabelled",
                "private_labels": None,
                "inspected_output": True,
                "prior_record_category": question.get("category"),
                "provenance_note": "Existing 8 September real vector retrieval; inspected development material only. Retrieved hits have no independent relevance or sufficiency label.",
            }
        )
    catalogue = {
        "schema": PROTOCOL_VERSION + "_catalogue",
        "source_record_sha256": digest_bytes(raw),
        "source_record": str(retrieval_record),
        "source_release_id": record["release_id"],
        "cases": cases,
    }
    validate_catalogue(catalogue)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical(catalogue))
    return {
        "cases": len(cases),
        "split": "development",
        "label_provenance": "unlabelled",
        "official_source_release": record["release_id"],
        "source_record_sha256": catalogue["source_record_sha256"],
        "catalogue_sha256": digest_bytes(output.read_bytes()),
    }
