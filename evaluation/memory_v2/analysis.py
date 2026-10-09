"""All-planned metrics and paired family/trajectory bootstrap; no invented scores."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import random
import statistics

from evaluation.enhancement.protocol import digest, freeze
from evaluation.memory_v2.judging import SCORE_FIELDS, checked_identity, validate_judgment
from evaluation.memory_v2.protocol import SEED
from evaluation.memory_v2.runner import load, now

PRIMARY = {"B": ("B2", "B1"), "T": ("T2", "T1"), "M": ("M4", "M3")}
TOKEN_FIELDS = (
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "reasoning_tokens",
    "cache_hit_input_tokens",
    "cache_miss_input_tokens",
)


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def composite(study, scores, answered):
    """Conservative end-to-end success; missing ratings never become positive."""
    if not answered or not scores:
        return False
    needed = ["factual_correct", "conditions_units"]
    if study == "A":
        needed += ["required_coverage"]
    else:
        needed += ["source_support", "citation_mapping", "citation_support"]
        if study == "T":
            needed += ["useful_hint", "allowed_disclosure"]
        else:
            needed += ["required_coverage"]
    if study == "M":
        needed += ["memory_appropriate", "current_instruction_followed"]
        if any(
            scores.get(k) != 0
            for k in (
                "stale_memory_reuse",
                "memory_scope_violation",
                "unsupported_learner_inference",
            )
        ):
            return False
    return all(scores.get(k) == 1 for k in needed)


def paired_cluster(left, right, *, samples=10000):
    """Equal-weight family means; all repeated turns remain in their cluster."""
    if not left or set(left) != set(right):
        raise ValueError("Primary contrast requires the same nonempty planned clusters")
    if samples != 10000:
        raise ValueError("Registered bootstrap requires exactly 10000 resamples")
    keys = sorted(left)
    if any(len(left[k]) != len(right[k]) or not left[k] for k in keys):
        raise ValueError("Paired clusters require the same positive number of planned turns")
    differences = [statistics.mean(left[k]) - statistics.mean(right[k]) for k in keys]
    rng = random.Random(SEED)
    draws = sorted(
        statistics.mean(rng.choices(differences, k=len(differences))) for _ in range(samples)
    )
    return {
        "difference": statistics.mean(differences),
        "ci95": [draws[250], draws[9750]],
        "paired_clusters": len(keys),
        "paired_requests": sum(len(left[k]) for k in keys),
        "left_successes": sum(sum(left[k]) for k in keys),
        "right_successes": sum(sum(right[k]) for k in keys),
        "cluster_wins": sum(d > 0 for d in differences),
        "cluster_losses": sum(d < 0 for d in differences),
        "cluster_ties": sum(d == 0 for d in differences),
        "cluster_differences": dict(zip(keys, differences)),
        "bootstrap_samples": samples,
        "seed": SEED,
        "method": "paired equal-weight family/trajectory means; percentile cluster bootstrap; all planned turns retained",
    }


def selected_state_metrics(result):
    """Explicit field-selection diagnostics, separate from semantic answer scores."""
    if not result or result["study"] != "M":
        return None
    if result["arm"] not in {"M3", "M4"}:
        return {
            "applicable": False,
            "required_recall": None,
            "precision": None,
            "reason": "Only M3/M4 expose comparable typed field keys; legacy memory, summary and profile state retain their original representations.",
        }
    state = result.get("memory_state_trace")
    if state is None:
        return None
    context = state.get("memory_context") or {}
    entries = context.get("entries", [])
    required = set((result.get("memory_expected") or {}).get("selected_fields", []))
    excluded = set((result.get("memory_expected") or {}).get("excluded_fields", []))
    selected = {e.get("field_key") for e in entries if e.get("field_key")}
    # The authored sets are intentionally partial: unlabelled selected fields
    # are not automatically false positives and cannot form a precision score.
    return {
        "applicable": True,
        "required_fields": sorted(required),
        "explicitly_excluded_fields": sorted(excluded),
        "selected_typed_fields": sorted(selected),
        "required_recall": ratio(len(required & selected), len(required)),
        "excluded_selected_count": len(excluded & selected),
        "precision": None,
        "precision_limit": "Authored required/excluded fields are partial labels, not an exhaustive relevant-set oracle; legacy untyped and summary state are not directly comparable.",
        "entries_without_field_key": sum(not e.get("field_key") for e in entries),
        "source_versions_present": all(
            e.get("id") and e.get("version") and e.get("source_message_id") for e in entries
        ),
    }


def analyse(output):
    plan = load(output / "judge-plan.json")
    scheduled = plan["rows"]
    identities = [r["id"] for r in scheduled]
    if not scheduled or len(identities) != len(set(identities)):
        raise ValueError("Invalid planned denominator")
    if any(p.stem not in set(identities) for p in (output / "judgments").glob("*.json")):
        raise ValueError("Unscheduled judgment found")
    rows, attempts, groups = [], [], defaultdict(list)
    for item in scheduled:
        result = load(Path(item["result_path"])) if item["result_path"] else None
        if result:
            checked_identity(item, result)
            if digest(result) != item["result_sha256"]:
                raise ValueError("Generation output changed from judge freeze")
        path = output / "judgments" / (item["id"] + ".json")
        judged = load(path) if path.exists() else None
        if judged and any(
            judged.get(k) != v
            for k, v in {
                "id": item["id"],
                "plan_sha256": digest(plan),
                "result_sha256": item["result_sha256"],
                "payload_sha256": item["payload_sha256"],
            }.items()
        ):
            raise ValueError("Judgment is not bound to this exact plan and result")
        scores = None
        if judged and judged["state"] == "judged":
            if not item["payload"]:
                raise ValueError("A result without delivered output cannot be judged")
            scores = validate_judgment(judged["judgment"], item["payload"])
        outcome = (result or {}).get("outcome") or {}
        response = outcome.get("response")
        delivered = bool(response and not outcome.get("error"))
        status = (result or {}).get("status", "missing")
        if delivered and response is not None and status != response["response_type"]:
            raise ValueError("Recorded delivery status differs from actual response")
        answered = delivered and response is not None and response["response_type"] == "answer"
        waiting = status == "waiting_external"
        attempted = bool(result and status not in {"planned", "not_run", "waiting_external"})
        eligible = item["arm"] != "A2" or bool((result or {}).get("oracle_confirmation"))
        row = {k: item[k] for k in ("id", "study", "case_id", "family", "arm", "turn")}
        row.update(
            status=status,
            eligible=eligible,
            attempted=attempted,
            delivered=delivered,
            answered=answered,
            waiting_external=waiting,
            judgment_state=(judged or {}).get("state", "missing"),
            judgment=scores,
            end_to_end_success=composite(item["study"], scores, answered),
            error=(outcome.get("error") or {}).get("code") or (result or {}).get("reason"),
            wall_seconds=(result or {}).get("wall_seconds"),
            selected_state=selected_state_metrics(result),
            result_sha256=item["result_sha256"],
            human_rating=None,
        )
        rows.append(row)
        groups[(item["study"], item["arm"])].append(row)
        for purpose, values in (
            (
                "generation",
                outcome.get("attempts") or (result or {}).get("recovered_attempts") or [],
            ),
            ("offline_judge", (judged or {}).get("attempts") or []),
        ):
            for index, a in enumerate(values, 1):
                attempts.append(
                    {
                        "item_id": item["id"],
                        "study": item["study"],
                        "arm": item["arm"],
                        "role": purpose,
                        "attempt_index": index,
                        "purpose": a.get("purpose", a.get("stage", purpose)),
                        "provider": a.get("provider"),
                        "model": a.get("model"),
                        "configuration_id": a.get("configuration_id"),
                        "provider_request_id": a.get("provider_request_id"),
                        "request_submitted": a.get("request_submitted"),
                        "usage": a.get("usage") or {},
                        "error": (a.get("error") or {}).get("code"),
                        "latency_ms": a.get("latency_ms"),
                        "cost": None,
                        "cost_scope": "Unpriced measured attempt; requires separately frozen applicable provider tariff, never assumed zero.",
                    }
                )
    arms = {}
    for (study, arm), group in groups.items():
        answered = [r for r in group if r["answered"]]
        judged_answers = [r for r in answered if r["judgment"]]
        all_judged = [r for r in group if r["judgment"]]
        eligible = [r for r in group if r["eligible"]]
        successes = sum(r["end_to_end_success"] for r in group)
        metrics = {
            "planned": len(group),
            "eligible": len(eligible),
            "attempted": sum(r["attempted"] for r in group),
            "delivered": sum(r["delivered"] for r in group),
            "answered": len(answered),
            "refused": sum(r["status"] == "refusal" for r in group),
            "clarified": sum(r["status"] == "clarification" for r in group),
            "failed": sum(r["status"] == "failed" for r in group),
            "unexecuted": sum(
                r["status"] in {"missing", "planned", "not_run", "waiting_external"} for r in group
            ),
            "waiting_external": sum(r["waiting_external"] for r in group),
            "judged": len(all_judged),
            "judged_answers": len(judged_answers),
            "judgment_coverage_delivered": ratio(
                len(all_judged), sum(r["delivered"] for r in group)
            ),
            "judgment_coverage_answers": ratio(len(judged_answers), len(answered)),
            "delivery_rate_planned_eligible": ratio(
                sum(r["delivered"] for r in eligible), len(eligible)
            ),
            "end_to_end_successes": successes,
            "end_to_end_rate_all_planned": ratio(successes, len(group)),
            "end_to_end_rate_planned_eligible": ratio(
                sum(r["end_to_end_success"] for r in eligible), len(eligible)
            ),
            "generation_error_counts": dict(Counter(r["error"] for r in group if r["error"])),
            "judge_states": dict(Counter(r["judgment_state"] for r in group)),
            "dimensions_among_judged_answers": {},
            "unnecessary_refusal_among_judged_nonanswers": None,
            "human_ratings": 0,
        }
        for name in sorted(SCORE_FIELDS - {"unnecessary_refusal"}):
            values = [
                r["judgment"][name] for r in judged_answers if r["judgment"][name] is not None
            ]
            metrics["dimensions_among_judged_answers"][name] = {
                "positive": sum(values),
                "judged_applicable": len(values),
                "rate": statistics.mean(values) if values else None,
            }
        refusal = [
            r["judgment"]["unnecessary_refusal"]
            for r in all_judged
            if r["judgment"]["unnecessary_refusal"] is not None
        ]
        metrics["unnecessary_refusal_among_judged_nonanswers"] = {
            "positive": sum(refusal),
            "judged_applicable": len(refusal),
            "rate": statistics.mean(refusal) if refusal else None,
        }
        arms[arm] = metrics
    contrasts = {}
    for study, (left_arm, right_arm) in PRIMARY.items():
        if (study, left_arm) not in groups or (study, right_arm) not in groups:
            contrasts[study] = {
                "state": "missing_planned_comparison",
                "left": left_arm,
                "right": right_arm,
            }
            continue
        clustered = []
        for arm in (left_arm, right_arm):
            values = defaultdict(list)
            for r in groups[(study, arm)]:
                values[r["family"]].append(int(r["end_to_end_success"]))
            clustered.append(values)
        contrasts[study] = {
            "classification": "registered_primary",
            "left": left_arm,
            "right": right_arm,
            "outcome": "conservative_end_to_end_success_all_planned",
            **paired_cluster(*clustered),
        }
    usage = {}
    for field in TOKEN_FIELDS:
        observed = [a["usage"].get(field) for a in attempts]
        known = [v for v in observed if type(v) is int and v >= 0]
        usage[field] = {
            "known_sum": sum(known),
            "attempts_with_value": len(known),
            "attempts_missing_value": len(observed) - len(known),
            "complete_total": sum(known) if len(known) == len(observed) else None,
        }
    return {
        "version": "memory_v2_analysis_v1",
        "created_at": now(),
        "judge_plan_sha256": digest(plan),
        "planned": len(rows),
        "arms": arms,
        "primary_contrasts": contrasts,
        "rows": rows,
        "attempts": attempts,
        "usage": usage,
        "human_ratings": 0,
        "limits": [
            "Automatic same-family judgments can share generator errors; independent human ratings remain absent.",
            "A factual correctness is separate from source support; A2 missing confirmation stays visible.",
            "All failed/missing/unjudged planned requests are unsuccessful only in conservative end-to-end composites, not fabricated factual-error labels.",
            "M primary combines scientific delivery and appropriate memory use; separate dimensions show the component effects.",
            "Selected-field labels are partial; no semantic selection precision is invented.",
            "Usage includes only these answer/judge attempts. Extraction, summary, preparation and diagnostic costs require separate receipt aggregation.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--judge", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = analyse(args.judge)
    freeze(args.output, report)
    print(
        json.dumps({"planned": report["planned"], "arms": len(report["arms"]), "human_ratings": 0})
    )


if __name__ == "__main__":
    main()
