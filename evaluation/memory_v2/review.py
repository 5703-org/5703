"""Blinded human-review materials and append-only, explicitly supplied attestations.

This module performs no model, database or network calls. It cannot establish a
reviewer's real-world identity; supplied identities and attestations are recorded.
"""

from __future__ import annotations

from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
import csv
import hashlib
import html
import json
from pathlib import Path
import random
import re

from evaluation.enhancement.protocol import digest, freeze, verify_frozen
from evaluation.memory_v2.judging import RUBRIC as AUTOMATIC_RUBRIC, SCORE_FIELDS, judge_input
from evaluation.memory_v2.protocol import SEED, require_oracle_confirmation, schedule

VERSION = "memory_v2_independent_review_v1"
SCORES = tuple(sorted(SCORE_FIELDS))
FIELDS = ("review_id", "reviewer_id", "rubric_version", *SCORES, "reason", "completed_at")
RUBRIC = {
    "version": VERSION,
    "dimensions": {k: AUTOMATIC_RUBRIC[k] for k in SCORES},
    "scale": "0/1 for applicable dimensions; NA for inapplicable dimensions; unfinished rows stay blank.",
    "identity_limit": "Reviewer identities and independent-human attestations are supplied by the operator, not technically authenticated.",
}


def load(path):
    return verify_frozen(json.loads(Path(path).read_text(encoding="utf-8")))


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def human_identity(value):
    if (
        not isinstance(value, str)
        or value != value.strip()
        or not 1 <= len(value) <= 80
        or any(ord(c) < 32 for c in value)
        or value.casefold() in {"ai", "codex", "automatic", "model", "chatgpt"}
    ):
        raise ValueError("Supply the actual human reviewer's bounded identifier")


def past_time(value):
    stamp = datetime.fromisoformat(value)
    if stamp.tzinfo is None or stamp > datetime.now(timezone.utc):
        raise ValueError("Completion time must be timezone-aware and no later than import")


def _inputs(source):
    study = load(source / "study.json")
    tasks = load(source / "private-tasks.json")["tasks"]
    private_memory = load(source / "private-trajectories.json")
    trajectories = private_memory["trajectories"]
    if (
        digest(tasks) != study["tasks_sha256"]
        or digest(trajectories) != study["trajectories_sha256"]
    ):
        raise ValueError("Private catalogue differs from the frozen study")
    if any(
        digest(private_memory[name]) != study["checkpoint"][field]
        for name, field in (
            ("extraction_cases", "memory_extraction_sha256"),
            ("gating_pairs", "memory_gating_sha256"),
        )
    ):
        raise ValueError("Private memory extraction/gating labels differ from the freeze")
    if study["schedule"] != schedule(tasks, trajectories):
        raise ValueError("The study does not contain the exact registered schedule")
    return study, {t["id"]: t for t in tasks}, {t["id"]: t for t in trajectories}


def export_reviews(
    run: Path, output: Path, *, memory_run: Path | None = None, source: Path | None = None
):
    """Export all 552 planned rows, retaining missing/failed/external outcomes."""
    run, output = Path(run), Path(output)
    if output.exists():
        raise ValueError("Keep prior review materials; choose a new output directory")
    run_manifest = load(run / "run-manifest.json")
    source = Path(source or run_manifest["source_directory"])
    study, tasks, trajectories = _inputs(source)
    if run_manifest["study_hash"] != digest(study):
        raise ValueError("Run and source study identities differ")
    roots = [run]
    if memory_run is not None:
        memory_run = Path(memory_run)
        if memory_run.resolve() == run.resolve():
            raise ValueError("Memory run must be a separate root")
        if load(memory_run / "answer-manifest.json")["study_hash"] != digest(study):
            raise ValueError("Memory run belongs to another study")
        roots.append(memory_run)
    scheduled_ids = {r["id"] for r in study["schedule"]}
    for folder in roots:
        if any(p.stem not in scheduled_ids for p in (folder / "results").glob("*.json")):
            raise ValueError("Unscheduled result file in supplied run")
    private, materials = [], []
    for item in study["schedule"]:
        paths = [p / "results" / (item["id"] + ".json") for p in roots]
        paths = [p for p in paths if p.exists()]
        if len(paths) > 1:
            raise ValueError("A scheduled result exists in more than one run")
        result = load(paths[0]) if paths else None
        if result and any(
            result.get(k) != item[k] for k in ("id", "study", "case_id", "arm", "turn", "family")
        ):
            raise ValueError("Result identity differs from the scheduled request")
        trajectory = trajectories[item["case_id"]] if item["study"] == "M" else None
        task = (
            tasks[trajectory["probes"][item["turn"] - 1]["question_id"]]
            if trajectory
            else tasks[item["case_id"]]
        )
        record = result or {**item, "outcome": None, "exposure": None, "prior_exposure": []}
        payload = judge_input(task, record, trajectory=trajectory)
        payload.pop("rubric")
        # An unpublished failed draft is never represented as learner exposure.
        if not record.get("exposure") or (record.get("outcome") or {}).get("error"):
            payload["current_exposure"] = None
            payload["applicable_fields"] = []
        review_id = (
            "review_" + digest({"study": digest(study), "item": item["id"], "seed": SEED})[:20]
        )
        material = {
            "review_id": review_id,
            "round": item["turn"],
            **payload,
            "execution_status": "delivered"
            if payload["current_exposure"]
            else "no_delivered_answer",
            "source_scope": "Verification references are distinct from actual delivered surfaces. Read only current_exposure/prior_exposure as learner exposure; no reading or comprehension is inferred.",
        }
        materials.append(material)
        private.append(
            {
                "review_id": review_id,
                "item_id": item["id"],
                "study": item["study"],
                "case_id": item["case_id"],
                "arm": item["arm"],
                "turn": item["turn"],
                "execution_status": record.get("status", "unrecorded") if result else "unrecorded",
                "result_sha256": digest(result) if result else None,
                "result_file_sha256": file_hash(paths[0]) if paths else None,
                "material_sha256": digest(material),
                "applicable_fields": material["applicable_fields"],
            }
        )
    output.mkdir(parents=True)
    public_hashes = {}
    for slot in (1, 2):
        rows = materials.copy()
        random.Random(SEED + slot).shuffle(rows)
        folder = output / f"reviewer-{slot}"
        folder.mkdir()
        material = {"rubric": RUBRIC, "items": rows, "assigned_reviewer_slot": slot}
        freeze(folder / "review-material.json", material)
        public_hashes[str(slot)] = digest(material)
        with (folder / "ratings.csv").open("x", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            for row in rows:
                writer.writerow({"review_id": row["review_id"], "rubric_version": VERSION})
        cards = [
            "<details><summary>"
            + html.escape(r["review_id"])
            + "</summary><pre>"
            + html.escape(json.dumps(r, ensure_ascii=False, indent=2))
            + "</pre></details>"
            for r in rows
        ]
        (folder / "review.html").write_text(
            "<!doctype html><html lang=en><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>Independent review</title><style>body{font:16px/1.5 system-ui;max-width:1000px;margin:auto;padding:24px}pre{white-space:pre-wrap;overflow-wrap:anywhere}summary{cursor:pointer;padding:12px}</style><h1>Independent review</h1><p>Score independently in ratings.csv using the supplied rubric. No scores have been filled in.</p><pre>"
            + html.escape(json.dumps(RUBRIC, indent=2))
            + "</pre>"
            + "\n".join(cards)
            + "</html>",
            encoding="utf-8",
        )
    freeze(
        output / "coordinator-only-condition-key.json",
        {
            "version": VERSION,
            "study_hash": digest(study),
            "run_manifest_hash": digest(run_manifest),
            "source_directory": str(source.resolve()),
            "run_directory": str(run.resolve()),
            "memory_run_directory": str(memory_run.resolve()) if memory_run else None,
            "planned": len(private),
            "review_material_hashes": public_hashes,
            "items": private,
        },
    )
    (output / "SCORING_GUIDE.md").write_text(
        "# Independent review\n\nGive each person only their reviewer folder and this guide. Keep the coordinator-only condition key, other reviews, online checks and automatic grades separate. Different reviewer orders do not guarantee that prose or visible sources cannot reveal a method.\n\n"
        "The study contains 552 planned requests; errors, missing outcomes and human-oracle prerequisites remain represented. Score delivered content only, not unpublished drafts. All scores, reviewer IDs, reasons and timestamps start blank. Completed rows require 0/1 for every applicable field and NA for every inapplicable field. An unavailable answer has no applicable quality scores; use NA with a factual execution note if reviewing that row. It remains in the all-planned denominator.\n\n"
        "References, help allowances and memory expectations are developer-authored; identify disagreements in your reason. Direct responses permit full answers. Hints use the stated round allowance and cumulative delivered content, including ordinarily accessible sources. Source support and factual correctness are separate dimensions. No method is shown as pre-approved.\n\n"
        "Supply your actual identifier and an ISO 8601 timezone-aware completion time. Import requires explicit independent_human=True and a reviewer slot. This is an operator attestation, not proof of identity. Slots must belong to different people. Imports are immutable; a revised submission creates a new record that links prior submissions. Adjudication requires both independent reviews and retains their original disagreements and ratings.\n\n"
        "The exporter makes no model calls and creates no human ratings. Do not distribute the coordinator key until independent review is complete.\n",
        encoding="utf-8",
    )
    return {
        "planned": len(private),
        "recorded": sum(i["result_sha256"] is not None for i in private),
        "reviewers": 2,
        "ratings_completed": 0,
    }


@contextmanager
def _locked(materials):
    path = Path(materials) / ".review-import.lock"
    try:
        stream = path.open("x", encoding="utf-8")
    except FileExistsError as exc:
        raise ValueError(
            "Another import is active or left an interrupted lock; inspect it before recovery"
        ) from exc
    try:
        with stream:
            stream.write(datetime.now(timezone.utc).isoformat())
        yield
    finally:
        path.unlink()


def _read_ratings(path, reviewer, allowed):
    human_identity(reviewer)
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise ValueError("Use the exact supplied CSV columns")
        rows = list(reader)
    seen, completed = set(), []
    for row in rows:
        identity = row["review_id"]
        if (
            identity not in allowed
            or identity in seen
            or None in row
            or any(v is None for v in row.values())
        ):
            raise ValueError("Unknown, duplicate or malformed review row")
        seen.add(identity)
        if not any(row[k].strip() for k in (*SCORES, "reviewer_id", "reason", "completed_at")):
            continue
        if row["reviewer_id"] != reviewer or row["rubric_version"] != VERSION:
            raise ValueError("Reviewer or rubric identity differs")
        applicable = set(allowed[identity]["applicable_fields"])
        if any(row[k] not in ({"0", "1"} if k in applicable else {"NA"}) for k in SCORES):
            raise ValueError("Scores must respect each item's declared applicability")
        if not row["reason"].strip() or len(row["reason"]) > 6000:
            raise ValueError("A bounded substantive review reason is required")
        past_time(row["completed_at"])
        completed.append({**row, **{k: int(row[k]) if k in applicable else None for k in SCORES}})
    if not completed:
        raise ValueError("No completed human review was supplied")
    return completed


def _imports(materials):
    records = []
    for path in sorted((Path(materials) / "imports").glob("*.json")):
        record = load(path)
        if (
            not path.with_suffix(".csv").exists()
            or file_hash(path.with_suffix(".csv")) != record["source_sha256"]
        ):
            raise ValueError("Original imported ratings are missing or changed")
        records.append(record)
    superseded = {name for r in records for name in r["supersedes"]}
    active = [r for r in records if r["source_sha256"] + ".json" not in superseded]
    if len({r["slot"] for r in active}) != len(active):
        raise ValueError("Conflicting active review revisions require explicit recovery")
    return records, active


def _write_original(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError("Existing immutable input bytes differ")
        return
    with path.open("xb") as stream:
        stream.write(raw)


def import_review(
    materials: Path, ratings: Path, reviewer: str, *, slot: int, independent_human: bool = False
):
    if independent_human is not True or type(slot) is not int or slot not in (1, 2):
        raise ValueError(
            "Explicit independent human attestation and reviewer slot 1/2 are required"
        )
    materials, ratings = Path(materials), Path(ratings)
    with _locked(materials):
        key = load(materials / "coordinator-only-condition-key.json")
        public = load(materials / f"reviewer-{slot}" / "review-material.json")
        if digest(public) != key["review_material_hashes"][str(slot)]:
            raise ValueError("Assigned review material was modified")
        allowed = {r["review_id"]: r for r in key["items"]}
        completed = _read_ratings(ratings, reviewer, allowed)
        records, active = _imports(materials)
        if any(
            (r["slot"] == slot) != (r["reviewer_id"].casefold() == reviewer.casefold())
            for r in records
        ):
            raise ValueError("Each slot must retain one distinct independent reviewer")
        raw = ratings.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        destination = materials / "imports" / (sha + ".json")
        if destination.exists():
            prior = load(destination)
            if prior["reviewer_id"] != reviewer or prior["slot"] != slot:
                raise ValueError("Existing import has a different identity")
            return {
                "ratings_imported": len(prior["submitted_ratings"]),
                "artifact": str(destination),
                "idempotent": True,
            }
        merged = {
            r["review_id"]: r for batch in active if batch["slot"] == slot for r in batch["ratings"]
        }
        merged.update({r["review_id"]: r for r in completed})
        _write_original(destination.with_suffix(".csv"), raw)
        freeze(
            destination,
            {
                "version": VERSION,
                "slot": slot,
                "reviewer_id": reviewer,
                "independent_human_attestation": True,
                "identity_authenticated": False,
                "source_sha256": sha,
                "materials_hash": digest(key),
                "imported_at": datetime.now(timezone.utc).isoformat(),
                "submitted_ratings": completed,
                "ratings": list(merged.values()),
                "supersedes": [r["source_sha256"] + ".json" for r in records if r["slot"] == slot],
            },
        )
    return {"ratings_imported": len(completed), "artifact": str(destination), "idempotent": False}


def agreement(materials: Path):
    key = load(Path(materials) / "coordinator-only-condition-key.json")
    _, active = _imports(materials)
    by_item = defaultdict(list)
    for batch in active:
        if batch["materials_hash"] != digest(key):
            raise ValueError("Import belongs to different materials")
        for row in batch["ratings"]:
            by_item[row["review_id"]].append(row)
    pairs = [
        r
        for r in by_item.values()
        if len(r) == 2 and len({x["reviewer_id"].casefold() for x in r}) == 2
    ]
    metrics = {}
    for field in SCORES:
        applicable = [r for r in pairs if all(x[field] is not None for x in r)]
        n = len(applicable)
        observed = sum(r[0][field] == r[1][field] for r in applicable) / n if n else None
        left = sum(r[0][field] for r in applicable) / n if n else None
        right = sum(r[1][field] for r in applicable) / n if n else None
        expected = left * right + (1 - left) * (1 - right) if n else None
        metrics[field] = {
            "paired_applicable": n,
            "agreement": observed,
            "cohen_kappa": (observed - expected) / (1 - expected) if n and expected != 1 else None,
        }
    return {
        "planned": key["planned"],
        "supplied_reviewer_identities": len(active),
        "identity_authenticated": False,
        "ratings_imported": sum(len(r["ratings"]) for r in active),
        "paired_items": len(pairs),
        "not_paired": key["planned"] - len(pairs),
        "agreement": metrics,
        "disagreements": [r for r in pairs if any(r[0][k] != r[1][k] for k in SCORES)],
        "adjudications": [
            load(p) for p in sorted((Path(materials) / "adjudications").glob("*.json"))
        ],
        "automatic_ratings_used_as_human": 0,
    }


def import_adjudication(
    materials: Path, ratings: Path, adjudicator: str, *, human_attestation: bool = False
):
    if human_attestation is not True:
        raise ValueError("A supplied human discussion/adjudication attestation is required")
    materials, ratings = Path(materials), Path(ratings)
    with _locked(materials):
        report = agreement(materials)
        if report["supplied_reviewer_identities"] != 2:
            raise ValueError("Both independent reviews are required before adjudication")
        disputed = {r[0]["review_id"] for r in report["disagreements"]}
        key = load(materials / "coordinator-only-condition-key.json")
        allowed = {r["review_id"]: r for r in key["items"] if r["review_id"] in disputed}
        decisions = _read_ratings(ratings, adjudicator, allowed)
        raw = ratings.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        destination = materials / "adjudications" / (sha + ".json")
        if destination.exists():
            if load(destination)["adjudicator"] != adjudicator:
                raise ValueError("Adjudication identity differs")
            return {"adjudicated": len(decisions), "artifact": str(destination), "idempotent": True}
        _, active = _imports(materials)
        _write_original(destination.with_suffix(".csv"), raw)
        freeze(
            destination,
            {
                "version": VERSION,
                "source_sha256": sha,
                "adjudicator": adjudicator,
                "human_attestation": True,
                "identity_authenticated": False,
                "materials_hash": digest(key),
                "review_import_hashes": [digest(r) for r in active],
                "decisions": decisions,
                "imported_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    return {"adjudicated": len(decisions), "artifact": str(destination), "idempotent": False}


def confirm_oracle(source: Path, case_id: str, retrieval_path: Path, attestation_path: Path):
    """Import a human attestation for these exact supplied sources, never create one."""
    source, retrieval_path, attestation_path = (
        Path(source),
        Path(retrieval_path),
        Path(attestation_path),
    )
    study, tasks, _ = _inputs(source)
    if case_id not in tasks or not re.fullmatch(r"[A-Za-z0-9_-]+", case_id):
        raise ValueError("Unknown or unsafe oracle case identity")
    retrieval = load(retrieval_path)
    if (
        retrieval.get("id") != case_id
        or retrieval.get("question") != tasks[case_id]["question"]
        or not retrieval.get("evidence")
        or not retrieval.get("source_map")
    ):
        raise ValueError("Oracle input needs the exact task and nonempty source-mapped evidence")
    evidence_ids = set()
    for item in retrieval["evidence"]:
        eid = item["evidence_id"]
        mapped = retrieval["source_map"].get(item["chunk_id"], {})
        if (
            eid in evidence_ids
            or hashlib.sha256(item["text"].encode()).hexdigest() != item["text_hash"]
        ):
            raise ValueError("Oracle evidence identity or text hash differs")
        evidence_ids.add(eid)
        if (
            mapped.get("chunk_text") != item["text"]
            or mapped.get("chunk_hash") != item["text_hash"]
        ):
            raise ValueError("Oracle evidence is not an exact mapped chunk")
        if (
            mapped.get("processing_id") != item.get("processing_id")
            or mapped.get("asset_id") != item.get("asset_id")
            or not mapped.get("document_version_id")
            or item.get("document_version_id") is not None
            and mapped["document_version_id"] != item["document_version_id"]
        ):
            raise ValueError("Oracle processing/document identities differ")
        for unit in mapped.get("units", []):
            if hashlib.sha256(unit["cleaned_text"].encode()).hexdigest() != unit["text_hash"]:
                raise ValueError("Oracle source unit hash differs")
        if not mapped.get("units"):
            raise ValueError("Oracle source units are unavailable")
    attestation = json.loads(attestation_path.read_text(encoding="utf-8"))
    human_identity(attestation.get("reviewer_id"))
    confirmed = require_oracle_confirmation({"oracle_confirmation": attestation}, digest(retrieval))
    coverage = confirmed["coverage"]
    if (
        not isinstance(coverage, dict)
        or not coverage
        or any(
            not isinstance(k, str)
            or not k.strip()
            or not isinstance(v, list)
            or not v
            or not set(v) <= evidence_ids
            for k, v in coverage.items()
        )
    ):
        raise ValueError(
            "Human coverage must map named required points to these exact evidence IDs"
        )
    destination = source / "oracle" / (case_id + ".json")
    freeze(
        destination,
        {
            "id": case_id,
            "study_hash": digest(study),
            "retrieval": retrieval,
            "oracle_confirmation": confirmed,
            "source_file_sha256": file_hash(retrieval_path),
            "attestation_file_sha256": file_hash(attestation_path),
            "validation_scope": "Supplied attestation, exact content/identity hashes and coverage links only; no automatic human or scientific sufficiency claim. Corpus membership requires the curator's separately verified source acquisition.",
        },
    )
    return {
        "case_id": case_id,
        "artifact": str(destination),
        "reviewer_id": confirmed["reviewer_id"],
        "evidence_sha256": digest(retrieval),
        "human_identity_authenticated": False,
    }
