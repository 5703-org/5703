"""Fit a model-specific relevance cutoff from reviewed development judgments only."""

import math


def main():
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--judgments", type=Path, required=True)
    parser.add_argument("--pool", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Preserve earlier calibration results")
    original = json.loads(args.pool.read_text(encoding="utf-8"))
    reviewed = json.loads(args.judgments.read_text(encoding="utf-8"))
    rows = validate_pool_review(original, reviewed)
    result = calibrate(rows, model=args.model, revision=args.revision)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


def validate_pool_review(original, reviewed):
    """Require exact scheduled membership and immutable question/source/score identity."""
    import hashlib

    for key in ("plan_sha256", "corpus_release_id", "model", "revision"):
        if not original.get(key) or original[key] != reviewed.get(key):
            raise ValueError("Review identity differs from the frozen retrieval pool")
    fields = (
        "question_id",
        "question",
        "chunk_id",
        "group",
        "split",
        "model",
        "revision",
        "score",
        "processing_id",
        "text_hash",
        "source_title",
        "source_url",
        "section",
        "pages",
        "text",
    )
    expected = {(r["question_id"], r["chunk_id"]): r for r in original["rows"]}
    if len(expected) != len(original["rows"]):
        raise ValueError("The original pool duplicates a scheduled pair")
    seen = set()
    for row in reviewed["rows"]:
        key = (row["question_id"], row["chunk_id"])
        if key not in expected or key in seen:
            raise ValueError("Unexpected or duplicate reviewed pair")
        if any(row[field] != expected[key][field] for field in fields):
            raise ValueError("Reviewed question, grouping, score or source was changed")
        if hashlib.sha256(row["text"].encode()).hexdigest() != row["text_hash"]:
            raise ValueError("Reviewed source text does not match its hash")
        seen.add(key)
    if seen != set(expected):
        raise ValueError("Scheduled pairs cannot be omitted from a calibration review")
    return reviewed["rows"]


def calibrate(rows, *, model, revision):
    """Return a proposal with separate holdout confusion counts; never activate it."""
    if not rows or not model or len(revision) != 40:
        raise ValueError("Named model, immutable revision and actual judgments are required")
    groups, pairs = {}, set()
    for row in rows:
        if row.get("model") != model or row.get("revision") != revision:
            raise ValueError("Different rerankers cannot share a raw-score calibration")
        if row.get("split") not in {"development", "holdout"}:
            raise ValueError("Every judgment needs a frozen split")
        if row.get("label") not in {0, 1} or type(row.get("label")) is not int:
            raise ValueError("Every scheduled judgment needs an explicit binary relevance label")
        if not row.get("reviewer_id") or not row.get("reviewed_at"):
            raise ValueError("Unreviewed pools cannot be described as calibrated")
        if type(row.get("score")) not in (int, float) or not math.isfinite(row["score"]):
            raise ValueError("Finite reranker logits are required")
        group = row["group"]
        if group in groups and groups[group] != row["split"]:
            raise ValueError("A knowledge group crosses development and holdout")
        groups[group] = row["split"]
        pair = (row["question_id"], row["chunk_id"])
        if pair in pairs:
            raise ValueError("Duplicate judged question/chunk pair")
        pairs.add(pair)
    development = [r for r in rows if r["split"] == "development"]
    holdout = [r for r in rows if r["split"] == "holdout"]
    if {r["label"] for r in development} != {0, 1} or not holdout:
        raise ValueError("Both development classes and a separate holdout are required")

    def metrics(items, threshold):
        counts = {"tp": 0, "tn": 0, "fp": 0, "fn": 0}
        for row in items:
            predicted = row["score"] >= threshold
            key = ("tp" if predicted else "fn") if row["label"] else ("fp" if predicted else "tn")
            counts[key] += 1
        positive = counts["tp"] + counts["fn"]
        negative = counts["tn"] + counts["fp"]
        counts["false_rejection_rate"] = counts["fn"] / positive if positive else None
        counts["false_acceptance_rate"] = counts["fp"] / negative if negative else None
        counts["balanced_accuracy"] = (
            ((counts["tp"] / positive + counts["tn"] / negative) / 2)
            if positive and negative
            else None
        )
        return counts

    scores = sorted({r["score"] for r in development})
    thresholds = (
        [math.nextafter(scores[0], -math.inf)]
        + [(a + b) / 2 for a, b in zip(scores, scores[1:])]
        + [math.nextafter(scores[-1], math.inf)]
    )
    curve = [{"threshold": t, **metrics(development, t)} for t in thresholds]
    # Ties prefer fewer false refusals, then the smaller cutoff. Holdout is never consulted.
    best = max(curve, key=lambda r: (r["balanced_accuracy"], -r["fn"], -r["threshold"]))
    return {
        "version": "reviewed-threshold-proposal-v1",
        "model": model,
        "revision": revision,
        "threshold": best["threshold"],
        "selection": "development balanced accuracy, then fewer false refusals",
        "development": metrics(development, best["threshold"]),
        "holdout": metrics(holdout, best["threshold"]),
        "development_curve": curve,
        "activated": False,
        "scope": "Topical relevance labels; this is not claim entailment or answer correctness",
    }


if __name__ == "__main__":
    main()
