"""Audit the seven registered study families from sanitized immutable receipts.

This reports evidence coverage, not the success of an unexecuted comparison.
Inputs never include exact questions, private labels or learner records.
"""

import argparse
import hashlib
import json
from pathlib import Path

from evaluation.week09_continuation.protocol import FAMILIES


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tally(receipt, key):
    families = receipt[key]
    unknown = set(families) - set(FAMILIES)
    if unknown:
        raise ValueError(f"Unknown study families: {sorted(unknown)}")
    counts = {}
    for family in FAMILIES:
        arms = families.get(family, {})
        unregistered = set(arms) - set(FAMILIES[family])
        if unregistered:
            raise ValueError(f"Unregistered arms for {family}: {sorted(unregistered)}")
        counts[family] = {
            "scheduled": sum(value["planned"] for value in arms.values()),
            "terminal": sum(value["terminal"] for value in arms.values()),
            "arms_executed": sorted(arms),
            "registered_arms_not_executed": sorted(set(FAMILIES[family]) - set(arms)),
        }
    if sum(value["scheduled"] for value in counts.values()) != receipt["scheduled_outcomes"]:
        raise ValueError("Family schedule does not match the frozen denominator")
    if sum(value["terminal"] for value in counts.values()) != receipt["terminal_outcomes"]:
        raise ValueError("Family terminal counts do not match the frozen denominator")
    return counts


def audit(pilot_path, formal_path, memory_path):
    pilot, formal, memory = (read(path) for path in (pilot_path, formal_path, memory_path))
    pilot_counts = tally(pilot, "families")
    formal_counts = tally(formal, "family_arm_results")
    if pilot.get("human_ratings") != 0 or formal.get("human_review", {}).get("human_ratings") != 0:
        raise ValueError("The human-score boundary changed; inspect it before updating this audit")
    if memory.get("human_ratings") != 0 or memory.get("answer_model_calls") != 0:
        raise ValueError("The offline memory scope result changed its evidence boundary")
    result = {
        "schema": "week09_seven_family_evidence_scope_v1",
        "input_sha256": {
            "seven_family_pilot_v7": sha(pilot_path),
            "conditional_formal_v8": sha(formal_path),
            "authored_memory_cpu_scope": sha(memory_path),
        },
        "registered_families": list(FAMILIES),
        "pilot": {
            "scheduled": pilot["scheduled_outcomes"],
            "terminal": pilot["terminal_outcomes"],
            "families": pilot_counts,
            "evidence_role": "development_pilot; non-QA/tutoring paths include diagnostic observations",
        },
        "formal": {
            "scheduled": formal["scheduled_outcomes"],
            "terminal": formal["terminal_outcomes"],
            "families": formal_counts,
            "families_without_formal_outcomes": sorted(
                family for family, count in formal_counts.items() if count["scheduled"] == 0
            ),
            "study_scope": formal["study_scope"],
            "human_ratings": formal["human_review"]["human_ratings"],
        },
        "memory_selector_addendum": {
            "development": memory["selection_counts"]["development"],
            "held_out": memory["selection_counts"]["reserved"],
            "label_origin": memory["label_origin"],
            "activation_decision": memory["activation_decision"],
            "real_cpu_e5_batches": memory["real_cpu_e5_batches"],
            "answer_model_calls": memory["answer_model_calls"],
            "human_ratings": memory["human_ratings"],
            "not_a_formal_family_result": True,
        },
        "interpretation": (
            "The seven-family pilot and two-family conditional automatic formal study have different "
            "denominators. Memory, practice, visual, safety and performance lack formal outcome "
            "sets; a private authored memory scope holdout does not fill that gap."
        ),
    }
    if len(result["formal"]["families_without_formal_outcomes"]) != 5:
        raise ValueError("Expected formal family scope changed; review before release")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", type=Path, required=True)
    parser.add_argument("--formal", type=Path, required=True)
    parser.add_argument("--memory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Preserve the earlier audit; choose a new output path")
    result = audit(args.pilot, args.formal, args.memory)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
