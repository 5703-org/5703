"""Create a deduplicated corpus-v5 relevance-review pool from retrieval runs.

Input files are JSON outputs produced by ``reproducible_retrieval_query.py``
or the existing ``retrieval_comparison.py`` diagnostic.  The output JSONL has
one Question--Chunk pair per line and leaves the human judgement blank.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Iterable


REQUIRED_VARIANTS = {"R0", "R1", "R2", "R3"}
LABELS = ("Relevant", "Partially relevant", "Not relevant")


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} is not valid JSON") from exc


def _records(report: dict, source_file: str) -> Iterable[dict]:
    """Support both one-query output and the R0--R3 comparison report."""
    if "hits" in report:
        if report.get("status") != "succeeded":
            return
        yield {**report, "source_file": source_file}
        return

    for item in report.get("results", []):
        if item.get("status") != "succeeded":
            continue
        yield {
            "question_id": item["question_id"],
            "question": item["question"],
            "variant": item["variant"],
            "top_k": item["top_k"],
            "hits": item["hits"],
            "release_id": report.get("release_id"),
            "configuration": report.get("configuration", {}),
            "manifest_hashes": report.get("manifest_hashes", {}),
            "source_file": source_file,
        }


def _source_location(hit: dict) -> str:
    parts = [
        str(hit.get("document") or hit.get("source") or hit.get("book") or ""),
        str(hit.get("chapter") or ""),
        str(hit.get("page") or hit.get("page_number") or ""),
    ]
    return " | ".join(part for part in parts if part)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", nargs="+", required=True, help="v5 retrieval JSON outputs")
    parser.add_argument("--output-jsonl", required=True)
    parser.add_argument("--output-csv", required=True)
    args = parser.parse_args()

    pooled: dict[tuple[str, str], dict] = {}
    variants_by_question: dict[str, set[str]] = {}
    release_ids: set[object] = set()
    corpus_signatures: set[str] = set()

    for filename in args.inputs:
        report = _load_json(Path(filename))
        for record in _records(report, filename):
            configuration = record.get("configuration", {})
            if configuration.get("embedding_model") not in (None, "intfloat/e5-small-v2"):
                raise ValueError(f"{filename} does not use the required E5-small-v2 configuration")
            if configuration.get("dimension") not in (None, 384):
                raise ValueError(f"{filename} does not use 384-dimensional embeddings")

            release_ids.add(record.get("release_id"))
            manifest = record.get("manifest_hashes", {})
            signature = json.dumps(manifest, sort_keys=True)
            if signature != "{}":
                corpus_signatures.add(signature)

            question_id = record["question_id"]
            variants_by_question.setdefault(question_id, set()).add(record["variant"])
            for hit in record["hits"]:
                key = (question_id, hit["chunk_id"])
                row = pooled.setdefault(
                    key,
                    {
                        "question_id": question_id,
                        "question": record["question"],
                        "chunk_id": hit["chunk_id"],
                        "text": hit["text"],
                        "source_location": _source_location(hit),
                        "text_hash": hit.get("text_hash", ""),
                        "retrieved_by": [],
                        "best_rank": hit.get("rank", 10**9),
                        "human_label": "",
                        "reviewer": "",
                        "review_notes": "",
                    },
                )
                row["retrieved_by"].append(
                    {"variant": record["variant"], "rank": hit.get("rank"), "score": hit.get("score")}
                )
                row["best_rank"] = min(row["best_rank"], hit.get("rank", 10**9))

    if len(release_ids - {None}) > 1 or len(corpus_signatures) > 1:
        raise ValueError("Do not mix corpus releases or source mappings in one relevance-review pool")

    missing = {
        question_id: sorted(REQUIRED_VARIANTS - variants)
        for question_id, variants in variants_by_question.items()
        if REQUIRED_VARIANTS - variants
    }
    if missing:
        raise ValueError(f"Each question needs R0--R3 candidates; missing variants: {missing}")

    rows = sorted(pooled.values(), key=lambda row: (row["question_id"], row["best_rank"], row["chunk_id"]))
    jsonl_path = Path(args.output_jsonl)
    csv_path = Path(args.output_csv)
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    jsonl_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8"
    )

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "question_id", "question", "chunk_id", "source_location", "text",
                "retrieved_by", "best_rank", "human_label", "reviewer", "review_notes",
            ),
        )
        writer.writeheader()
        for row in rows:
            flat = dict(row)
            flat["retrieved_by"] = json.dumps(row["retrieved_by"], ensure_ascii=False)
            writer.writerow({key: flat[key] for key in writer.fieldnames})

    print(
        json.dumps(
            {
                "status": "succeeded",
                "pairs": len(rows),
                "labels": list(LABELS),
                "release_id": next(iter(release_ids - {None}), None),
                "jsonl": str(jsonl_path),
                "csv": str(csv_path),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
