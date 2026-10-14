"""Terminal accounting that keeps provider failures and missing labels visible."""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
from pathlib import Path

from . import PROTOCOL_VERSION
from .protocol import canonical, load_frozen
from .statistics import distribution, teaching_contrasts

TERMINAL_STATES = {
    "answered",
    "hinted",
    "supported_partial",
    "evidence_refusal",
    "clarification",
    "social_response",
    "model_failure",
    "retrieval_failure",
    "local_model_failure",
    "timeout",
    "cancelled",
    "empty_output",
    "invalid_output",
    "policy_block",
    "security_block",
    "execution_failure",
    "diagnostic_observation",
}
DELIVERED = {"answered", "hinted", "supported_partial"}
TOKEN_FIELDS = ("input_tokens", "output_tokens", "cache_hit_input_tokens")


def _nonnegative(value: object, *, integer: bool = False) -> bool:
    if integer:
        return type(value) is int and value >= 0
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def validate_terminal(row: dict, expected: dict) -> None:
    if row.get("schedule_id") != expected["id"]:
        raise ValueError("Terminal identity does not match its frozen schedule")
    if row.get("state") not in TERMINAL_STATES:
        raise ValueError("Unknown terminal state")
    if not _nonnegative(row.get("elapsed_ms")):
        raise ValueError("Every terminal outcome needs measured nonnegative elapsed time")
    if row.get("provider_calls") is not None and not _nonnegative(
        row["provider_calls"], integer=True
    ):
        raise ValueError("Known provider attempts must be nonnegative integers")
    usage = row.get("usage") or {}
    for field in TOKEN_FIELDS:
        value = usage.get(field)
        if value is not None and not _nonnegative(value, integer=True):
            raise ValueError(f"Invalid {field} counter")
    if row["state"] in DELIVERED and not row.get("learner_visible_output"):
        raise ValueError("Delivered outcomes must retain actual learner-visible output")
    if row["state"] not in DELIVERED and row.get("learner_visible_output"):
        raise ValueError("A failure/refusal cannot be silently recategorized as delivery")


def write_terminal(folder: Path, row: dict) -> Path:
    manifest = load_frozen(folder)
    schedule = {item["id"]: item for item in manifest["schedule"]}
    identity = row.get("schedule_id")
    if identity not in schedule:
        raise ValueError("Unscheduled outcome")
    validate_terminal(row, schedule[identity])
    destination = folder / "outcomes" / (identity.replace("::", "--") + ".json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as stream:
        stream.write(canonical(row))
    return destination


def _tariff_cost(usage: dict, tariff: dict) -> float | None:
    incoming, outgoing, cached = (usage.get(field) for field in TOKEN_FIELDS)
    if any(value is None for value in (incoming, outgoing, cached)):
        return None
    if cached > incoming:
        raise ValueError("Cache-hit input tokens exceed input tokens")
    keys = ("input_per_million", "output_per_million", "cache_hit_input_per_million")
    if any(not _nonnegative(tariff.get(key)) for key in keys):
        return None
    return (
        (incoming - cached) * tariff[keys[0]]
        + outgoing * tariff[keys[1]]
        + cached * tariff[keys[2]]
    ) / 1_000_000


def _recorded_cost(row: dict, tariff: dict) -> float | None:
    """A recorded zero-call outcome has no provider charge for this request."""
    if row.get("provider_calls") == 0:
        usage = row.get("usage") or {}
        if any(usage.get(field) not in (None, 0) for field in TOKEN_FIELDS):
            raise ValueError("Zero-call outcome conflicts with recorded provider tokens")
        return 0.0
    return _tariff_cost(row.get("usage") or {}, tariff)


def _rate(numerator: int, denominator: int) -> dict:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "rate": numerator / denominator if denominator else None,
    }


def summarize(folder: Path, *, ratings_path: Path | None = None) -> dict:
    manifest = load_frozen(folder)
    ratings = json.loads(ratings_path.read_text(encoding="utf-8")) if ratings_path else {}
    labels = json.loads((folder / "private-labels.json").read_text(encoding="utf-8"))
    if not isinstance(ratings, dict):
        raise ValueError("Independent ratings must be keyed by frozen schedule ID")
    schedule = {item["id"]: item for item in manifest["schedule"]}
    if set(ratings) - set(schedule):
        raise ValueError("Independent ratings contain unscheduled IDs")
    rows = {}
    for identity, expected in schedule.items():
        path = folder / "outcomes" / (identity.replace("::", "--") + ".json")
        if path.exists():
            row = json.loads(path.read_text(encoding="utf-8"))
            validate_terminal(row, expected)
            rows[identity] = row
    family_arms = defaultdict(list)
    for identity, item in schedule.items():
        family_arms[(item["family"], item["arm"])].append((identity, item))
    metrics = {}
    teaching_primary = []
    for (family, arm), entries in sorted(family_arms.items()):
        observed = [
            (identity, item, rows[identity]) for identity, item in entries if identity in rows
        ]
        states = Counter(row["state"] for _, _, row in observed)
        latencies = {
            "all": distribution([row["elapsed_ms"] for _, _, row in observed]),
            "successful": distribution(
                [row["elapsed_ms"] for _, _, row in observed if row["state"] in DELIVERED]
            ),
            "failed_or_refused": distribution(
                [row["elapsed_ms"] for _, _, row in observed if row["state"] not in DELIVERED]
            ),
        }
        known_costs = [
            _recorded_cost(row, manifest["candidate"]["tariff"]) for _, _, row in observed
        ]
        judged = [
            (identity, item, rating)
            for identity, item, _ in observed
            if (rating := ratings.get(identity)) is not None
        ]
        for identity, item, rating in judged:
            if rating.get("provenance") not in {
                "human_existing",
                "program_derived",
                "ai_generated",
            }:
                raise ValueError("Rated outcomes require explicit label provenance")
        if family == "joint_tutoring":
            for identity, item, row in observed:
                rating = ratings.get(identity) or {}
                if row["state"] not in DELIVERED:
                    value = 0.0
                elif type(rating.get("useful_accurate_within_help")) is bool:
                    value = float(rating["useful_accurate_within_help"])
                else:
                    continue
                teaching_primary.append(
                    {"concept_group": item["concept_group"], "arm": arm, "value": value}
                )
        eligible = [rating for _, _, rating in judged if type(rating.get("correct")) is bool]
        if family == "joint_tutoring":
            quality = [
                rating
                for _, _, rating in judged
                if type(rating.get("useful_accurate_within_help")) is bool
            ]
            primary = _rate(sum(r["useful_accurate_within_help"] for r in quality), len(entries))
            scored_ids = {
                identity
                for identity, _, rating in judged
                if type(rating.get("useful_accurate_within_help")) is bool
            }
            unrated_deliveries = sum(
                identity not in scored_ids and row["state"] in DELIVERED
                for identity, _, row in observed
            )
            primary["unrated_deliveries"] = unrated_deliveries
            primary["terminal_failures_counted_zero"] = sum(
                row["state"] not in DELIVERED for _, _, row in observed
            )
            primary["unstarted"] = len(entries) - len(observed)
            primary["interpretation"] = (
                "Reported only when all delivered hints have independent ratings and every planned request is terminal; terminal failures count zero."
            )
            if unrated_deliveries or primary["unstarted"]:
                primary["rate"] = None
        else:
            primary = None
        metrics.setdefault(family, {})[arm] = {
            "planned": len(entries),
            "terminal": len(observed),
            "unstarted": len(entries) - len(observed),
            "terminal_states": dict(states),
            "substantive_delivery": _rate(
                sum(row["state"] in DELIVERED for _, _, row in observed), len(entries)
            ),
            "latency_ms": latencies,
            "provider_calls_known_total": sum(
                row["provider_calls"] for _, _, row in observed if row["provider_calls"] is not None
            ),
            "provider_calls_unknown_outcomes": len(entries)
            - sum(row["provider_calls"] is not None for _, _, row in observed),
            "cost_estimate": {
                "known_subtotal": sum(value for value in known_costs if value is not None),
                "known_terminal_count": sum(value is not None for value in known_costs),
                "unknown_terminal_count": len(observed)
                - sum(value is not None for value in known_costs),
                "unstarted_count": len(entries) - len(observed),
                "currency": manifest["candidate"]["tariff"].get("currency"),
                "invoice_reconciled": False,
            },
            "independently_scored": len(judged),
            "correctness_scored_subset": _rate(sum(r["correct"] for r in eligible), len(eligible)),
            "teaching_primary_scheduled": primary,
            "rating_provenance": dict(Counter(r["provenance"] for _, _, r in judged)),
        }
    from .quality import stratified_quality

    return {
        "schema": PROTOCOL_VERSION + "_results",
        "manifest_sha256": json.loads((folder / "freeze-receipt.json").read_text(encoding="utf-8"))[
            "manifest_sha256"
        ],
        "split": manifest["split"],
        "planned": len(schedule),
        "terminal": len(rows),
        "unstarted": len(schedule) - len(rows),
        "families": metrics,
        "label_source_quality": stratified_quality(manifest, rows, ratings, labels),
        "teaching_quality_contrasts": teaching_contrasts(teaching_primary),
        "quality_boundary": "Independent semantic ratings remain separate from online checker decisions and operational delivery.",
    }
