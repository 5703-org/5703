"""Blinded independent-review forms and strict append-only human result import."""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import random

from evaluation.enhancement.protocol import RUBRIC, RUBRIC_VERSION, SEED, digest, freeze
from evaluation.enhancement.runner import load, resolve_source


def blind_exposure(exposure):
    if not exposure:
        return None
    return {
        "response": exposure.get("response"),
        "sources": [
            {k: v.get(k) for k in ("evidence_id", "title", "section", "pages", "preview")}
            for v in exposure.get("citation_views", [])
        ],
    }


SCORES = (
    "supported",
    "specific_help",
    "within_scope",
    "fact_error",
    "citation_complete",
    "memory_misuse",
    "complete_answer",
)
FIELDS = ("review_id", "reviewer_id", "rubric_version", *SCORES, "reason", "completed_at")


def export_reviews(run: Path, output: Path):
    if output.exists():
        raise ValueError("Keep existing review materials; choose a new output directory")
    manifest = load(run / "run-manifest.json")
    tasks = {
        t["id"]: t for t in load(resolve_source(run, manifest) / "private-tasks.json")["tasks"]
    }
    output.mkdir(parents=True)
    private = []
    material = []
    for item in manifest["planned"]:
        path = run / "results" / (item["id"] + ".json")
        result = load(path) if path.exists() else None
        review_id = (
            "review_" + digest({"run": digest(manifest), "item": item["id"], "seed": SEED})[:16]
        )
        private.append(
            {
                "review_id": review_id,
                "item_id": item["id"],
                "task_id": item["task_id"],
                "condition": item["condition"],
                "turn": item["turn"],
            }
        )
        task = tasks[item["task_id"]]
        outcome = (result or {}).get("outcome", {})
        material.append(
            {
                "review_id": review_id,
                "question": task["question"],
                "round": item["turn"],
                "request": task["turns"][item["turn"] - 1]
                if manifest["experiment"] == "hints"
                else "Give a complete answer",
                "reference_answer": task["critical_answer"],
                "help_allowance": task["help_allowances"][item["turn"] - 1]
                if manifest["experiment"] == "hints"
                else "A complete direct explanation is requested. The final result and full supporting source text are allowed; do not apply hint withholding limits.",
                "delivered_content": blind_exposure((result or {}).get("exposure")),
                "previous_delivered_content": [
                    blind_exposure(e) for e in (result or {}).get("prior_exposure", [])
                ],
                "cited_sources": [
                    {
                        k: e.get(k)
                        for k in (
                            "evidence_id",
                            "source_title",
                            "section",
                            "pages",
                            "locator",
                            "text",
                            "text_hash",
                        )
                    }
                    for e in outcome.get("evidence", [])
                    if e["evidence_id"] in (outcome.get("response") or {}).get("citations", [])
                ],
                "reference_source_scope": "These cited passages are verification references. Only delivered_content and previous_delivered_content describe actual learner exposure.",
                "execution_status": "answer_available"
                if (result or {}).get("exposure")
                else "no_delivered_answer",
            }
        )
    freeze(
        output / "coordinator-only-condition-key.json",
        {"run_manifest_sha256": digest(manifest), "run_directory": str(run), "items": private},
    )
    # Reviewers receive different orders and no method/condition/online/automatic scores.
    for reviewer in (1, 2):
        rows = material.copy()
        random.Random(SEED + reviewer).shuffle(rows)
        folder = output / f"reviewer-{reviewer}"
        folder.mkdir()
        freeze(
            folder / "review-material.json",
            {"rubric": RUBRIC, "items": rows, "assigned_reviewer_slot": reviewer},
        )
        with (folder / "ratings.csv").open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            for row in rows:
                writer.writerow({"review_id": row["review_id"], "rubric_version": RUBRIC_VERSION})
        cards = []
        for row in rows:
            # Pure text rendering avoids treating retrieved content as executable markup.
            cards.append(
                "<details><summary>"
                + html.escape(row["review_id"] + " · round " + str(row["round"]))
                + "</summary><pre>"
                + html.escape(json.dumps(row, indent=2, ensure_ascii=False))
                + "</pre></details>"
            )
        (folder / "review.html").write_text(
            "<!doctype html><html lang=en><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>Independent learning-assistant review</title><style>body{font:16px system-ui;max-width:1000px;margin:30px auto;padding:16px}summary{cursor:pointer;padding:12px;border-bottom:1px solid #ccc}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:15px/1.5 system-ui}</style><h1>Independent learning-assistant review</h1><p>Use the rubric and enter your own ratings in ratings.csv. Condition labels and automatic ratings are hidden.</p>"
            + "\n".join(cards)
            + "</html>",
            encoding="utf-8",
        )
    (output / "SCORING_GUIDE.md").write_text(
        "# Independent human review\n\nTwo people score their assigned materials independently. Keep the coordinator-only key separate until both original rating files have been imported. Do not share scores during the first pass.\n\n"
        "Use your own reviewer identifier, the supplied rubric version, 0/1 for each score, a brief source-based reason and an ISO 8601 completion timestamp. Leave unfinished rows blank. An unavailable answer is retained in the study denominator; enter a reason if you review that failure. Reference annotations are developer-authored: record disagreements rather than treating them as unquestionable labels.\n\n"
        + "\n".join(f"- **{name}**: {meaning}" for name, meaning in RUBRIC["dimensions"].items())
        + "\n- **complete_answer**: the direct answer covers the requested relationships and essential conditions. For a restrained hint, use 0 when the complete solution is intentionally left to the learner.\n\n"
        "A valid hint requires supported=1, specific_help=1 and within_scope=1. Review the answer, short answer, suggestions, ordinary source text and previous delivered turns together. An exposed answer inside a citation counts as exposure.\n\n"
        "Run `python -m scripts.verify.enhancement import-review --materials PATH --ratings PATH_TO_CSV --reviewer YOUR_ID`. Imports validate identities, scores, rubric and timestamps and preserve the original file with its hash. Revisions use a new file and are linked to prior imports. After two imports, use `review-summary`; disagreements and automatic-to-human comparisons are exported without replacing original ratings. A separate adjudication file can record agreed decisions after discussion.\n\n"
        "Use `python -m scripts.verify.enhancement import-adjudication --materials PATH --ratings DECISIONS.csv --adjudicator YOUR_ID` for disputed items after both independent imports. This separate file uses the same columns and records the discussion rationale. It preserves both original scores.\n\n"
        "Highlight timing is a separate paired interface exercise using highlight_review.html and real study data. Timing results are observations of the review interface, not evidence of learning gains.\n",
        encoding="utf-8",
    )
    return {"items": len(material), "reviewers": 2, "ratings_completed": 0}


def import_review(materials: Path, ratings: Path, reviewer: str):
    if not reviewer.strip() or len(reviewer) > 80:
        raise ValueError("A bounded actual reviewer identifier is required")
    key = load(materials / "coordinator-only-condition-key.json")
    allowed = {i["review_id"] for i in key["items"]}
    with ratings.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if set(reader.fieldnames or []) != set(FIELDS):
            raise ValueError("CSV columns differ from the supplied review form")
        rows = list(reader)
    seen = set()
    completed = []
    for row in rows:
        if row["review_id"] not in allowed or row["review_id"] in seen:
            raise ValueError("Unknown or duplicate blinded item")
        seen.add(row["review_id"])
        if not any(row[k].strip() for k in (*SCORES, "reviewer_id", "reason", "completed_at")):
            continue
        if row["reviewer_id"] != reviewer or row["rubric_version"] != RUBRIC_VERSION:
            raise ValueError("Reviewer or rubric identity mismatch")
        if any(row[k] not in {"0", "1"} for k in SCORES) or not row["reason"].strip():
            raise ValueError("Completed ratings need every binary score and a reason")
        stamp = datetime.fromisoformat(row["completed_at"])
        if stamp.tzinfo is None or stamp > datetime.now(timezone.utc):
            raise ValueError("Use a timezone-aware completion timestamp no later than import")
        completed.append({**row, **{k: int(row[k]) for k in SCORES}})
    if not completed:
        raise ValueError("No actual completed human ratings were supplied")
    import hashlib

    raw_hash = hashlib.sha256(ratings.read_bytes()).hexdigest()
    path = materials / "imports" / (raw_hash + ".json")
    if path.exists():
        prior_import = load(path)
        if prior_import["reviewer_id"] != reviewer:
            raise ValueError("Existing import belongs to a different reviewer")
        return {
            "reviewer_id": reviewer,
            "ratings_imported": len(prior_import["submitted_ratings"]),
            "artifact": str(path),
        }
    prior = (
        sorted((materials / "imports").glob("*.json")) if (materials / "imports").exists() else []
    )
    supersedes = [p.name for p in prior if load(p)["reviewer_id"] == reviewer]
    existing_reviewers = {load(p)["reviewer_id"] for p in prior}
    if reviewer not in existing_reviewers and len(existing_reviewers) >= 2:
        raise ValueError(
            "Two independent reviewer identities are already assigned; adjudication uses its separate import"
        )
    prior_values = [load(p) for p in prior]
    superseded_names = {n for item in prior_values for n in item["supersedes"]}
    previous_rows = {
        r["review_id"]: r
        for item in prior_values
        if item["reviewer_id"] == reviewer
        and item["source_sha256"] + ".json" not in superseded_names
        for r in item["ratings"]
    }
    previous_rows.update({r["review_id"]: r for r in completed})
    value = {
        "reviewer_id": reviewer,
        "rubric_version": RUBRIC_VERSION,
        "source_sha256": raw_hash,
        "ratings": list(previous_rows.values()),
        "submitted_ratings": completed,
        "supersedes": supersedes,
    }
    freeze(path, value)
    (path.parent / (raw_hash + ".csv")).write_bytes(ratings.read_bytes())
    return {"reviewer_id": reviewer, "ratings_imported": len(completed), "artifact": str(path)}


def agreement(materials: Path, run_path: Path | None = None):
    imports = (
        [load(p) for p in (materials / "imports").glob("*.json")]
        if (materials / "imports").exists()
        else []
    )
    superseded = {name for item in imports for name in item["supersedes"]}
    active = [i for i in imports if i["source_sha256"] + ".json" not in superseded]
    by_item = defaultdict(list)
    for item in active:
        for row in item["ratings"]:
            by_item[row["review_id"]].append(row)
    pairs = [
        sorted(rows, key=lambda r: r["reviewer_id"])
        for rows in by_item.values()
        if len({r["reviewer_id"] for r in rows}) == 2 and len(rows) == 2
    ]
    metrics = {}
    for dimension in SCORES:
        n = len(pairs)
        matches = sum(p[0][dimension] == p[1][dimension] for p in pairs)
        p1 = sum(p[0][dimension] for p in pairs) / n if n else None
        p2 = sum(p[1][dimension] for p in pairs) / n if n else None
        expected = p1 * p2 + (1 - p1) * (1 - p2) if n else None
        observed = matches / n if n else None
        metrics[dimension] = {
            "paired": n,
            "agreement": observed,
            "cohen_kappa": (observed - expected) / (1 - expected) if n and expected != 1 else None,
        }
    key = load(materials / "coordinator-only-condition-key.json")
    automatic_comparisons = []
    if run_path or key.get("run_directory"):
        identifiers = {r["review_id"]: r["item_id"] for r in key["items"]}
        for rows in by_item.values():
            for row in rows:
                path = (
                    Path(run_path or key["run_directory"])
                    / "judgments"
                    / (identifiers[row["review_id"]] + ".json")
                )
                judge = load(path).get("judgment") if path.exists() else None
                if judge:
                    automatic_comparisons.append(
                        {
                            "review_id": row["review_id"],
                            "reviewer_id": row["reviewer_id"],
                            "agreement": {d: row[d] == judge[d] for d in SCORES},
                        }
                    )
    return {
        "actual_reviewers": len({i["reviewer_id"] for i in active}),
        "actual_ratings": sum(len(i["ratings"]) for i in active),
        "agreement": metrics,
        "disagreements": [p for p in pairs if any(p[0][d] != p[1][d] for d in SCORES)],
        "adjudication": [load(p) for p in sorted((materials / "adjudications").glob("*.json"))]
        if (materials / "adjudications").exists()
        else [],
        "automatic_human_comparisons": automatic_comparisons,
    }


def import_adjudication(materials: Path, ratings: Path, adjudicator: str):
    """Separate agreed decisions never overwrite either original independent rating."""
    report = agreement(materials)
    if report["actual_reviewers"] != 2:
        raise ValueError("Import both independent reviewers before adjudication")
    disputed = {pair[0]["review_id"] for pair in report["disagreements"]}
    with ratings.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if set(reader.fieldnames or []) != set(FIELDS):
            raise ValueError("Use the same rating columns for the separate adjudication form")
        rows = list(reader)
    if not rows or not adjudicator.strip() or len({r["review_id"] for r in rows}) != len(rows):
        raise ValueError("A named adjudicator and unique decisions are required")
    for row in rows:
        if (
            row["review_id"] not in disputed
            or row["reviewer_id"] != adjudicator
            or row["rubric_version"] != RUBRIC_VERSION
        ):
            raise ValueError(
                "Adjudication must identify a disputed item, adjudicator and current rubric"
            )
        if any(row[d] not in {"0", "1"} for d in SCORES) or not row["reason"].strip():
            raise ValueError("All adjudication scores and a discussion rationale are required")
        stamp = datetime.fromisoformat(row["completed_at"])
        if stamp.tzinfo is None or stamp > datetime.now(timezone.utc):
            raise ValueError("Adjudication completion needs an actual timezone-aware timestamp")
    import hashlib

    sha = hashlib.sha256(ratings.read_bytes()).hexdigest()
    destination = materials / "adjudications" / (sha + ".json")
    freeze(
        destination,
        {
            "source_sha256": sha,
            "adjudicator": adjudicator,
            "decisions": [{**r, **{d: int(r[d]) for d in SCORES}} for r in rows],
        },
    )
    destination.with_suffix(".csv").write_bytes(ratings.read_bytes())
    return {"adjudicated": len(rows), "artifact": str(destination)}
