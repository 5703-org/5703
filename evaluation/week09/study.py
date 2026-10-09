"""Frozen paired teaching pilot with separate operational and human outcomes."""

from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import random
import statistics
import time

from generation import GenerationService, RequestBudget
from generation.teaching_plan import freeze_generation_policy
from scripts.verify.teaching_contracts_live import build_request as reference_request
from scripts.verify.all import source_snapshot, ROOT
from .diagnostics import summarize as diagnose_summary
from .review import write


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def runtime_sources():
    roots = (
        "generation/",
        "contracts/",
        "conversation/",
        "personalisation/",
        "retrieval/",
        "evaluation/week09/",
        "scripts/verify/teaching_contracts_live.py",
    )
    return {name: value for name, value in source_snapshot().items() if name.startswith(roots)}


def build_request(item, manifest):
    adapted = {
        **item,
        "policy": "evidence_reliability_v3" if item["arm"] == "W8" else "evidence_reliability_v4",
    }
    request = reference_request(adapted, manifest)
    context = {**(request.teaching_context or {}), "current_step": 1}
    prepared = request.prepared_query or {}
    return replace(
        request,
        teaching_context=context,
        understanding=prepared.get("understanding"),
        generation_policy=None if item["arm"] == "W8" else freeze_generation_policy(item["arm"]),
        provider_output_policy=manifest["provider_output_policy"],
    )


def freeze(
    preparation: Path,
    output: Path,
    *,
    split="pilot",
    repeats=1,
    include_reference=True,
    provider_output_policy="strict_v1",
    sample_decision=None,
):
    if output.exists() or split not in {"pilot", "reserved"} or not 1 <= repeats <= 3:
        raise ValueError("Use a new study directory and a bounded declared design")
    prepared = read(preparation)
    cases = [case for case in prepared["cases"] if case["split"] == split]
    if split == "reserved" and sample_decision is None:
        raise ValueError("Freeze the pilot-based sample decision before opening reserved cases")
    arms = ["A", "B", "C", "D"] + (["W8"] if include_reference else [])
    schedule = []
    for case in cases:
        for stage in ("first_hint", "learner_attempt"):
            for repeat in range(repeats):
                for arm in arms:
                    schedule.append(
                        {
                            "id": f"{'P' if split == 'pilot' else 'F'}{len(schedule) + 1:04d}",
                            "case_id": case["id"],
                            "family": case["family"],
                            "book": case["book"],
                            "answer_mode": "textbook",
                            "stage": stage,
                            "repeat": repeat,
                            "arm": arm,
                        }
                    )
    random.Random(570309).shuffle(schedule)
    manifest = {
        "schema": "week09_teaching_factorial_v1",
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "preparation_sha256": sha(preparation),
        "split": split,
        "cases": cases,
        "schedule": schedule,
        "planned_outcomes": len(schedule),
        "model_config": prepared["model_config"],
        "checker_config": prepared["checker_config"],
        "corpus": prepared["corpus"],
        "source_hashes": runtime_sources(),
        "budget": {"max_calls": 4, "max_active_seconds": 180},
        "provider_output_policy": provider_output_policy,
        "concurrency": 2,
        "seed": 570309,
        "sample_decision": sample_decision,
        "human_ratings": 0,
        "interpretation": "Randomized paired generation/checking study on frozen real retrieved sources. Latency excludes HTTP queue, retrieval and browser display. Online acceptance is operational, not independent semantic truth. Authored fixed contexts make stages comparable across arms.",
    }
    for item in schedule:
        request = build_request(item, manifest)
        if not request.evidence:
            raise ValueError(
                "A scheduled textbook case has no retrieved context; retain and resolve preparation explicitly"
            )
    output.mkdir(parents=True)
    write(output / "frozen-study.json", manifest)
    for name in manifest["source_hashes"]:
        target = output / "frozen-source" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())
    receipt = {
        "frozen_study_sha256": sha(output / "frozen-study.json"),
        "source_files": len(manifest["source_hashes"]),
        "planned": len(schedule),
        "split": split,
    }
    write(output / "freeze-receipt.json", receipt)
    return receipt


def run_one(item, manifest, output, key):
    path = output / "outcomes" / (item["id"] + ".json")
    if path.exists():
        return read(path)
    if runtime_sources() != manifest["source_hashes"]:
        raise ValueError("Frozen runtime sources changed before execution")
    event_path = output / "attempt-events" / (item["id"] + ".jsonl")
    if event_path.exists():
        raise ValueError("An interrupted call has preserved events; reconcile it before any retry")
    event_path.parent.mkdir(parents=True, exist_ok=True)
    request = build_request(item, manifest)
    started = time.perf_counter()

    def event(value):
        with event_path.open("a", encoding="utf-8") as stream:
            stream.write(
                json.dumps(
                    {"recorded_at": datetime.now(timezone.utc).isoformat(), **value},
                    ensure_ascii=False,
                )
                + "\n"
            )
            stream.flush()

    record = {
        "schedule": item,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "request": asdict(request),
    }
    try:
        result = GenerationService(api_key=key, checker_api_key=key).generate(
            request, RequestBudget(**manifest["budget"]), on_attempt=event
        )
        record.update(outcome=result.to_dict(), error=None)
    except Exception as error:
        record.update(
            outcome=None,
            error={
                "code": "EVALUATOR_EXCEPTION",
                "type": type(error).__name__,
                "message": str(error)[:1200],
            },
        )
    record["elapsed_ms"] = (time.perf_counter() - started) * 1000
    record["source_unchanged"] = runtime_sources() == manifest["source_hashes"]
    write(path, record)
    outcome = record.get("outcome") or {}
    print(
        json.dumps(
            {
                "id": item["id"],
                "arm": item["arm"],
                "published": bool(outcome.get("response")) and not outcome.get("error"),
                "error": (outcome.get("error") or record.get("error") or {}).get("code"),
                "elapsed_ms": round(record["elapsed_ms"], 1),
            }
        ),
        flush=True,
    )
    return record


def execute(output: Path, key):
    manifest = read(output / "frozen-study.json")
    if (
        sha(output / "frozen-study.json")
        != read(output / "freeze-receipt.json")["frozen_study_sha256"]
    ):
        raise ValueError("Frozen manifest changed")
    if not key:
        raise ValueError("A configured real provider key is required")
    with ThreadPoolExecutor(max_workers=manifest["concurrency"]) as pool:
        futures = [
            pool.submit(run_one, item, manifest, output, key) for item in manifest["schedule"]
        ]
        for future in as_completed(futures):
            future.result()
    return summarize(output)


def distribution(values):
    if not values:
        return {"n": 0, "median_ms": None, "p95_ms": None}
    ordered = sorted(values)
    index = (len(ordered) - 1) * 0.95
    lower = math.floor(index)
    upper = math.ceil(index)
    p95 = ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)
    return {"n": len(values), "median_ms": statistics.median(values), "p95_ms": p95}


def published(row):
    outcome = row.get("outcome") or {}
    return outcome.get("response") is not None and not outcome.get("error")


def summarize(output: Path):
    manifest = read(output / "frozen-study.json")
    records = [
        read(output / "outcomes" / (item["id"] + ".json"))
        for item in manifest["schedule"]
        if (output / "outcomes" / (item["id"] + ".json")).exists()
    ]
    arms = {}
    for arm in sorted({item["arm"] for item in manifest["schedule"]}):
        selected = [row for row in records if row["schedule"]["arm"] == arm]
        successes = [row for row in selected if published(row)]
        failures = [row for row in selected if not published(row)]
        attempts = [
            attempt
            for row in selected
            for attempt in (row.get("outcome") or {}).get("attempts", [])
        ]
        usage = {}
        for field in (
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "cache_hit_input_tokens",
            "cache_miss_input_tokens",
        ):
            counters = [(row.get("outcome") or {}).get("usage", {}).get(field) for row in selected]
            usage[field] = (
                sum(value for value in counters if isinstance(value, (int, float)))
                if any(value is not None for value in counters)
                else None
            )
        arms[arm] = {
            "planned": sum(item["arm"] == arm for item in manifest["schedule"]),
            "terminal": len(selected),
            "published": len(successes),
            "failed": len(failures),
            "first_check_accepted": sum(
                bool((row.get("outcome") or {}).get("checks"))
                and (row["outcome"]["checks"][0].get("accepted") is True)
                for row in selected
            ),
            "provider_attempts": len(attempts),
            "usage": usage,
            "usage_accounting": {
                "scope": "Sum of known provider counters; no invoice reconciliation",
                "complete_outcomes": sum(
                    (row.get("outcome") or {}).get("usage", {}).get("usage_complete") is True
                    for row in selected
                ),
                "missing_or_incomplete_outcomes": sum(
                    (row.get("outcome") or {}).get("usage", {}).get("usage_complete") is not True
                    for row in selected
                ),
                "submitted_attempts_with_unknown_token_usage": sum(
                    attempt.get("request_submitted") is not False
                    and not all(
                        isinstance((attempt.get("usage") or {}).get(field), (int, float))
                        for field in ("input_tokens", "output_tokens", "total_tokens")
                    )
                    for attempt in attempts
                ),
            },
            "latency_all": distribution([row["elapsed_ms"] for row in selected]),
            "latency_success": distribution([row["elapsed_ms"] for row in successes]),
            "latency_failure": distribution([row["elapsed_ms"] for row in failures]),
            "errors": dict(
                Counter(
                    ((row.get("outcome") or {}).get("error") or row.get("error") or {}).get(
                        "code", "UNKNOWN"
                    )
                    for row in failures
                )
            ),
        }
    comparisons = {}
    rng = random.Random(570309)
    families = sorted({item["family"] for item in manifest["schedule"]})
    means = {}
    for family in families:
        means[family] = {
            arm: statistics.mean(
                int(published(row))
                for row in records
                if row["schedule"]["family"] == family and row["schedule"]["arm"] == arm
            )
            for arm in arms
            if any(
                row["schedule"]["family"] == family and row["schedule"]["arm"] == arm
                for row in records
            )
        }
    for name, weights in {
        "B_minus_A": {"B": 1, "A": -1},
        "C_minus_A": {"C": 1, "A": -1},
        "D_minus_A": {"D": 1, "A": -1},
        "interaction": {"D": 1, "B": -1, "C": -1, "A": 1},
        "A_minus_W8": {"A": 1, "W8": -1},
    }.items():
        values = [
            sum(weights[arm] * row[arm] for arm in weights)
            for row in means.values()
            if set(weights) <= set(row)
        ]
        if values:
            bootstrap = sorted(
                statistics.mean(rng.choices(values, k=len(values))) for _ in range(2000)
            )
            comparisons[name] = {
                "unit": "knowledge-group mean operational delivery",
                "groups": len(values),
                "difference": statistics.mean(values),
                "paired_sd": statistics.stdev(values) if len(values) > 1 else None,
                "cluster_bootstrap_95": [bootstrap[49], bootstrap[1949]],
            }
    result = {
        "schema": "week09_operational_results_v1",
        "split": manifest["split"],
        "planned": manifest["planned_outcomes"],
        "terminal": len(records),
        "unstarted": manifest["planned_outcomes"] - len(records),
        "arms": arms,
        "comparisons": comparisons,
        "diagnostics": diagnose_summary(records),
        "runtime_sources_unchanged": all(row["source_unchanged"] for row in records),
        "human_scored_rows": 0,
        "semantic_correctness_rate": None,
        "useful_non_overreaching_hint_rate": None,
        "checker_false_block_rate": None,
        "checker_false_release_rate": None,
        "latency_scope": "Generation and checking on frozen CPU-retrieved context; excludes HTTP queue, live retrieval and browser display",
        "replication_scope": "Each family-stage-arm cell runs once unless repeats is declared. Stages are different conditions; no within-cell stochastic variance is estimated with one repeat.",
        "frozen_study_sha256": sha(output / "frozen-study.json"),
    }
    write(output / "summary.json", result)
    return result


def sample_decision(pilot: Path, output: Path, *, target_half_width=0.15):
    """A precision estimate for operational delivery, separate from human power."""
    if output.exists():
        raise ValueError("Preserve the prior sample-size decision")
    report = read(pilot / "summary.json")
    if report["unstarted"] or report["split"] != "pilot":
        raise ValueError("The pilot must be terminal before planning the next sample")
    pair = report["comparisons"]["D_minus_A"]
    # A zero pilot difference variance does not justify a zero-variance future study.
    sd = max(pair["paired_sd"] or 0, 0.25)
    required = max(16, math.ceil((1.96 * sd / target_half_width) ** 2))
    result = {
        "schema": "week09_pilot_sample_decision_v1",
        "pilot_sha256": sha(pilot / "summary.json"),
        "planned_endpoint": "Paired knowledge-group operational delivery difference D minus A",
        "pilot_difference": pair["difference"],
        "pilot_paired_sd": pair["paired_sd"],
        "variance_floor_sd": 0.25,
        "two_sided_normal_approximation": True,
        "target_95_half_width": target_half_width,
        "estimated_required_groups": required,
        "currently_reserved_groups": 16,
        "repetitions_replace_independent_groups": False,
        "quality_endpoint_power": None,
        "human_label_dependency": "Human quality labels remain unfilled; operational differences do not estimate quality effect size.",
        "next_action": "Use the untouched reserved groups with the frozen implementation; report achieved interval width and expand independent groups if required before claiming target precision.",
    }
    write(output, result)
    return result
