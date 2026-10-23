"""Independent reviewer materials for the source-bound practice-feedback addendum."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
from uuid import UUID, uuid5

from .practice_feedback_formal import load_catalogue, sha256, stable_json

REVIEW_NAMESPACE = UUID("a8a9ce72-b5ae-499f-8c35-df6fbf89e038")
SCORES = {
    "item_solvable": {"yes", "no", "unclear"},
    "response_correctness": {"correct", "partial", "incorrect", "unclear"},
    "feedback_accurate": {"yes", "no", "unclear"},
    "feedback_actionable": {"yes", "no", "unclear"},
    "answer_key_exposed_before_attempt": {"yes", "no", "unclear"},
}
REVIEW_FIELDS = [
    "review_id",
    "source_title",
    "source_url",
    "physical_pdf_page",
    "source_section",
    "source_text",
    "item_kind",
    "item_prompt",
    "item_options",
    "learner_response",
    "learner_feedback_outcome",
    "learner_feedback_message",
    *SCORES,
    "reason",
    "reviewer_id",
    "completed_at_utc",
]


def export_materials(
    frozen_dir: Path,
    reserved_dir: Path,
    source_units_path: Path,
    destination: Path,
    *,
    seed: int = 5703,
) -> dict:
    if destination.exists():
        raise FileExistsError("Reviewer materials must be created in a fresh directory")
    catalogue_path = frozen_dir / "catalogue.json"
    manifest_path = frozen_dir / "manifest.json"
    catalogue = load_catalogue(catalogue_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if sha256(catalogue_path.read_bytes()) != manifest["catalogue_sha256"]:
        raise ValueError("Review material catalogue does not match the practice freeze")
    reserved = json.loads((reserved_dir / "summary.json").read_text(encoding="utf-8"))
    if reserved["frozen_manifest_sha256"] != sha256(manifest_path.read_bytes()):
        raise ValueError("Reserved run does not match the practice freeze")
    source_data = json.loads(source_units_path.read_text(encoding="utf-8"))
    source_by_id = {row["id"]: row for row in source_data["cases"]}
    outcomes = {row["id"]: row for row in reserved["case_records"]}
    rows = []
    coordinator = []
    for case in catalogue["cases"]:
        if case["split"] != "reserved":
            continue
        cid = case["id"]
        source = source_by_id.get(cid)
        if (
            source is None
            or source["source_unit_id"] != case["source"]["locator"]["source_unit_id"]
            or sha256(source["text"].encode("utf-8")) != case["source"]["locator"]["text_hash"]
        ):
            raise ValueError(f"Reviewer source text cannot be verified: {cid}")
        observed = outcomes[cid]
        for ordinal, attempt in enumerate(observed["attempts"], 1):
            review_id = str(
                uuid5(REVIEW_NAMESPACE, f"{manifest['catalogue_sha256']}:{seed}:{cid}:{ordinal}")
            )
            row = {
                "review_id": review_id,
                "source_title": case["source"]["title"],
                "source_url": next(
                    item["source_url"]
                    for item in manifest["source_audit"]["sources"]
                    if item["id"] == cid
                ),
                "physical_pdf_page": case["source"]["physical_pdf_page"],
                "source_section": case["source"]["section"],
                "source_text": source["text"],
                "item_kind": case["draft"]["kind"],
                "item_prompt": case["draft"]["prompt"],
                "item_options": json.dumps(case["draft"].get("options", []), ensure_ascii=False),
                "learner_response": json.dumps(attempt["response"], ensure_ascii=False),
                "learner_feedback_outcome": attempt["observed_outcome"],
                "learner_feedback_message": attempt["feedback"]["message"],
                **{field: "" for field in SCORES},
                "reason": "",
                "reviewer_id": "",
                "completed_at_utc": "",
            }
            rows.append(row)
            coordinator.append(
                {
                    "review_id": review_id,
                    "case_id": cid,
                    "attempt_ordinal": ordinal,
                    "expected_rule_outcome": case["attempts"][ordinal - 1]["expected_rule_outcome"],
                    "observed_rule_outcome": attempt["observed_outcome"],
                }
            )
    if len(rows) != reserved["scheduled_attempts"]:
        raise ValueError("Every frozen reserved attempt needs one reviewer row")
    destination.mkdir(parents=True)
    with (destination / "coordinator-key.json").open("xb") as stream:
        stream.write(
            stable_json(
                {
                    "schema": "practice_feedback_review_coordinator_v1",
                    "frozen_manifest_sha256": sha256(manifest_path.read_bytes()),
                    "source_units_sha256": sha256(source_units_path.read_bytes()),
                    "rows": coordinator,
                }
            )
        )
    for index, reviewer in enumerate(("A", "B")):
        shuffled = list(rows)
        random.Random(seed + index * 1009).shuffle(shuffled)
        with (destination / f"reviewer-{reviewer}-blank.csv").open(
            "x", encoding="utf-8-sig", newline=""
        ) as stream:
            writer = csv.DictWriter(stream, fieldnames=REVIEW_FIELDS)
            writer.writeheader()
            writer.writerows(shuffled)
    (destination / "SCORING_GUIDE.md").write_text(
        "# Practice feedback independent review\n\n"
        "Review the exact released textbook source text and page, item prompt/options, submitted learner response "
        "and learner-visible feedback. Work independently; the coordinator key contains frozen automatic rule labels "
        "and must remain closed during scoring. The displayed PDF page is the physical PDF page.\n\n"
        "For every row score: `item_solvable` (source and prompt permit one justified response); "
        "`response_correctness` (judge the submitted response using the source and stated conditions); "
        "`feedback_accurate` (feedback outcome and explanation fit the response); "
        "`feedback_actionable` (a learner could make a useful next attempt); "
        "and `answer_key_exposed_before_attempt` (use `unclear` unless independent API evidence establishes what "
        "was visible before submission). Use only the allowed vocabulary in the template. Provide an evidence-based "
        "reason for every scored row and a timezone-aware completion timestamp. Leave all score fields blank on "
        "unreviewed rows. Do not infer actual learner gain or semantic quality from deterministic rule agreement.\n",
        encoding="utf-8",
    )
    return {
        "schema": "practice_feedback_review_materials_v1",
        "reserved_attempts": len(rows),
        "two_blank_independent_forms": True,
        "human_ratings": 0,
        "coordinator_key_sha256": sha256((destination / "coordinator-key.json").read_bytes()),
        "reviewer_A_form_sha256": sha256((destination / "reviewer-A-blank.csv").read_bytes()),
        "reviewer_B_form_sha256": sha256((destination / "reviewer-B-blank.csv").read_bytes()),
    }


def import_ratings(
    materials_dir: Path, filled_csv: Path, reviewer_id: str, destination: Path
) -> dict:
    if not reviewer_id.strip() or destination.exists():
        raise ValueError("A distinct reviewer identity and fresh import path are required")
    key = json.loads((materials_dir / "coordinator-key.json").read_text(encoding="utf-8"))
    expected_ids = {row["review_id"] for row in key["rows"]}
    with (materials_dir / "reviewer-A-blank.csv").open(
        "r", encoding="utf-8-sig", newline=""
    ) as stream:
        original_rows = {row["review_id"]: row for row in csv.DictReader(stream)}
    if set(original_rows) != expected_ids:
        raise ValueError("The source reviewer template changed")
    with filled_csv.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != REVIEW_FIELDS:
            raise ValueError("The reviewer template columns changed")
        rows = list(reader)
    if len(rows) != len(expected_ids) or {row["review_id"] for row in rows} != expected_ids:
        raise ValueError("Reviewer IDs are missing, duplicated or added")
    completed = []
    fixed_fields = [
        field
        for field in REVIEW_FIELDS
        if field not in SCORES and field not in {"reason", "reviewer_id", "completed_at_utc"}
    ]
    for row in rows:
        original = original_rows[row["review_id"]]
        if any(row[field] != original[field] for field in fixed_fields):
            raise ValueError("Source, question, answer or feedback text changed during review")
        values = {field: row[field].strip() for field in SCORES}
        any_score = any(values.values())
        if not any_score:
            if (
                row["reason"].strip()
                or row["reviewer_id"].strip()
                or row["completed_at_utc"].strip()
            ):
                raise ValueError("Unscored rows must remain blank")
            continue
        if (
            any(values[field] not in choices for field, choices in SCORES.items())
            or not row["reason"].strip()
            or row["reviewer_id"].strip() != reviewer_id
        ):
            raise ValueError("A scored row needs every valid score, reason and actual reviewer ID")
        try:
            completed_at = datetime.fromisoformat(row["completed_at_utc"])
        except ValueError as exc:
            raise ValueError("A scored row needs an ISO completion timestamp") from exc
        if completed_at.tzinfo is None or completed_at.astimezone(timezone.utc) > datetime.now(
            timezone.utc
        ):
            raise ValueError("Review timestamp must be timezone-aware and not in the future")
        completed.append(
            {
                "review_id": row["review_id"],
                "scores": values,
                "reason": row["reason"].strip(),
                "reviewer_id": reviewer_id,
                "completed_at_utc": completed_at.isoformat(),
            }
        )
    result = {
        "schema": "practice_feedback_independent_review_import_v1",
        "coordinator_key_sha256": sha256((materials_dir / "coordinator-key.json").read_bytes()),
        "submitted_csv_sha256": sha256(filled_csv.read_bytes()),
        "reviewer_id": reviewer_id,
        "scheduled_rows": len(expected_ids),
        "completed_rows": len(completed),
        "ratings": completed,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as stream:
        stream.write(stable_json(result))
    return {
        key: result[key] for key in ("schema", "reviewer_id", "scheduled_rows", "completed_rows")
    }
