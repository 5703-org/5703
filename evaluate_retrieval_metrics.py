"""Calculate Recall@K, Hit Rate, MRR and nDCG for R0--R3 retrieval outputs.

Inputs are JSONL files.  ``qrels`` needs question_id, chunk_id and human_label.
``runs`` needs question_id, variant and either ``evidence`` or ``hits``.
Only completed human labels are used; blank/null labels never become relevance.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import json
import math
from pathlib import Path


GRADE = {"Relevant": 3, "Partially relevant": 1, "Not relevant": 0}


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path}:{number}") from exc
    return rows


def normalise_run_rows(rows: list[dict]) -> list[dict]:
    normalised = []
    for row in rows:
        evidence = row.get("evidence", row.get("hits"))
        if evidence is None:
            raise ValueError("Each run row must contain evidence or hits")
        for rank, hit in enumerate(evidence, start=1):
            normalised.append(
                {
                    "question_id": row["question_id"],
                    "variant": row["variant"],
                    "chunk_id": hit["chunk_id"],
                    "rank": int(hit.get("rank", rank)),
                }
            )
    return normalised


def dcg(grades: list[int]) -> float:
    return sum((2**grade - 1) / math.log2(rank + 1) for rank, grade in enumerate(grades, start=1))


def metrics_for_question(retrieved: list[str], qrels: dict[str, int], k: int) -> dict:
    grades = [qrels.get(chunk_id, 0) for chunk_id in retrieved[:k]]
    relevant = {chunk_id for chunk_id, grade in qrels.items() if grade > 0}
    first_rank = next((rank for rank, chunk_id in enumerate(retrieved[:k], 1) if chunk_id in relevant), None)
    recall = len(set(retrieved[:k]) & relevant) / len(relevant) if relevant else None
    ideal = sorted(qrels.values(), reverse=True)[:k]
    return {
        "recall": recall,
        "hit_rate": 1.0 if first_rank else 0.0,
        "mrr": 1.0 / first_rank if first_rank else 0.0,
        "ndcg": dcg(grades) / dcg(ideal) if dcg(ideal) else None,
    }


def average(values: list[float | None]) -> float | None:
    usable = [value for value in values if value is not None]
    return round(sum(usable) / len(usable), 6) if usable else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qrels", required=True, type=Path)
    parser.add_argument("--runs", required=True, type=Path)
    parser.add_argument("--output-csv", required=True, type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--k", type=int, choices=(3, 5, 10), default=5)
    args = parser.parse_args()

    qrels_by_question: dict[str, dict[str, int]] = defaultdict(dict)
    for row in read_jsonl(args.qrels):
        label = row.get("human_label")
        if label in (None, ""):
            continue
        if label not in GRADE:
            raise ValueError(f"Unknown human_label: {label}")
        qrels_by_question[row["question_id"]][row["chunk_id"]] = GRADE[label]
    if not qrels_by_question:
        raise ValueError("No completed human relevance labels found; metrics must not be fabricated")

    runs: dict[tuple[str, str], list[tuple[int, str]]] = defaultdict(list)
    for row in normalise_run_rows(read_jsonl(args.runs)):
        runs[(row["variant"], row["question_id"])].append((row["rank"], row["chunk_id"]))

    details, grouped = [], defaultdict(list)
    for (variant, question_id), candidates in sorted(runs.items()):
        if question_id not in qrels_by_question:
            continue
        ordered = [chunk_id for _, chunk_id in sorted(candidates)]
        values = metrics_for_question(ordered, qrels_by_question[question_id], args.k)
        details.append({"variant": variant, "question_id": question_id, **values})
        grouped[variant].append(values)

    summary = []
    for variant, rows in sorted(grouped.items()):
        summary.append(
            {
                "variant": variant,
                "questions_scored": len(rows),
                "Recall@K": average([row["recall"] for row in rows]),
                "Hit_Rate@K": average([row["hit_rate"] for row in rows]),
                "MRR@K": average([row["mrr"] for row in rows]),
                "nDCG@K": average([row["ndcg"] for row in rows]),
            }
        )
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary[0]) if summary else ["variant"])
        writer.writeheader()
        writer.writerows(summary)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps({"k": args.k, "summary": summary, "per_question": details}, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"status": "succeeded", "variants": len(summary), "k": args.k}))


if __name__ == "__main__":
    main()
