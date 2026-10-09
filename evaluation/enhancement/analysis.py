"""All-planned automatic metrics, paired task bootstrap and itemised API usage."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import random
import statistics
from urllib.parse import urlsplit

from evaluation.enhancement.protocol import SEED, digest, freeze
from evaluation.enhancement.runner import load

# Official CNY Flash tariff retrieved 20 September 2026; billed account currency
# and provider invoice may differ. Cache splits are measured, never inferred.
TARIFF = {
    "source": "https://api-docs.deepseek.com/zh-cn/quick_start/pricing/",
    "retrieved_date": "2026-09-20",
    "currency": "CNY",
    "per_tokens": 1000000,
    "off_peak": {"cache_hit": 0.02, "cache_miss": 1.0, "output": 4.0},
    "peak": {"cache_hit": 0.04, "cache_miss": 2.0, "output": 8.0},
    "peak_definition": "Asia/Shanghai Monday-Friday 09:00-12:00 and 14:00-18:00",
    "kind": "published_tariff_estimate_not_invoice",
}


def cost_estimate(usage, completed_at, *, model, base_url):
    endpoint = urlsplit(str(base_url))
    if (
        model != "deepseek-flash"
        or endpoint.scheme != "https"
        or endpoint.hostname != "api.deepseek.com"
        or endpoint.username
        or endpoint.password
    ):
        return None
    timestamp = datetime.fromisoformat(completed_at)
    if timestamp.tzinfo is None:
        return None
    timestamp = timestamp.astimezone(timezone(timedelta(hours=8)))
    minute = timestamp.hour * 60 + timestamp.minute
    peak = timestamp.weekday() < 5 and (540 <= minute < 720 or 840 <= minute < 1080)
    rate = TARIFF["peak" if peak else "off_peak"]
    hit, miss, tokens_out = (
        usage.get(k) for k in ("cache_hit_input_tokens", "cache_miss_input_tokens", "output_tokens")
    )
    if any(type(v) is not int or v < 0 for v in (hit, miss, tokens_out)):
        return None
    return (
        hit * rate["cache_hit"] + miss * rate["cache_miss"] + tokens_out * rate["output"]
    ) / 1_000_000


def paired_interval(left: dict[str, float], right: dict[str, float], *, samples=10000):
    if set(left) != set(right) or not left:
        raise ValueError("Paired comparisons require the same nonempty scheduled task set")
    differences = [left[k] - right[k] for k in sorted(left)]
    rng = random.Random(SEED)
    draws = sorted(
        statistics.mean(rng.choices(differences, k=len(differences))) for _ in range(samples)
    )
    return {
        "difference": statistics.mean(differences),
        "ci95": [draws[int(samples * 0.025)], draws[min(samples - 1, int(samples * 0.975))]],
        "paired_tasks": len(differences),
        "bootstrap_samples": samples,
        "seed": SEED,
    }


def analyse(run: Path):
    manifest = load(run / "run-manifest.json")
    judge_manifest = (
        load(run / "judge-manifest.json") if (run / "judge-manifest.json").exists() else None
    )
    by_condition = defaultdict(list)
    usages = []
    rows = []
    if len({i["id"] for i in manifest["planned"]}) != len(manifest["planned"]):
        raise ValueError("Duplicate scheduled study identity")
    for item in manifest["planned"]:
        path = run / "results" / (item["id"] + ".json")
        result = load(path) if path.exists() else None
        judge_path = run / "judgments" / (item["id"] + ".json")
        judged = load(judge_path) if judge_path.exists() else None
        if result and any(
            k in result and result[k] != item[k] for k in ("id", "task_id", "condition", "turn")
        ):
            raise ValueError("Result identity differs from scheduled item")
        if judged and judged.get("id", item["id"]) != item["id"]:
            raise ValueError("Judge identity differs from scheduled item")
        outcome = (result or {}).get("outcome", {})
        published = bool((result or {}).get("exposure"))
        answered = bool(
            (outcome.get("response") or {}).get("response_type") == "answer"
            and not outcome.get("error")
        )
        verdict = (
            (judged or {}).get("judgment") if (judged or {}).get("state") == "judged" else None
        )
        row = {
            **item,
            **manifest.get("task_metadata", {}).get(
                item["task_id"], {"subject": "unrecorded", "task_type": "unrecorded"}
            ),
            "published": published,
            "answered": answered,
            "valid_hint": bool(
                published
                and answered
                and verdict
                and all(verdict[d] == 1 for d in ("supported", "specific_help", "within_scope"))
            ),
            "automatic_judgment": verdict,
            "generation_error": (outcome.get("error") or {}).get("code"),
            "judge_state": (judged or {}).get("state", "missing"),
            "wall_seconds": (result or {}).get("wall_seconds"),
            "calls": outcome.get("budget", {}).get("consumed_calls"),
            "repair_calls": sum(
                a.get("purpose", a.get("stage")) in {"semantic_repair", "generation_format_repair"}
                for a in outcome.get("attempts", [])
            ),
        }
        by_condition[item["condition"]].append(row)
        rows.append(row)
        for role, attempts in (
            ("product", outcome.get("attempts", [])),
            ("offline_judge", (judged or {}).get("attempts", [])),
        ):
            for attempt in attempts:
                usage = attempt.get("usage", {})
                priced_config = (
                    judge_manifest["model"]
                    if role == "offline_judge" and judge_manifest
                    else manifest["model_config"]
                )
                priced_time = (
                    (judged or {}).get("completed_at")
                    if role == "offline_judge"
                    else (result or {}).get("completed_at")
                )
                estimate = cost_estimate(
                    usage,
                    priced_time or manifest["created_at"],
                    model=attempt.get("model"),
                    base_url=priced_config["base_url"],
                )
                usages.append(
                    {
                        "id": item["id"],
                        "role": role,
                        "purpose": attempt.get("purpose", attempt.get("stage", role)),
                        "usage": usage,
                        "latency_ms": attempt.get("latency_ms"),
                        "estimated_cny": estimate,
                    }
                )
    metrics = {}
    task_rates = {}
    for condition, items in by_condition.items():
        times = [i["wall_seconds"] for i in items if i["wall_seconds"] is not None]
        successful = [i for i in items if i["answered"]]
        judged = [i for i in items if i["automatic_judgment"]]
        metric = {
            "planned": len(items),
            "completed": len(times),
            "answered": len(successful),
            "judged": len(judged),
            "valid_hints_all_planned": sum(i["valid_hint"] for i in items),
            "valid_hint_rate_all_planned": statistics.mean(i["valid_hint"] for i in items),
            "error_counts": dict(
                Counter(
                    i["generation_error"] or "missing_or_nonanswer"
                    for i in items
                    if not i["answered"]
                )
            ),
            "mean_seconds_completed": statistics.mean(times) if times else None,
            "median_seconds_completed": statistics.median(times) if times else None,
            "product_calls": sum(i["calls"] for i in items if i["calls"] is not None),
            "requests_with_unknown_call_count": sum(i["calls"] is None for i in items),
            "repair_calls": sum(i["repair_calls"] for i in items),
        }
        for dimension in (
            "supported",
            "specific_help",
            "within_scope",
            "fact_error",
            "citation_complete",
            "complete_answer",
        ):
            numerator = sum(i["automatic_judgment"][dimension] for i in judged)
            metric[dimension] = {
                "positive": numerator,
                "judged_denominator": len(judged),
                "planned_denominator": len(items),
                "judged_rate": numerator / len(judged) if judged else None,
            }
        metrics[condition] = metric
        groups = defaultdict(list)
        for item in items:
            groups[item["task_id"]].append(float(item["valid_hint"]))
        task_rates[condition] = {key: statistics.mean(values) for key, values in groups.items()}
    comparisons = {}
    if manifest["experiment"] == "hints":
        for left, right in (("T2", "T1"), ("T2", "T3"), ("T2", "T4"), ("T2", "T0")):
            if left in task_rates and right in task_rates:
                comparisons[f"{left}_minus_{right}"] = paired_interval(
                    task_rates[left], task_rates[right]
                )
    purposes = defaultdict(
        lambda: {
            "calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "missing_usage_calls": 0,
            "estimated_cny_known": 0.0,
            "unknown_cost_calls": 0,
        }
    )
    for item in usages:
        target = purposes[item["purpose"]]
        target["calls"] += 1
        for key in ("input_tokens", "output_tokens"):
            target[key] += item["usage"].get(key) or 0
        target["missing_usage_calls"] += item["usage"].get("total_tokens") is None
        target["estimated_cny_known"] += item["estimated_cny"] or 0
        target["unknown_cost_calls"] += item["estimated_cny"] is None
    summary = {
        "run_manifest_sha256": digest(manifest),
        "experiment": manifest["experiment"],
        "split": manifest["split"],
        "metrics": metrics,
        "paired_task_comparisons": comparisons,
        "automatic_evaluation": {
            "source": "separate_model_judge",
            "same_model_family_bias": True,
            "scores_are_not_human_labels": True,
        },
        "human_evaluation": {
            "reviewers": 0,
            "completed_ratings": 0,
            "agreement": None,
            "status": "awaiting_actual_review",
        },
        "tariff": TARIFF,
        "pricing_time_scope": "Per-request or offline-judge completion timestamp is a proxy for individual call pricing time; a request crossing a tariff boundary may differ from the provider invoice.",
        "usage_by_purpose": dict(purposes),
        "items": rows,
        "strata": {},
    }
    for field in ("subject", "task_type"):
        strata = {}
        for value in sorted({row[field] for row in rows}):
            strata[value] = {}
            for condition in by_condition:
                selected = [r for r in rows if r[field] == value and r["condition"] == condition]
                strata[value][condition] = {
                    "planned": len(selected),
                    "answered": sum(r["answered"] for r in selected),
                    "valid_hints": sum(r["valid_hint"] for r in selected),
                    "valid_hint_rate_all_planned": sum(r["valid_hint"] for r in selected)
                    / len(selected)
                    if selected
                    else None,
                }
        summary["strata"][field] = strata
    if manifest["experiment"] == "citations":
        for condition, metric in metrics.items():
            items = by_condition[condition]
            correct = sum(
                bool(
                    i["answered"]
                    and i["automatic_judgment"]
                    and i["automatic_judgment"]["supported"]
                    and i["automatic_judgment"]["complete_answer"]
                    and not i["automatic_judgment"]["fact_error"]
                )
                for i in items
            )
            metric["complete_supported_answer_rate_all_planned"] = correct / len(items)
            metric.pop("valid_hints_all_planned", None)
            metric.pop("valid_hint_rate_all_planned", None)
        for field, strata in summary["strata"].items():
            for value, conditions in strata.items():
                for condition, metric in conditions.items():
                    selected = [
                        r for r in rows if r["condition"] == condition and r[field] == value
                    ]
                    correct = sum(
                        bool(
                            r["answered"]
                            and r["automatic_judgment"]
                            and r["automatic_judgment"]["supported"]
                            and r["automatic_judgment"]["complete_answer"]
                            and not r["automatic_judgment"]["fact_error"]
                        )
                        for r in selected
                    )
                    metric.pop("valid_hints", None)
                    metric.pop("valid_hint_rate_all_planned", None)
                    metric["complete_supported_answers"] = correct
                    metric["complete_supported_answer_rate_all_planned"] = (
                        correct / len(selected) if selected else None
                    )
        summary["citation_primary_metric"] = (
            "Complete supported direct answers among all planned requests; citation completeness is reported separately."
        )
    freeze(run / "analysis.json", summary)
    freeze(run / "usage-ledger.json", {"tariff": TARIFF, "calls": usages})
    return summary
