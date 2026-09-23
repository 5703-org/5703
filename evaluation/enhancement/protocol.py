"""Immutable condition definitions, scheduling and evaluator-only rubric."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

PROTOCOL_VERSION = "w8-enhancement-v1"
RUBRIC_VERSION = "w8-hint-rubric-v1"
SEED = 20260920
CONDITIONS = {
    "T0": {"body_check": False, "evidence_control": False, "cumulative_check": False},
    "T1": {"body_check": True, "evidence_control": False, "cumulative_check": False},
    "T2": {"body_check": True, "evidence_control": True, "cumulative_check": True},
    "T3": {"body_check": True, "evidence_control": True, "cumulative_check": False},
    "T4": {"body_check": True, "evidence_control": False, "cumulative_check": True},
}
CITATION_CONDITIONS = ("paragraph", "posthoc_spans", "preselected_spans")
MEMORY_CONDITIONS = ("profile_session", "rolling_summary", "structured_memory")
DIMENSIONS = ("supported", "specific_help", "within_scope")

RUBRIC = {
    "version": RUBRIC_VERSION,
    "dimensions": {
        "supported": "The delivered hint is factually compatible with the cited textbook passages and preserves material conditions and units.",
        "specific_help": "The hint gives a concrete, task-relevant next reasoning step or comparison dimension that the learner can use; a vague encouragement alone fails.",
        "within_scope": "All content accessible after the ordinary citation-open action, combined with previously exposed turns, stays within the private per-round help allowance and avoids the protected conclusion or final result.",
        "fact_error": "At least one delivered factual statement is contradicted by the source or an applicable calculation/condition.",
        "citation_complete": "Every material factual assertion in the hint has supporting cited text, with required conditions retained.",
        "memory_misuse": "The answer applies an expired, deleted, superseded, unrelated or explicitly disabled memory, or ignores an overriding current instruction.",
    },
    "scale": "Binary 0 or 1, with a written reason and optional source/answer quote; null only when an item cannot be judged.",
    "valid_hint": "supported == 1 and specific_help == 1 and within_scope == 1, with successful publication and complete judging",
    "human_review": "Two independent named reviewers; blinded condition labels and randomized order; adjudication is separate from original ratings.",
    "failure_policy": "Generation errors, timeouts and refusals are unsuccessful planned hint requests. Missing judge outputs remain missing and count as unsuccessful in conservative all-planned metrics.",
}


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def freeze(path: Path, value: dict) -> dict:
    """Write once; a repeated identical freeze is read-only and safe."""
    payload = {**value, "content_sha256": digest(value)}
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing != payload:
            raise ValueError("Frozen protocol or schedule already exists with different bytes")
        return existing
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    return payload


def verify_frozen(payload: dict) -> dict:
    value = {k: v for k, v in payload.items() if k != "content_sha256"}
    if payload.get("content_sha256") != digest(value):
        raise ValueError("Frozen content digest differs")
    return value


def validate_tasks(tasks: list[dict], *, split: str) -> None:
    expected = 12 if split == "development" else 60
    if len(tasks) != expected or len({t["id"] for t in tasks}) != expected:
        raise ValueError("Task count or unique identity does not match the protocol")
    groups = Counter((t["subject"], t["task_type"]) for t in tasks)
    if set(groups) != {
        (subject, kind)
        for subject in ("biology", "chemistry")
        for kind in ("comparison", "process", "calculation")
    } or set(groups.values()) != {expected // 6}:
        raise ValueError("Subject and task-type balance differs from the protocol")
    for task in tasks:
        if task.get("split") != split or not task.get("family") or not task.get("question"):
            raise ValueError("Task split, family and question are required")
        if len(task.get("turns", [])) != 3:
            raise ValueError("Each task needs exactly three scheduled hint turns")
        if len(task.get("help_allowances", [])) != 3 or not task.get("critical_answer"):
            raise ValueError("Evaluator-only help allowances and critical answer are required")


def generation_task(task: dict) -> dict:
    """Explicit allowlist excludes evaluator answers, help labels and anchors."""
    return {k: task[k] for k in ("id", "question", "turns")}


def hint_schedule(
    tasks: list[dict], *, conditions: tuple[str, ...] = tuple(CONDITIONS)
) -> list[dict]:
    result = []
    # Condition order rotates by task to avoid one condition always receiving warm service.
    for task in sorted(tasks, key=lambda t: digest({"seed": SEED, "id": t["id"]})):
        offset = int(digest(task["id"])[:8], 16) % len(conditions)
        order = conditions[offset:] + conditions[:offset]
        for condition in order:
            if condition not in CONDITIONS:
                raise ValueError("Unknown teaching condition")
            for turn in range(1, 4):
                result.append(
                    {
                        "id": f"{task['id']}-{condition}-H{turn}",
                        "task_id": task["id"],
                        "condition": condition,
                        "turn": turn,
                        "state": "planned",
                    }
                )
    return result
