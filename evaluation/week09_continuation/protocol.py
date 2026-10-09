"""Freeze seven study families without exposing private labels to the product."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import random
from urllib.parse import urlsplit

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from . import PROTOCOL_VERSION

FAMILIES = {
    "textbook_qa": ("release_20260926", "candidate", "E0", "E1"),
    "joint_tutoring": ("A", "B", "C", "D", "release_20260926"),
    "learning_memory": ("previous", "candidate"),
    "practice_feedback": ("candidate",),
    "visual_structure": ("previous", "candidate"),
    "safety_robustness": ("previous", "candidate"),
    "performance_recovery": ("release_20260926", "candidate"),
}
LABEL_PROVENANCE = {"human_existing", "program_derived", "ai_generated", "unlabelled"}
SPLITS = {"development", "pilot", "reserved"}
SOURCE_FAMILIES = {"textbook_qa", "joint_tutoring", "practice_feedback", "visual_structure"}
PRIVATE_TASK_KEYS = {
    "answer_key",
    "correct_answer",
    "correct_option",
    "reference_answer",
    "private_labels",
    "hidden_solution",
    "forbidden_memory_ids",
}
OFFICIAL_BOOKS = {
    "Anatomy and Physiology 2e": "aa2e577b2083c343f4d57b38f00dd935dd2d98befdb38c0f368d72d636d0ff46",
    "Biology 2e": "4d1f413fd779f114838cdaeab7859dcb2922ca7529230d3bfd7d36a77b4e27b6",
    "Chemistry 2e": "fd89db1b8a1fee06b8ad3e8982f4f4b34bde4e93654a4ce28b724f8c0efe98d6",
    "Concepts of Biology": "da0ffc8585e172f04eb0abb08949087baf85cc229ef2736ef06e5aa17094b1f6",
}
REQUIRED_FREEZE = {
    "candidate_source_sha256",
    "migration_head",
    "corpus_release_id",
    "corpus_manifest_sha256",
    "model_roles",
    "budgets",
    "policy_versions",
    "software_gate_sha256",
    "tariff",
}


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _hex_sha(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(letter in "0123456789abcdef" for letter in value)
    )


def _source_anchor(anchor: dict) -> None:
    if anchor.get("source_kind") != "official_openstax":
        raise ValueError("Textbook anchors must identify official OpenStax source material")
    if not all(anchor.get(field) for field in ("source_title", "source_url", "chunk_id")):
        raise ValueError("Source title, official URL and chunk identity are required")
    parsed = urlsplit(str(anchor["source_url"]))
    if parsed.scheme != "https" or parsed.hostname != "assets.openstax.org":
        raise ValueError("Official PDF URL must use the OpenStax asset host")
    if not anchor.get("pages") or not all(
        type(page) is int and page > 0 for page in anchor["pages"]
    ):
        raise ValueError("Physical PDF page numbers are required")
    if not _hex_sha(anchor.get("text_hash")) or not _hex_sha(anchor.get("original_sha256")):
        raise ValueError("Source text and official PDF SHA-256 are required")
    if OFFICIAL_BOOKS.get(anchor["source_title"]) != anchor["original_sha256"]:
        raise ValueError("Book identity does not match the preserved official PDF")
    if "text" in anchor and digest_bytes(anchor["text"].encode("utf-8")) != anchor["text_hash"]:
        raise ValueError("Anchor text differs from its content hash")
    if anchor.get("release_id") is None:
        raise ValueError("Source anchor needs its immutable corpus release")


def validate_catalogue(catalogue: dict) -> dict:
    if catalogue.get("schema") != PROTOCOL_VERSION + "_catalogue":
        raise ValueError("Unsupported continuation catalogue schema")
    cases = catalogue.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("A nonempty case catalogue is required")
    ids: set[str] = set()
    group_splits: dict[str, str] = {}
    for case in cases:
        identity, family, split, group = (
            case.get("id"),
            case.get("family"),
            case.get("split"),
            case.get("concept_group"),
        )
        if not isinstance(identity, str) or not identity or identity in ids:
            raise ValueError("Case identities must be nonempty and unique")
        ids.add(identity)
        if family not in FAMILIES or split not in SPLITS:
            raise ValueError(f"Unknown family or split in {identity}")
        if not isinstance(group, str) or not group:
            raise ValueError("Every case needs a knowledge-concept grouping key")
        if group in group_splits and group_splits[group] != split:
            raise ValueError(f"Knowledge-concept group crosses splits: {group}")
        group_splits[group] = split
        if case.get("label_provenance") not in LABEL_PROVENANCE:
            raise ValueError(f"Invalid label provenance in {identity}")
        if not isinstance(case.get("task"), dict) or not case["task"]:
            raise ValueError(f"Runnable task contract missing in {identity}")

        def private_key(value):
            if isinstance(value, dict):
                return any(
                    key in PRIVATE_TASK_KEYS or private_key(child) for key, child in value.items()
                )
            if isinstance(value, list):
                return any(private_key(child) for child in value)
            return False

        if private_key(case["task"]):
            raise ValueError("Private answer or evaluator labels cannot enter the runnable task")
        if not isinstance(case.get("required_points", []), list) or not isinstance(
            case.get("unsupported_conclusions", []), list
        ):
            raise ValueError("Required and unsupported point lists must be explicit")
        anchors = case.get("source_anchors")
        if not isinstance(anchors, list) or (family in SOURCE_FAMILIES and not anchors):
            raise ValueError("Textbook cases require real source anchors")
        for anchor in anchors:
            _source_anchor(anchor)
        if case["label_provenance"] == "unlabelled" and case.get("private_labels"):
            raise ValueError("Unlabelled cases cannot carry scored reference labels")
        if split == "reserved" and case.get("inspected_output"):
            raise ValueError("Inspected output cannot enter a reserved concept group")
        arms = case.get("arms", FAMILIES[family])
        if not isinstance(arms, (list, tuple)) or not arms or len(set(arms)) != len(arms):
            raise ValueError("Cases need distinct declared comparison arms")
        if not set(arms) <= set(FAMILIES[family]):
            raise ValueError("Case arm is outside its preregistered family")
        if family == "joint_tutoring" and not {"A", "B", "C", "D"} <= set(arms):
            raise ValueError("Teaching factorial needs all four matched arms")
    return {"cases": len(cases), "groups": len(group_splits), "splits": group_splits}


def _validate_candidate(candidate: dict, *, allow_development: bool) -> None:
    missing = REQUIRED_FREEZE - set(candidate)
    if missing:
        raise ValueError(f"Candidate freeze is missing: {', '.join(sorted(missing))}")
    if not all(
        _hex_sha(candidate[key])
        for key in ("candidate_source_sha256", "corpus_manifest_sha256", "software_gate_sha256")
    ):
        raise ValueError("Candidate source, corpus and software hashes must be SHA-256")
    if not candidate["model_roles"] or not candidate["budgets"] or not candidate["policy_versions"]:
        raise ValueError("Model roles, budgets and policy versions must be frozen")
    if not allow_development and candidate.get("integration_status") != "verified_and_frozen":
        raise ValueError("Pilot or reserved execution requires a verified integrated candidate")


def verify_official_anchors(
    cases: list[dict],
    release_id: str,
    *,
    connection_file: Path | None = None,
    database_url_env: str | None = None,
) -> dict:
    """Read-only SQL binds each claimed passage to the released official PDF."""
    if (connection_file is None) == (database_url_env is None):
        raise ValueError("Provide exactly one private database connection source")
    if connection_file is not None:
        url = json.loads(connection_file.read_text(encoding="utf-8"))["database_url"]
    else:
        url = os.environ.get(database_url_env or "")
        if not url:
            raise ValueError("The selected private database URL environment is unavailable")
    if not url.startswith("postgresql+"):
        raise ValueError("Official anchor verification requires PostgreSQL")
    engine = create_engine(url, hide_parameters=True, connect_args={"connect_timeout": 10})
    checked = 0
    try:
        with Session(engine) as db:
            db.execute(text("SET TRANSACTION READ ONLY"))
            if db.scalar(text("SHOW transaction_read_only")) != "on":
                raise ValueError("Anchor verifier transaction is not read-only")
            active = db.scalar(text("SELECT release_id FROM active_corpus WHERE id=1"))
            if active != release_id:
                raise ValueError("Frozen source release is not the active corpus")
            for case in cases:
                for anchor in case["source_anchors"]:
                    observed = db.execute(
                        text("""
                        SELECT c.text, c.text_hash, c.pages, c.section,
                               d.title, d.source_url, dv.raw_hash
                        FROM release_chunks rc
                        JOIN chunks c ON c.id = rc.chunk_id
                        JOIN documents d ON d.id = c.document_id
                        JOIN processing_runs pr ON pr.id = c.processing_id
                        JOIN document_versions dv ON dv.id = pr.document_version_id
                        WHERE rc.release_id = :release AND rc.chunk_id = :chunk
                    """),
                        {"release": release_id, "chunk": anchor["chunk_id"]},
                    ).one_or_none()
                    if observed is None:
                        raise ValueError("Anchor chunk does not belong to the frozen release")
                    (source_text, text_hash, pages, section, title, source_url, raw_hash) = observed
                    if (
                        digest_bytes(source_text.encode("utf-8")) != anchor["text_hash"]
                        or text_hash != anchor["text_hash"]
                        or sorted(pages) != sorted(anchor["pages"])
                        or title != anchor["source_title"]
                        or source_url != anchor["source_url"]
                        or raw_hash != anchor["original_sha256"]
                        or (anchor.get("section") is not None and section != anchor["section"])
                        or ("text" in anchor and source_text != anchor["text"])
                    ):
                        raise ValueError(
                            "Claimed source location differs from the released database"
                        )
                    checked += 1
    finally:
        engine.dispose()
    return {"verified_anchors": checked, "release_id": release_id, "read_only": True}


def verify_prepared_source_coverage(
    cases: list[dict],
    candidate: dict,
    *,
    qa_preparation_path: Path | None = None,
    teaching_preparation_path: Path | None = None,
    require_snapshots: bool = True,
) -> dict:
    """Reject a frozen CPU snapshot that filtered out a declared textbook anchor."""
    coverage = {}
    for family, digest_field, path in (
        ("textbook_qa", "qa_retrieval_sha256", qa_preparation_path),
        ("joint_tutoring", "teaching_retrieval_sha256", teaching_preparation_path),
    ):
        selected = [case for case in cases if case["family"] == family]
        expected_digest = candidate.get(digest_field)
        if not selected:
            continue
        if expected_digest is None:
            if require_snapshots:
                raise ValueError(f"{family} requires its frozen CPU preparation SHA")
            continue
        if not _hex_sha(expected_digest) or path is None or not path.is_file():
            raise ValueError(f"{family} requires its frozen real CPU preparation file")
        raw = path.read_bytes()
        if digest_bytes(raw) != expected_digest:
            raise ValueError(f"{family} preparation differs from the candidate freeze")
        prepared = json.loads(raw)
        if (
            prepared.get("provider_calls") != 0
            or prepared.get("corpus_unchanged") is not True
            or prepared.get("runtime_device") != "cpu"
            or prepared.get("corpus", {}).get("release_id") != candidate["corpus_release_id"]
        ):
            raise ValueError(f"{family} preparation lacks real read-only CPU lineage")
        rows = prepared.get("cases")
        if not isinstance(rows, list) or len({row.get("id") for row in rows}) != len(rows):
            raise ValueError(f"{family} preparation case identities are invalid")
        by_id = {row["id"]: row for row in rows}
        if set(by_id) != {case["id"] for case in selected}:
            raise ValueError(f"{family} preparation does not cover the frozen cases")
        checked = 0
        for case in selected:
            evidence = by_id[case["id"]].get("retrieval", {}).get("evidence")
            if not isinstance(evidence, list):
                raise ValueError(f"{family} has no accepted evidence list")
            accepted = {item.get("chunk_id"): item for item in evidence}
            for anchor in case["source_anchors"]:
                item = accepted.get(anchor["chunk_id"])
                if item is None or item.get("text_hash") != anchor["text_hash"]:
                    raise ValueError(
                        f"{family} accepted retrieval omitted its declared official source anchor"
                    )
                checked += 1
        coverage[family] = {"cases": len(selected), "accepted_source_anchors": checked}
    return coverage


def freeze(
    catalogue_path: Path,
    candidate_path: Path,
    output: Path,
    *,
    split: str,
    seed: int = 57030930,
    pilot_decision_path: Path | None = None,
    connection_file: Path | None = None,
    database_url_env: str | None = None,
    qa_preparation_path: Path | None = None,
    teaching_preparation_path: Path | None = None,
) -> dict:
    """Write one immutable study schedule; never silently reuse a study directory."""
    if output.exists():
        raise ValueError("Use a new directory; prior experiment receipts are immutable")
    if split not in SPLITS:
        raise ValueError("Unknown split")
    raw_catalogue, raw_candidate = catalogue_path.read_bytes(), candidate_path.read_bytes()
    catalogue, candidate = json.loads(raw_catalogue), json.loads(raw_candidate)
    validate_catalogue(catalogue)
    _validate_candidate(candidate, allow_development=split == "development")
    if split != "development" and not _hex_sha(candidate.get("quality_thresholds_sha256")):
        raise ValueError("Pilot and reserved studies require prespecified quality thresholds")
    if split == "reserved":
        if pilot_decision_path is None or not pilot_decision_path.is_file():
            raise ValueError("The pilot-based decision must be frozen before reserved execution")
        pilot_decision = json.loads(pilot_decision_path.read_text(encoding="utf-8"))
        if pilot_decision.get("schema") != PROTOCOL_VERSION + "_pilot_decision":
            raise ValueError("Unknown pilot decision version")
        if pilot_decision.get("ready_for_reserved") is not True:
            raise ValueError("Pilot has not passed the preregistered reserved-study gates")
        decision_hash = digest_bytes(pilot_decision_path.read_bytes())
    else:
        decision_hash = None
    selected = [case for case in catalogue["cases"] if case["split"] == split]
    if not selected:
        raise ValueError(f"The {split} split has no cases")
    release = candidate["corpus_release_id"]
    for case in selected:
        for anchor in case["source_anchors"]:
            if anchor["release_id"] != release:
                raise ValueError("Study anchor differs from the candidate corpus release")
    prepared_source_coverage = verify_prepared_source_coverage(
        selected,
        candidate,
        qa_preparation_path=qa_preparation_path,
        teaching_preparation_path=teaching_preparation_path,
        require_snapshots=split != "development",
    )
    if split != "development" and connection_file is None and database_url_env is None:
        raise ValueError(
            "Pilot and reserved source anchors require real read-only database verification"
        )
    anchor_verification = (
        verify_official_anchors(
            selected,
            release,
            connection_file=connection_file,
            database_url_env=database_url_env,
        )
        if connection_file is not None or database_url_env is not None
        else {
            "verified_anchors": 0,
            "release_id": release,
            "read_only": False,
            "scope": "structural_validation_only_development",
        }
    )
    schedule = [
        {
            "id": f"{case['id']}::{arm}",
            "case_id": case["id"],
            "family": case["family"],
            "concept_group": case["concept_group"],
            "arm": arm,
        }
        for case in selected
        for arm in case.get("arms", FAMILIES[case["family"]])
    ]
    for case in selected:
        if not set(case.get("arms", FAMILIES[case["family"]])) <= set(FAMILIES[case["family"]]):
            raise ValueError("Case arm is outside its preregistered family")
    random.Random(seed).shuffle(schedule)
    public_cases = [
        {
            key: value
            for key, value in case.items()
            if key not in {"private_labels", "inspected_output"}
        }
        for case in selected
    ]
    private_labels = {case["id"]: case.get("private_labels") for case in selected}
    manifest = {
        "schema": PROTOCOL_VERSION + "_manifest",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "split": split,
        "catalogue_sha256": digest_bytes(raw_catalogue),
        "candidate_sha256": digest_bytes(raw_candidate),
        "pilot_decision_sha256": decision_hash,
        "candidate": candidate,
        "anchor_verification": anchor_verification,
        "prepared_source_coverage": prepared_source_coverage,
        "cases": public_cases,
        "schedule": schedule,
        "planned": len(schedule),
        "seed": seed,
        "label_provenance": {case["id"]: case["label_provenance"] for case in selected},
        "human_ratings_recorded": 0,
    }
    output.mkdir(parents=True)
    (output / "manifest.json").write_bytes(canonical(manifest))
    (output / "private-labels.json").write_bytes(canonical(private_labels))
    receipt = {
        "schema": PROTOCOL_VERSION + "_freeze_receipt",
        "manifest_sha256": digest_bytes((output / "manifest.json").read_bytes()),
        "private_labels_sha256": digest_bytes((output / "private-labels.json").read_bytes()),
        "planned": len(schedule),
        "case_count": len(selected),
        "concept_groups": len({case["concept_group"] for case in selected}),
        "split": split,
    }
    (output / "freeze-receipt.json").write_bytes(canonical(receipt))
    return receipt


def load_frozen(folder: Path) -> dict:
    manifest_bytes = (folder / "manifest.json").read_bytes()
    receipt = json.loads((folder / "freeze-receipt.json").read_bytes())
    if digest_bytes(manifest_bytes) != receipt["manifest_sha256"]:
        raise ValueError("Frozen study manifest changed")
    if (
        digest_bytes((folder / "private-labels.json").read_bytes())
        != receipt["private_labels_sha256"]
    ):
        raise ValueError("Private label file changed")
    manifest = json.loads(manifest_bytes)
    if manifest["schema"] != PROTOCOL_VERSION + "_manifest":
        raise ValueError("Unsupported frozen study")
    return manifest
