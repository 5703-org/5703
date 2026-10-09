"""Measure fixed 5/10/20 CPU rerank arms over a frozen real-corpus candidate replay."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import time

from retrieval.chat import load_policy, rerank_candidates
from retrieval.cpu_backend import file_hash, torch_runtime
from scripts.verify.cpu_backend_replay import corpus, dump, process_memory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Choose a new budget evidence directory")
    reference_manifest = json.loads(
        (args.reference / "frozen-input.json").read_text(encoding="utf-8")
    )
    rows, _, identity = corpus(args.bundle)
    if identity != reference_manifest["corpus"]:
        raise ValueError("Fixed-budget replay must use the identical official corpus")
    mapping = {row["chunk_id"]: row for row in rows}
    args.output.mkdir(parents=True)
    frozen = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "budgets": [5, 10, 20],
        "reference_manifest_sha256": file_hash(args.reference / "frozen-input.json"),
        "source_cases": {
            case["id"]: file_hash(args.reference / f"{case['id']}.json")
            for case in reference_manifest["cases"]
        },
        "corpus": identity,
        "runtime": torch_runtime(2),
        "repeats": 3,
        "scope": "Fresh CPU scoring of frozen actual candidates, against reference top-five retention. No answer-quality, citation-support or latency-SLO judgment.",
        "answer_model_calls": 0,
        "changes_adaptive_fit": False,
    }
    dump(args.output / "frozen-input.json", frozen)
    base = load_policy("configs/retrieval/chat_hybrid_minilm.json")
    results = []
    for case in reference_manifest["cases"]:
        reference = json.loads((args.reference / f"{case['id']}.json").read_text(encoding="utf-8"))
        reference_ids = reference["backends"]["torch_2"]["ordered_ids"][:5]
        result = {**case, "arms": {}}
        for budget in (5, 10, 20):
            candidates = [mapping[cid] for cid in reference["candidate_ids"][:budget]]
            policy = dict(
                base,
                version="chat_hybrid_rerank_v2",
                reranker_device="cpu",
                reranker_runtime=torch_runtime(2),
                adaptive_policy=None,
            )
            measurements = []
            try:
                for repeat in range(3):
                    start = time.perf_counter()
                    ranked, _ = rerank_candidates(case["query"], candidates, policy)
                    measurements.append(
                        {
                            "phase": "first_observation"
                            if not results and budget == 5 and repeat == 0
                            else "warm",
                            "elapsed_ms": (time.perf_counter() - start) * 1000,
                        }
                    )
                actual_ids = [row["chunk_id"] for row in ranked[:5]]
                result["arms"][str(budget)] = {
                    "status": "completed",
                    "measurements": measurements,
                    "top5_ids": actual_ids,
                    "reference_top5_retained": len(set(actual_ids) & set(reference_ids)),
                    "reference_top5_order_equal": actual_ids == reference_ids,
                    "missing_reference_ids": sorted(set(reference_ids) - set(actual_ids)),
                }
            except Exception as exc:
                result["arms"][str(budget)] = {
                    "status": "failed",
                    "measurements": measurements,
                    "error": type(exc).__name__,
                    "detail": str(exc),
                }
        result["process_memory"] = process_memory()
        results.append(result)
        dump(args.output / f"{case['id']}.json", result)
        print(case["id"], {k: v["status"] for k, v in result["arms"].items()}, flush=True)
    import numpy as np

    summary = {
        "scheduled_cases": len(reference_manifest["cases"]),
        "completed_cases": len(results),
        "arms": {},
        "default_activation": False,
        "answer_quality_gate": "Not evaluated in retrieval-only replay",
    }
    for split in ("development", "holdout"):
        summary["arms"][split] = {}
        for budget in (5, 10, 20):
            values = [row["arms"][str(budget)] for row in results if row["split"] == split]
            warm = [
                m["elapsed_ms"]
                for row in values
                for m in row["measurements"]
                if m["phase"] == "warm"
            ]
            completed = [row for row in values if row["status"] == "completed"]
            summary["arms"][split][str(budget)] = {
                "scheduled": len(values),
                "completed": len(completed),
                "complete_reference_top5": sum(
                    x["reference_top5_retained"] == 5 for x in completed
                ),
                "mean_reference_top5_fraction": statistics.mean(
                    x["reference_top5_retained"] / 5 for x in completed
                )
                if completed
                else None,
                "warm_n": len(warm),
                "warm_median_ms": statistics.median(warm) if warm else None,
                "warm_p95_ms": float(np.percentile(warm, 95)) if warm else None,
            }
    dump(args.output / "summary.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
