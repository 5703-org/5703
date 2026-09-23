"""Write-once schedules and explicit-denominator analysis for the new study."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from evaluation.enhancement.protocol import digest, freeze, verify_frozen

VERSION = "week08_memory_v2_study_v1"
SEED = 20260921
ARMS = {
    "A": ("A0", "A1", "A2"),
    "B": ("B0", "B1", "B2"),
    "C": ("C1", "C2"),
    "T": ("T0", "T1", "T2", "T3", "T4"),
    "M": ("M0", "M1", "M2", "M3", "M4"),
}
CONDITION_POLICIES = {
    "B0": {"checking": "schema_only_research_v1", "reliability_policy": "evidence_reliability_v2"},
    "B1": {"checking": "complete", "reliability_policy": "legacy_joint_v1"},
    "B2": {"checking": "complete", "reliability_policy": "evidence_reliability_v2"},
    "C1": {
        "checking": "complete",
        "reliability_policy": "evidence_reliability_v2",
        "generation_context_policy": "legacy_context_v1",
    },
    "C2": {
        "checking": "complete",
        "reliability_policy": "evidence_reliability_v2",
        "repair_policy": "generic_answer_repair_v1",
    },
}


def schedule(tasks: list[dict], trajectories: list[dict]) -> list[dict]:
    """Freeze all planned arms; external dependencies never drop a row."""
    if len(tasks) != 24 or len({t["id"] for t in tasks}) != 24:
        raise ValueError("The registered final catalogue requires 24 unique tasks")
    if len({t["family"] for t in tasks}) != 24:
        raise ValueError("Final task families must be distinct")
    if sorted(Counter(t["source_requirement"]["book"] for t in tasks).values()) != [6] * 4:
        raise ValueError("The registered coverage requires six tasks per book")
    hints = [t for t in tasks if t["teaching_task"]]
    if len(hints) != 12:
        raise ValueError("T requires exactly twelve teaching tasks")
    if len(trajectories) != 12 or len({t["id"] for t in trajectories}) != 12:
        raise ValueError("M requires twelve unique learner trajectories")
    rows = []
    for study in ("A", "B", "C", "T", "M"):
        inputs = trajectories if study == "M" else hints if study == "T" else tasks
        for task in sorted(inputs, key=lambda t: digest({"seed": SEED, "id": t["id"]})):
            arms = ARMS[study]
            offset = int(digest(task["id"])[:8], 16) % len(arms)
            for arm in arms[offset:] + arms[:offset]:
                for turn in range(1, 4 if study in {"M", "T"} else 2):
                    rows.append(
                        {
                            "id": f"{task['id']}-{arm}-{turn}",
                            "study": study,
                            "case_id": task["id"],
                            "family": task.get("family", task["id"]),
                            "arm": arm,
                            "turn": turn,
                            "status": "planned",
                            "external_requirement": "human_oracle_confirmation"
                            if arm == "A2"
                            else None,
                        }
                    )
    if len(rows) != 552 or len({r["id"] for r in rows}) != 552:
        raise ValueError("Schedule differs from the preregistered 552 requests")
    return rows


def require_oracle_confirmation(task: dict, evidence_hash: str) -> dict:
    """A software/source check cannot supply an actual human attestation."""
    value = task.get("oracle_confirmation")
    if not isinstance(value, dict):
        raise ValueError("Human confirmation has not been supplied")
    required = {"reviewer_id", "confirmed_at", "sufficient", "evidence_sha256", "coverage"}
    if set(value) != required or value["sufficient"] is not True:
        raise ValueError("Oracle confirmation fields or sufficiency are invalid")
    if not isinstance(value["reviewer_id"], str) or not value["reviewer_id"].strip():
        raise ValueError("An actual reviewer identity is required")
    if value["reviewer_id"].casefold() in {"codex", "automatic", "model", "ai"}:
        raise ValueError("An automatic evaluator is not a human confirmer")
    if value["evidence_sha256"] != evidence_hash or not value["coverage"]:
        raise ValueError("Confirmation does not identify these sufficient sources")
    when = datetime.fromisoformat(value["confirmed_at"])
    if when.tzinfo is None or when > datetime.now(timezone.utc):
        raise ValueError("Confirmation time must be an actual past timezone-aware time")
    return deepcopy(value)


def freeze_study(path: Path, tasks: list[dict], trajectories: list[dict], checkpoint: dict) -> dict:
    required = {
        "source_hashes",
        "protocol_hashes",
        "model_config",
        "checker_config",
        "corpus",
        "retrieval_hashes",
        "memory_extraction_sha256",
        "memory_gating_sha256",
    }
    if not required.issubset(checkpoint) or any(not checkpoint[k] for k in required):
        raise ValueError("A complete executable checkpoint is required before formal calls")
    value = {
        "version": VERSION,
        "seed": SEED,
        "tasks_sha256": digest(tasks),
        "trajectories_sha256": digest(trajectories),
        "checkpoint": checkpoint,
        "schedule": schedule(tasks, trajectories),
        "condition_policies": CONDITION_POLICIES,
        "human_ratings": 0,
        "formal_results_at_freeze": 0,
    }
    return freeze(path, value)


def outcome_counts(planned: list[dict], outcomes: list[dict], judgments: list[dict]) -> dict:
    """Unknown judgments and failed attempts remain in explicit denominators."""
    ids = {r["id"] for r in planned}
    if len(ids) != len(planned):
        raise ValueError("Duplicate planned identities")
    indexed = {r["id"]: r for r in outcomes}
    judged = {r["id"]: r for r in judgments}
    if len(indexed) != len(outcomes) or len(judged) != len(judgments):
        raise ValueError("Duplicate outcomes or ratings require explicit revision selection")
    if not set(indexed).issubset(ids) or not set(judged).issubset(ids):
        raise ValueError("Result or judgment outside the frozen schedule")
    delivered = {i for i, r in indexed.items() if r.get("status") == "answer"}
    correct = {i for i in delivered if judged.get(i, {}).get("correct") is True}
    judged_delivered = {i for i in delivered if type(judged.get(i, {}).get("correct")) is bool}
    counts = Counter(r.get("status", "unknown") for r in outcomes)

    def ratio(n, d):
        return {"numerator": n, "denominator": d, "value": n / d if d else None}

    return {
        "planned": len(planned),
        "recorded": len(outcomes),
        "unrecorded": len(ids - set(indexed)),
        "status_counts": dict(counts),
        "delivered": len(delivered),
        "judged_delivered": len(judged_delivered),
        "correct_delivered": len(correct),
        "delivery": ratio(len(delivered), len(planned)),
        "judgment_coverage": ratio(len(judged_delivered), len(delivered)),
        "correct_among_judged_delivered": ratio(len(correct), len(judged_delivered)),
        "end_to_end_correct_conservative": ratio(len(correct), len(planned)),
    }


__all__ = [
    "VERSION",
    "ARMS",
    "schedule",
    "freeze_study",
    "require_oracle_confirmation",
    "outcome_counts",
    "verify_frozen",
]
