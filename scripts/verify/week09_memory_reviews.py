"""Blinded memory application packets and strict, non-imputing human import."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import random


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


FIELDS = ["review_id", "reviewer_id", "preference_applicable", "preference_followed", "notes"]


def export(study, output):
    if output.exists():
        raise ValueError("Preserve existing reviewer materials")
    plan = read(study / "frozen-study.json")
    cases = {case["id"]: case for case in plan["cases"]}
    paths = sorted((study / "private/outcomes").glob("*.json"))
    random.Random(570309).shuffle(paths)
    packets, mapping = [], {}
    for index, path in enumerate(paths, 1):
        result = read(path)
        case = cases[result["case_id"]]
        outcome = result.get("outcome") or {}
        response = outcome.get("response")
        rid = f"MR-{index:03}"
        packets.append(
            {
                "review_id": rid,
                "question": case["question"],
                "saved_profile": {"level": "intermediate", "style": "concise"},
                "saved_statement": case["entry"]["content"],
                "saved_scope": case["entry"]["scope"],
                "visible_response": response,
                "delivery_status": "delivered"
                if response and not outcome.get("error")
                else "unavailable",
                "source_material": [
                    {
                        k: ev.get(k)
                        for k in ["evidence_id", "text", "source_title", "section", "pages"]
                    }
                    for ev in outcome.get("evidence", [])
                ],
            }
        )
        mapping[rid] = {
            "case_id": result["case_id"],
            "arm": result["arm"],
            "outcome_sha256": sha(path),
            "selected": bool(case["states"][result["arm"]]["entries"]),
            "delivery_status": packets[-1]["delivery_status"],
        }
    write(output / "review-packets.json", packets)
    write(output / "coordinator-only/mapping.json", mapping)
    write(
        output / "coordinator-only/manifest.json",
        {
            "packets_sha256": sha(output / "review-packets.json"),
            "mapping_sha256": sha(output / "coordinator-only/mapping.json"),
        },
    )
    for number in (1, 2):
        with (output / f"reviewer-{number}.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows({"review_id": card["review_id"]} for card in packets)
    (output / "SCORING_GUIDE.md").write_text(
        "# Memory application review\n\n"
        "Review each card independently. The saved statement is the learner's exact authored preference; "
        "the question and any explicit current instruction determine its applicability. "
        "Current instructions take priority, then applicable subject-specific memory, then the concise profile default.\n\n"
        "Enter your own reviewer identifier. For `preference_applicable`, use 1 when the saved preference "
        "applies to this question, 0 when it does not, or NA when its scope is ambiguous. "
        "For `preference_followed`, assess whether the delivered answer follows the applicable instruction hierarchy: "
        "1=yes, 0=no, NA=no assessable answer or insufficient information. "
        "Detailed means supported explanation with useful causal steps or necessary conditions; word count alone is insufficient. "
        "Concise means direct, economical wording that retains necessary qualifications. "
        "Record concrete reasons in notes. Leave ratings blank until you have actually reviewed the card.\n\n"
        "Reviewer 1 and reviewer 2 work independently. The coordinator retains the mapping folder and imports "
        "both files with `python -m scripts.verify.week09_memory_reviews import --output <review-folder> "
        "--reviews <reviewer-1.csv> <reviewer-2.csv> --result <new-result.json>`. "
        "Blank cells remain missing; they never become passing scores.\n",
        encoding="utf-8",
    )


def import_reviews(output, files, result_path):
    if result_path.exists():
        raise ValueError("Preserve previous human result imports")
    manifest = read(output / "coordinator-only/manifest.json")
    assert sha(output / "review-packets.json") == manifest["packets_sha256"]
    assert sha(output / "coordinator-only/mapping.json") == manifest["mapping_sha256"]
    mapping = read(output / "coordinator-only/mapping.json")
    ratings, seen = [], set()
    for path in files:
        local_seen = set()
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != FIELDS:
                raise ValueError("Reviewer CSV columns differ from the frozen form")
            for row in reader:
                rid = row["review_id"]
                if rid not in mapping or rid in local_seen:
                    raise ValueError("Unknown or duplicate review ID")
                local_seen.add(rid)
                values = [
                    row[key].strip() for key in ["preference_applicable", "preference_followed"]
                ]
                row["preference_applicable"], row["preference_followed"] = values
                if any(x not in {"", "0", "1", "NA"} for x in values):
                    raise ValueError("Ratings must be blank, 0, 1 or NA")
                if any(values):
                    reviewer = row["reviewer_id"].strip()
                    if not reviewer or (rid, reviewer) in seen:
                        raise ValueError("A unique independent reviewer identifier is required")
                    seen.add((rid, reviewer))
                    if mapping[rid]["delivery_status"] == "unavailable" and values[1] in {"0", "1"}:
                        raise ValueError("An unavailable answer cannot receive a compliance score")
                    ratings.append({**row, **mapping[rid]})
    arms = {}
    for arm in ("rules", "semantic"):
        records = [r for r in ratings if r["arm"] == arm]
        scored = [
            int(r["preference_followed"]) for r in records if r["preference_followed"] in {"0", "1"}
        ]
        applicable = [r for r in records if r["preference_applicable"] in {"0", "1"}]
        arms[arm] = {
            "compliance_ratings": len(scored),
            "compliance_mean": sum(scored) / len(scored) if scored else None,
            "false_selection_ratings": sum(
                r["selected"] and r["preference_applicable"] == "0" for r in applicable
            ),
            "omission_ratings": sum(
                not r["selected"] and r["preference_applicable"] == "1" for r in applicable
            ),
        }
    write(
        result_path,
        {
            "human_ratings": len(ratings),
            "missing_values_imputed": 0,
            "arms": arms,
            "ratings": ratings,
        },
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["export", "import"])
    parser.add_argument("--study", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reviews", nargs="+", type=Path)
    parser.add_argument("--result", type=Path)
    args = parser.parse_args()
    if args.action == "export":
        export(args.study, args.output)
    else:
        import_reviews(args.output, args.reviews, args.result)


if __name__ == "__main__":
    main()
