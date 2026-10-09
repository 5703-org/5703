"""Export real matched source presentations and import actual browser observations."""

from collections import defaultdict
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import statistics

from evaluation.enhancement.protocol import SEED, digest, freeze
from evaluation.enhancement.runner import load, resolve_source

TOOL_VERSION = "highlight_review_v1"
GRADES = {"supported", "partially_supported", "unsupported", "cannot_judge"}


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def segments(text, fragments):
    cuts = {0, len(text)}
    for f in fragments:
        if (
            type(f["start"]) is not int
            or type(f["end"]) is not int
            or not 0 <= f["start"] < f["end"] <= len(text)
            or text[f["start"] : f["end"]] != f["exact_text"]
            or sha(f["exact_text"]) != f["text_hash"]
        ):
            raise ValueError("Fragment differs from immutable source-unit text")
        cuts.update((f["start"], f["end"]))
    bounds = sorted(cuts)
    result = []
    for start, end in zip(bounds, bounds[1:]):
        selected = [f["fragment_id"] for f in fragments if f["start"] <= start and end <= f["end"]]
        result.append(
            {"text": text[start:end], "highlight": bool(selected), "fragment_ids": selected}
        )
    return result


def export_highlight(run: Path, output: Path):
    """Use all eligible published posthoc claims; missing/failed tasks stay in the log."""
    if output.exists():
        raise ValueError("Keep the existing frozen highlight materials")
    manifest = load(run / "run-manifest.json")
    if manifest["experiment"] != "citations":
        raise ValueError("Highlight comparison uses the direct citation experiment")
    source = resolve_source(run, manifest)
    tasks = {t["id"]: t for t in load(source / "private-tasks.json")["tasks"]}
    items, keys, exclusions = [], [], []
    planned_answers = [i for i in manifest["planned"] if i["condition"] == "posthoc_spans"]
    if len({i["id"] for i in manifest["planned"]}) != len(manifest["planned"]):
        raise ValueError("Duplicate scheduled study identity")
    linked_answers, skipped_claims = 0, 0
    for item in manifest["planned"]:
        if item["condition"] != "posthoc_spans":
            continue
        path = run / "results" / (item["id"] + ".json")
        result = load(path) if path.exists() else {}
        outcome = result.get("outcome", {})
        if result and any(result.get(k) != item[k] for k in ("id", "task_id", "condition")):
            raise ValueError("Delivered result differs from scheduled study identity")
        if not result.get("exposure") or not outcome.get("attribution"):
            exclusions.append(
                {
                    "id": item["id"],
                    "reason": "No delivered answer with source attribution",
                    "error": outcome.get("error"),
                }
            )
            continue
        retrieval = load(source / "retrieval" / (item["task_id"] + ".json"))
        if result.get("retrieval_sha256") != digest(retrieval):
            raise ValueError("Result differs from frozen retrieval input")
        fragments = {f["fragment_id"]: f for f in outcome["attribution"]["fragments"]}
        evidence = {e["evidence_id"]: e for e in outcome["evidence"]}
        if len(fragments) != len(outcome["attribution"]["fragments"]) or len(evidence) != len(
            outcome["evidence"]
        ):
            raise ValueError("Duplicate evidence or fragment identity")
        answer = result["exposure"]["response"]["answer_text"]
        before = len(items)
        for claim in outcome["attribution"]["claims"]:
            if claim["answer_field"] != "answer_text" or not claim["fragment_ids"]:
                skipped_claims += claim["answer_field"] == "answer_text"
                continue
            if (
                type(claim["start"]) is not int
                or type(claim["end"]) is not int
                or not 0 <= claim["start"] < claim["end"] <= len(answer)
                or answer[claim["start"] : claim["end"]] != claim["text"]
            ):
                raise ValueError("Claim range differs from the delivered answer")
            grouped = defaultdict(list)
            for identity in claim["fragment_ids"]:
                f = fragments[identity]
                grouped[(f["evidence_id"], f["source_unit_id"])].append(f)
            displays = []
            for (evidence_id, unit_id), selected in grouped.items():
                e = evidence[evidence_id]
                mapping = retrieval["source_map"][e["chunk_id"]]
                unit = next(u for u in mapping["units"] if u["id"] == unit_id)
                text = unit["cleaned_text"]
                if sha(text) != unit["text_hash"]:
                    raise ValueError("Frozen source-unit hash differs")
                for fragment in selected:
                    if (
                        (
                            claim["evidence_ids"]
                            and fragment["evidence_id"] not in claim["evidence_ids"]
                        )
                        or fragment["chunk_id"] != e["chunk_id"]
                        or any(
                            fragment[k] != mapping[k]
                            for k in ("document_version_id", "processing_id", "asset_id")
                        )
                        or any(e[k] != mapping[k] for k in ("processing_id", "asset_id"))
                        or fragment["page"] != unit["page"]
                        or fragment["offset_basis"] != "cleaned_source_unit_unicode"
                        or sha(mapping["chunk_text"]) != mapping["chunk_hash"]
                        or mapping["chunk_text"][fragment["chunk_start"] : fragment["chunk_end"]]
                        != fragment["exact_text"]
                        or not any(
                            s["unit_id"] == unit_id
                            and s["start"] <= fragment["start"] < fragment["end"] <= s["end"]
                            and fragment["chunk_start"]
                            == s["chunk_start"] + fragment["start"] - s["start"]
                            and fragment["chunk_end"] - fragment["chunk_start"]
                            == fragment["end"] - fragment["start"]
                            for s in mapping["spans"]
                        )
                    ):
                        raise ValueError("Fragment source identity or chunk span differs")
                displays.append(
                    {
                        "evidence_id": evidence_id + ":" + unit_id,
                        "source_title": e["source_title"],
                        "locator": f"{e['section']}; PDF physical page {unit['page']}",
                        "text": text,
                        "text_sha256": sha(text),
                        "segments": segments(text, selected),
                    }
                )
            identity = (
                "source_"
                + digest({"run": digest(manifest), "item": item["id"], "claim": claim["claim_id"]})[
                    :16
                ]
            )
            items.append(
                {
                    "id": identity,
                    "question": tasks[item["task_id"]]["question"],
                    "answer_text": answer,
                    "claim": {k: claim[k] for k in ("claim_id", "start", "end", "text")},
                    "evidence": displays,
                }
            )
            keys.append(
                {
                    "id": identity,
                    "item_id": item["id"],
                    "claim_id": claim["claim_id"],
                    "fragments": [fragments[f] for f in claim["fragment_ids"]],
                    "automatic_support": claim.get("support"),
                    "human_reference_grade": None,
                    "displayed_characters": sum(len(d["text"]) for d in displays),
                    "highlighted_characters": sum(
                        len(s["text"]) for d in displays for s in d["segments"] if s["highlight"]
                    ),
                    "exact_mapping_verified": True,
                    "inline_evidence_ids": claim["evidence_ids"],
                }
            )
        if len(items) > before:
            linked_answers += 1
        else:
            exclusions.append(
                {
                    "id": item["id"],
                    "reason": "Delivered answer has no linked answer_text claims",
                    "error": None,
                }
            )
    output.mkdir(parents=True)
    payload = {
        "version": "highlight_review_input_v1",
        "review_version": "week08-" + manifest["split"] + "-source-display-v1",
        "seed": SEED,
        "items": items,
    }
    (output / "participant-input.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    freeze(
        output / "coordinator-only-reference.json",
        {
            "run_sha256": digest(manifest),
            "items": keys,
            "exclusions": exclusions,
            "selection": "Every eligible delivered posthoc answer_text claim, in scheduled order",
            "human_reference_count": 0,
            "planned_task_answers": len(planned_answers),
            "eligible_task_answers": linked_answers,
            "unlinked_answer_text_claims": skipped_claims,
        },
    )
    with (output / "expert-reference-grades.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as stream:
        writer = csv.DictWriter(
            stream, fieldnames=("item_id", "expert_id", "grade", "reason", "completed_at")
        )
        writer.writeheader()
        writer.writerows({"item_id": i["id"]} for i in items)
    for name in ("highlight_review.html", "highlight_review.README.md"):
        shutil.copyfile(Path(__file__).parent / name, output / name)
    return {
        "claims": len(items),
        "planned_task_answers": len(planned_answers),
        "eligible_task_answers": linked_answers,
        "excluded_task_answers": len(exclusions),
        "unlinked_answer_text_claims": skipped_claims,
        "human_observations": 0,
        "displayed_characters": sum(k["displayed_characters"] for k in keys),
        "highlighted_characters": sum(k["highlighted_characters"] for k in keys),
        "linked_claims_without_inline_citations": sum(not k["inline_evidence_ids"] for k in keys),
    }


def browser_schedule(data, participant):
    """Reproduce the published browser's Mulberry32 and JSON.stringify identities."""
    identity = json.dumps(
        [TOOL_VERSION, data["review_version"], data["seed"], participant],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    state = int(sha(identity)[:8], 16)
    mask = 0xFFFFFFFF

    def random():
        nonlocal state
        state = (state + 0x6D2B79F5) & mask
        value = ((state ^ (state >> 15)) * (state | 1)) & mask
        value ^= (value + (((value ^ (value >> 7)) * (value | 61)) & mask)) & mask
        return ((value ^ (value >> 14)) & mask) / 4294967296

    def shuffled(values):
        result = values.copy()
        for index in range(len(result) - 1, 0, -1):
            other = int(random() * (index + 1))
            result[index], result[other] = result[other], result[index]
        return result

    indices = shuffled(list(range(len(data["items"]))))
    flip = random() < 0.5
    mapping = {"A": "highlight", "B": "paragraph"} if flip else {"A": "paragraph", "B": "highlight"}
    first = [
        {
            "item_index": item_index,
            "condition": "highlight" if (index % 2 == 0) != flip else "paragraph",
        }
        for index, item_index in enumerate(indices)
    ]
    second = shuffled(
        [
            {**row, "condition": "paragraph" if row["condition"] == "highlight" else "highlight"}
            for row in first
        ]
    )
    if len(second) > 1 and second[0]["item_index"] == first[-1]["item_index"]:
        second.append(second.pop(0))
    internal = [
        {**row, "presentation_code": "A" if mapping["A"] == row["condition"] else "B"}
        for row in first + second
    ]
    key = [
        {
            "schedule_index": index,
            "item_id": data["items"][row["item_index"]]["id"],
            "claim_id": data["items"][row["item_index"]]["claim"]["claim_id"],
            "presentation_code": row["presentation_code"],
            "condition": row["condition"],
        }
        for index, row in enumerate(internal)
    ]
    return key, mapping, sha(json.dumps(internal, ensure_ascii=False, separators=(",", ":")))


def import_highlight(materials: Path, observations: Path, key_file: Path):
    """Import measured first attempts; keep reopens and incomplete observations separate."""
    raw = observations.read_bytes()
    observed = json.loads(raw)
    key = json.loads(key_file.read_text(encoding="utf-8-sig"))
    dataset_hash = hashlib.sha256((materials / "participant-input.json").read_bytes()).hexdigest()
    data = json.loads((materials / "participant-input.json").read_text(encoding="utf-8"))
    if (
        observed.get("version") != "highlight_review_results_v1"
        or key.get("version") != "highlight_review_key_v1"
    ):
        raise ValueError("Unsupported browser observation or key version")
    for field in ("dataset_sha256", "review_version", "participant_id", "seed", "schedule_sha256"):
        if observed.get(field) != key.get(field):
            raise ValueError("Browser observation and investigator key identities differ")
    if observed["dataset_sha256"] != dataset_hash or not observed["participant_id"]:
        raise ValueError("Actual participant and matching frozen dataset are required")
    if (
        observed.get("tool_version") != TOOL_VERSION
        or key.get("tool_version") != TOOL_VERSION
        or observed["review_version"] != data["review_version"]
        or observed["seed"] != data["seed"]
        or not isinstance(observed["participant_id"], str)
        or len(observed["participant_id"]) > 64
        or observed["participant_id"].strip() != observed["participant_id"]
    ):
        raise ValueError("Browser tool or frozen dataset metadata differs")
    expected, mapping, schedule_hash = browser_schedule(data, observed["participant_id"])
    if (
        key["schedule"] != expected
        or key.get("presentation_mapping") != mapping
        or key["schedule_sha256"] != schedule_hash
    ):
        raise ValueError("Browser schedule or its hash differs from the deterministic assignment")
    schedule = {r["schedule_index"]: r for r in key["schedule"]}
    if (
        type(observed["planned_presentations"]) is not int
        or len(schedule) != observed["planned_presentations"]
    ):
        raise ValueError("Planned presentation count differs")
    allowed = {
        r["id"]
        for r in json.loads((materials / "participant-input.json").read_text(encoding="utf-8"))[
            "items"
        ]
    }
    seen, rows = set(), []
    per_presentation = defaultdict(int)
    for row in observed["attempts"]:
        if (
            type(row["schedule_index"]) is not int
            or type(row["attempt"]) is not int
            or type(row["reopened"]) is not bool
        ):
            raise ValueError("Invalid presentation or attempt type")
        planned = schedule.get(row["schedule_index"])
        if (
            not planned
            or row["item_id"] not in allowed
            or any(row[k] != planned[k] for k in ("item_id", "claim_id", "presentation_code"))
        ):
            raise ValueError("Observation differs from its assigned presentation")
        identity = (row["schedule_index"], row["attempt"])
        if (
            identity in seen
            or row["attempt"] < 1
            or row["support"] not in GRADES
            or row["attempt"] != per_presentation[row["schedule_index"]] + 1
            or row["reopened"] != (row["attempt"] > 1)
        ):
            raise ValueError("Duplicate attempt or invalid actual judgment")
        seen.add(identity)
        per_presentation[row["schedule_index"]] += 1
        if (
            type(row["active_visible_ms"]) is not int
            or type(row["elapsed_wall_ms"]) is not int
            or not (0 <= row["active_visible_ms"] <= row["elapsed_wall_ms"])
            or row["elapsed_wall_ms"] <= 0
        ):
            raise ValueError("Invalid measured timing")
        begin, end = (
            datetime.fromisoformat(row[k].replace("Z", "+00:00"))
            for k in ("started_at", "completed_at")
        )
        if (
            begin.tzinfo is None
            or end.tzinfo is None
            or end <= begin
            or end > datetime.now(timezone.utc)
        ):
            raise ValueError("Actual completion timestamps are required")
        if planned["condition"] not in {"paragraph", "highlight"}:
            raise ValueError("Unknown source-presentation condition")
        rows.append({**row, "condition": planned["condition"]})
    primary = [r for r in rows if r["attempt"] == 1 and not r["reopened"]]
    if [r["schedule_index"] for r in primary] != list(range(len(primary))):
        raise ValueError("First presentations differ from their scheduled order")
    if (
        type(observed.get("completed_presentations")) is not int
        or type(observed.get("remaining_presentations")) is not int
        or observed["completed_presentations"] != len(primary)
        or observed["remaining_presentations"] != len(schedule) - len(primary)
    ):
        raise ValueError("Browser completion denominator differs from recorded attempts")
    by_condition = {
        condition: [r for r in primary if r["condition"] == condition]
        for condition in {r["condition"] for r in primary}
    }
    value = {
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "participant_id": observed["participant_id"],
        "dataset_sha256": dataset_hash,
        "review_version": data["review_version"],
        "schedule_sha256": schedule_hash,
        "planned": len(schedule),
        "first_completed": len(primary),
        "missing": len(schedule) - len(primary),
        "attempts": rows,
        "timing": {
            k: {
                "first_completed": len(v),
                "median_wall_ms": statistics.median(r["elapsed_wall_ms"] for r in v),
                "median_visible_ms": statistics.median(r["active_visible_ms"] for r in v),
            }
            for k, v in by_condition.items()
        },
        "correctness": None,
        "correctness_status": "Requires independently completed expert-reference-grades.csv",
    }
    path = materials / "observation-imports" / (value["source_sha256"] + ".json")
    for previous in (materials / "observation-imports").glob("*.json"):
        if previous.name.endswith(".browser.json"):
            continue
        prior = load(previous)
        if (
            prior["participant_id"] == observed["participant_id"]
            and prior["source_sha256"] != value["source_sha256"]
        ):
            raise ValueError(
                "A different submission for this participant already exists; preserve and review it explicitly"
            )
    freeze(path, value)
    path.with_suffix(".browser.json").write_bytes(raw)
    return {
        "actual_participant": observed["participant_id"],
        "first_completed": len(primary),
        "artifact": str(path),
    }


def import_reference(materials: Path, ratings: Path):
    dataset_hash = hashlib.sha256((materials / "participant-input.json").read_bytes()).hexdigest()
    allowed = {
        r["id"]
        for r in json.loads((materials / "participant-input.json").read_text(encoding="utf-8"))[
            "items"
        ]
    }
    rows = []
    with ratings.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if not row.get("grade"):
                continue
            if (
                row["item_id"] not in allowed
                or row["grade"] not in GRADES
                or not row["expert_id"].strip()
                or not row["reason"].strip()
            ):
                raise ValueError("Actual expert identity, item, grade and reason are required")
            stamp = datetime.fromisoformat(row["completed_at"])
            if stamp.tzinfo is None or stamp > datetime.now(timezone.utc):
                raise ValueError("Use an actual timezone-aware completion timestamp")
            rows.append(row)
    if not rows or len({r["item_id"] for r in rows}) != len(rows):
        raise ValueError("Completed unique expert decisions are required")
    target = (
        materials
        / "reference-imports"
        / (hashlib.sha256(ratings.read_bytes()).hexdigest() + ".json")
    )
    freeze(
        target,
        {
            "ratings": rows,
            "source_sha256": hashlib.sha256(ratings.read_bytes()).hexdigest(),
            "dataset_sha256": dataset_hash,
        },
    )
    return {"actual_reference_grades": len(rows), "artifact": str(target)}


def summarise(materials: Path, reference: Path | None = None):
    dataset_hash = hashlib.sha256((materials / "participant-input.json").read_bytes()).hexdigest()
    reference_data = load(reference) if reference else None
    if reference_data and reference_data.get("dataset_sha256") != dataset_hash:
        raise ValueError("Expert reference belongs to a different frozen dataset")
    labels = {r["item_id"]: r["grade"] for r in reference_data["ratings"]} if reference_data else {}
    observations = [
        load(p)
        for p in (materials / "observation-imports").glob("*.json")
        if not p.name.endswith(".browser.json")
    ]
    if any(o["dataset_sha256"] != dataset_hash for o in observations):
        raise ValueError("Imported observation belongs to a different frozen dataset")
    if len({o["participant_id"] for o in observations}) != len(observations):
        raise ValueError("Duplicate participant imports cannot inflate the denominator")
    rows = [
        {**r, "participant_id": o["participant_id"]}
        for o in observations
        for r in o["attempts"]
        if r["attempt"] == 1 and not r["reopened"]
    ]
    groups = defaultdict(dict)
    for row in rows:
        groups[(row["participant_id"], row["item_id"])][row["condition"]] = row
    pairs = [p for p in groups.values() if set(p) == {"paragraph", "highlight"}]
    differences = [
        p["highlight"]["active_visible_ms"] - p["paragraph"]["active_visible_ms"] for p in pairs
    ]
    conditions = {}
    for condition in ("paragraph", "highlight"):
        subset = [r for r in rows if r["condition"] == condition]
        scored = [
            r for r in subset if r["item_id"] in labels and labels[r["item_id"]] != "cannot_judge"
        ]
        conditions[condition] = {
            "observations": len(subset),
            "correctness_denominator": len(scored),
            "correct": sum(r["support"] == labels[r["item_id"]] for r in scored),
            "mean_visible_ms": statistics.mean(r["active_visible_ms"] for r in subset)
            if subset
            else None,
        }
    return {
        "actual_participants": len(observations),
        "planned_presentations": sum(o["planned"] for o in observations),
        "first_completed": len(rows),
        "missing_presentations": sum(o["planned"] for o in observations) - len(rows),
        "paired_presentations": len(pairs),
        "mean_paired_visible_ms_difference": statistics.mean(differences) if differences else None,
        "conditions": conditions,
        "expert_reference_count": len(labels),
        "analysis_scope": "Descriptive actual browser observations; repeated exposure and order may influence timing. No learning-gain inference.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    export = sub.add_parser("export")
    export.add_argument("--run", type=Path, required=True)
    export.add_argument("--output", type=Path, required=True)
    imported = sub.add_parser("import")
    imported.add_argument("--materials", type=Path, required=True)
    imported.add_argument("--observations", type=Path, required=True)
    imported.add_argument("--key", type=Path, required=True)
    expert = sub.add_parser("import-reference")
    expert.add_argument("--materials", type=Path, required=True)
    expert.add_argument("--ratings", type=Path, required=True)
    summary = sub.add_parser("summary")
    summary.add_argument("--materials", type=Path, required=True)
    summary.add_argument("--reference", type=Path)
    args = parser.parse_args()
    if args.operation == "export":
        result = export_highlight(args.run.resolve(), args.output.resolve())
    elif args.operation == "import":
        result = import_highlight(
            args.materials.resolve(), args.observations.resolve(), args.key.resolve()
        )
    elif args.operation == "import-reference":
        result = import_reference(args.materials.resolve(), args.ratings.resolve())
    else:
        result = summarise(args.materials.resolve(), args.reference)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
