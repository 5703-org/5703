"""Frozen grouped, paired scope selection study using real local E5 CPU vectors.

The applicability labels are authored development fixtures, not human judgments.
Answer preference application is imported separately and is never inferred from
selection or similarity. No answer-provider call is made by this tool.
"""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import time

from personalisation import memory_v2 as old, memory_v3 as new


class Counter:
    def count(self, value):
        # Fixed offline projection counter, not an answering-model tokenizer claim.
        return (len(value.encode()) + 2) // 3


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_cases(data):
    """Reject split leakage or malformed authored labels before any E5 work."""
    if not isinstance(data, dict) or not isinstance(data.get("version"), str):
        raise ValueError("A versioned memory catalogue is required")
    if data.get("label_origin") != "authored_applicability_fixture":
        raise ValueError("Memory applicability labels need explicit authored provenance")
    cases, grid = data.get("cases"), data.get("threshold_grid")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Memory catalogue needs cases")
    if (
        not isinstance(grid, list)
        or not grid
        or any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or not 0 <= value <= 1
            for value in grid
        )
        or len(set(grid)) != len(grid)
    ):
        raise ValueError("Threshold grid must contain distinct finite values in [0, 1]")
    seen_ids: set[str] = set()
    groups: dict[str, str] = {}
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("Memory case must be an object")
        identity, group, split = (case.get(k) for k in ("id", "group", "split"))
        if (
            not isinstance(identity, str)
            or not identity
            or identity in seen_ids
            or not isinstance(group, str)
            or not group
            or split not in {"development", "reserved"}
            or not isinstance(case.get("question"), str)
            or not case["question"].strip()
            or type(case.get("expected_selected")) is not bool
        ):
            raise ValueError("Memory case identity, split, question or label is invalid")
        seen_ids.add(identity)
        if group in groups and groups[group] != split:
            raise ValueError("Knowledge-concept group crosses splits")
        groups[group] = split
        entry = case.get("entry")
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("id"), str)
            or not isinstance(entry.get("content"), str)
            or not isinstance(entry.get("scope"), str)
            or not isinstance(entry.get("source_message_id"), str)
            or type(entry.get("version")) is not int
            or entry.get("category") != "preference"
            or entry.get("field_key") not in old.FIELDS
            or not isinstance(entry.get("scope_topics"), list)
        ):
            raise ValueError("Memory case has an invalid typed authored entry")
    if {"development", "reserved"} - set(groups.values()):
        raise ValueError("Development and reserved groups must both be present")
    return {
        "cases": len(cases),
        "groups": {
            split: sorted(g for g, value in groups.items() if value == split)
            for split in ("development", "reserved")
        },
    }


def freeze(output, cases_path):
    data = json.loads(cases_path.read_text(encoding="utf-8"))
    catalogue = validate_cases(data)
    if output.exists() and any(output.iterdir()):
        raise ValueError("Freeze requires an empty study directory")
    output.mkdir(parents=True, exist_ok=True)
    dump(output / "frozen-cases.json", data)
    paths = [
        Path(__file__),
        Path("personalisation/memory_v2.py"),
        Path("personalisation/memory_v3.py"),
        Path("retrieval/embedding.py"),
        Path("retrieval/runtime.py"),
    ]
    dump(
        output / "freeze.json",
        {
            "cases_sha256": sha(output / "frozen-cases.json"),
            "source_files": {p.as_posix(): sha(p) for p in paths},
            "embedding": new.EMBEDDING,
            "group_disjoint": True,
            "catalogue": catalogue,
            "label_origin": data["label_origin"],
        },
    )


def source_reader(entry):
    return {
        "owned": True,
        "memory_id": entry["id"],
        "memory_version": entry["version"],
        "source_message_id": entry["source_message_id"],
        "content": entry["content"],
        "source_hash": old.digest(entry["content"]),
    }


def counts(records):
    return {
        "cases": len(records),
        "correct_selection": sum(r["selected"] and r["expected"] for r in records),
        "false_selection": sum(r["selected"] and not r["expected"] for r in records),
        "omission": sum(not r["selected"] and r["expected"] for r in records),
        "correct_exclusion": sum(not r["selected"] and not r["expected"] for r in records),
    }


def evaluate(cases, policy):
    rows = []
    for case in cases:
        start = time.perf_counter()
        result = new.select(
            [case["entry"]],
            case["question"],
            {"profile": {"style": "concise"}},
            policy=policy,
            source_reader=source_reader,
            counter=Counter(),
        )
        rows.append(
            {
                "id": case["id"],
                "group": case["group"],
                "expected": case["expected_selected"],
                "selected": bool(result.state["entries"]),
                "state": result.state,
                "trace": result.trace,
                "elapsed_ms": (time.perf_counter() - start) * 1000,
                "answer_preference_application": None,
            }
        )
    return rows


def run(output):
    receipt = json.loads((output / "freeze.json").read_text())
    assert receipt["cases_sha256"] == sha(output / "frozen-cases.json")
    assert all(sha(Path(p)) == value for p, value in receipt["source_files"].items())
    if (output / "calibration.json").exists() or (output / "results.json").exists():
        raise ValueError(
            "Preserve the first development/reserved run; create a new version for changes"
        )
    data = json.loads((output / "frozen-cases.json").read_text())
    assert validate_cases(data) == receipt["catalogue"]
    dev = [c for c in data["cases"] if c["split"] == "development"]
    reserved = [c for c in data["cases"] if c["split"] == "reserved"]
    # Cache measured scores only inside this offline process. Every unique text/scope
    # is encoded by the pinned real model; the product never uses this scorer cache.
    original_scorer, scores = new.scope_scores, {}

    def measured(question, scopes):
        key = (question, tuple(scopes))
        if key not in scores:
            scores[key] = original_scorer(question, scopes)
        return scores[key]

    new.scope_scores = measured
    try:
        grid = []
        for threshold in data["threshold_grid"]:
            rows = evaluate(
                dev,
                new.freeze_policy(
                    enabled=True, threshold=threshold, calibration_id=receipt["cases_sha256"]
                ),
            )
            grid.append({"threshold": threshold, **counts(rows)})
        eligible = [r for r in grid if r["false_selection"] == 0]
        chosen = min(
            eligible or grid,
            key=lambda r: (r["false_selection"], -r["correct_selection"], -r["threshold"]),
        )
        activation_decision = (
            "development_zero_false_gate_passed"
            if eligible
            else "rejected_development_false_selection"
        )
        calibration = {
            "fixture_sha256": receipt["cases_sha256"],
            "development_groups": sorted({r["group"] for r in dev}),
            "grid": grid,
            "chosen": chosen,
            "activation_decision": activation_decision,
            "label_origin": data["label_origin"],
            "embedding": new.EMBEDDING,
            "default_enabled": False,
        }
        dump(output / "calibration.json", calibration)
        policy = new.freeze_policy(
            enabled=True,
            threshold=chosen["threshold"],
            calibration_id=sha(output / "calibration.json"),
        )
        # A failed gate has a diagnostic policy for offline comparison only.
        policy_file = (
            "experimental-policy.json" if eligible else "diagnostic-policy-not-for-activation.json"
        )
        dump(output / policy_file, policy)
        # The cutoff and calibration artifact exist before the first reserved E5 call.
        results: dict = {"development": {}, "reserved": {}}
        for name, cases in (("development", dev), ("reserved", reserved)):
            for arm, arm_policy in (("rules", new.freeze_policy()), ("semantic", policy)):
                rows = evaluate(cases, arm_policy)
                results[name][arm] = {"counts": counts(rows), "records": rows}
        dump(
            output / "results.json",
            {
                "version": data["version"],
                "calibration_sha256": sha(output / "calibration.json"),
                "unique_real_embedding_batches": len(scores),
                "answer_model_calls": 0,
                "human_ratings": 0,
                "answer_preference_application": None,
                "results": results,
                "source_unchanged": all(
                    sha(Path(p)) == value for p, value in receipt["source_files"].items()
                ),
            },
        )
        dump(
            output / "public-summary.json",
            {
                "schema": "week09_memory_v3_authored_cpu_selection_v1",
                "catalogue_sha256": receipt["cases_sha256"],
                "calibration_sha256": sha(output / "calibration.json"),
                "development_groups": receipt["catalogue"]["groups"]["development"],
                "held_out_groups": receipt["catalogue"]["groups"]["reserved"],
                "label_origin": data["label_origin"],
                "selected_cutoff": chosen["threshold"],
                "activation_decision": activation_decision,
                "cutoff_role": "experimental" if eligible else "diagnostic_only",
                "selection_counts": {
                    split: {arm: results[split][arm]["counts"] for arm in ("rules", "semantic")}
                    for split in ("development", "reserved")
                },
                "real_cpu_e5_batches": len(scores),
                "embedding": new.EMBEDDING,
                "answer_model_calls": 0,
                "human_ratings": 0,
                "answer_preference_application": None,
                "product_semantic_default_enabled": False,
                "scope": "Offline selector applicability only; authored labels and a small holdout do not establish real learner preference use or activation safety.",
            },
        )
        with (output / "preference-application-review.csv").open(
            "w", newline="", encoding="utf-8"
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["case_id", "arm", "answer_id", "applied", "reviewer_id", "notes"],
            )
            writer.writeheader()
            for case in data["cases"]:
                for arm in ("rules", "semantic"):
                    writer.writerow({"case_id": case["id"], "arm": arm})
    finally:
        new.scope_scores = original_scorer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["freeze", "run"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--cases", type=Path, help="Protected authored fixture JSON required for freeze"
    )
    args = parser.parse_args()
    if args.action == "freeze":
        if args.cases is None:
            parser.error("freeze requires --cases")
        freeze(args.output, args.cases)
    else:
        run(args.output)


if __name__ == "__main__":
    main()
