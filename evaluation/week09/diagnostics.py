"""Separate observable failure signals from unknown semantic and human labels."""

from collections import Counter
import hashlib
import json


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def diagnose(record):
    outcome = record.get("outcome") or {}
    error = outcome.get("error") or record.get("error") or {}
    code = error.get("code") if isinstance(error, dict) else str(error)
    checks = outcome.get("checks") or []
    signals = []
    if not outcome:
        signals.append("execution_or_input_failure")
    if code and any(
        word in code.upper() for word in ("EMPTY", "TIMEOUT", "TRANSPORT", "RATE_LIMIT")
    ):
        signals.append("provider_transport_or_empty_content")
    if code and any(word in code.upper() for word in ("SCHEMA", "FORMAT", "PARSE", "CONTRACT")):
        signals.append("output_contract_failure")
    for check in checks:
        if check.get("checker_inconsistencies"):
            signals.append("checker_record_inconsistency")
        judgment = check.get("judgment") or {}
        if any(
            judgment.get(key) is False
            for key in ("scope_ok", "evidence_display_ok", "cumulative_ok")
        ):
            signals.append("automatic_teaching_disclosure_rejection")
        if judgment.get("coverage") in {"none", "supported_partial"}:
            signals.append("automatic_draft_coverage_gap")
        issues = json.dumps(check.get("structural_issues") or [], sort_keys=True).lower()
        if "binding" in issues or "citation" in issues:
            signals.append("citation_binding_or_structure")
    if code == "SEMANTIC_CHECK_FAILED":
        signals.append("automatic_checker_rejection")
    published = outcome.get("response") is not None and not outcome.get("error")
    return {
        "published": published,
        "error_code": code or None,
        "observed_signals": sorted(set(signals)),
        "available_drafts": len(outcome.get("drafts") or []),
        "checker_records": len(checks),
        "context_sufficient_human": None,
        "draft_correct_human": None,
        "checker_false_block_human": None,
        "checker_false_release_human": None,
        "interpretation": "Signals identify review strata; semantic causes require independent labels.",
    }


def draft_observations(record):
    """Bind each draft to checks for that exact revision and projection identity."""
    outcome = record.get("outcome") or {}
    checks = outcome.get("checks") or []
    result = []
    for draft in outcome.get("drafts") or []:
        matches = [c for c in checks if c.get("revision") == draft.get("revision")]
        # A checker contract repair creates another record for the same draft.
        latest = max(matches, key=lambda c: c.get("checker_contract_revision", 0), default=None)
        projection = draft.get("projection") or {}
        expected = latest.get("projection_hash") if latest else None
        actual = hashlib.sha256(
            json.dumps(
                {k: v for k, v in projection.items() if k != "content_hash"},
                sort_keys=True,
                ensure_ascii=False,
            ).encode()
        ).hexdigest()
        stored = projection.get("content_hash")
        binding = (
            "unrecorded" if expected is None else "matched" if actual == expected else "mismatch"
        )
        if stored is not None and stored != actual:
            binding = "mismatch"
        result.append(
            {
                "revision": draft.get("revision"),
                "draft": draft,
                "checker": latest,
                "projection_hash": actual,
                "checker_projection_hash": expected,
                "projection_binding": binding,
            }
        )
    return result


def summarize(records):
    rows = [diagnose(row) for row in records]
    return {
        "requests": len(rows),
        "published": sum(row["published"] for row in rows),
        "failed": sum(not row["published"] for row in rows),
        "error_codes": dict(Counter(row["error_code"] for row in rows if row["error_code"])),
        "observed_signals": dict(
            Counter(signal for row in rows for signal in row["observed_signals"])
        ),
        "independent_human_labels": 0,
        "checker_false_block_rate": None,
        "checker_false_release_rate": None,
        "context_sufficiency_rate": None,
        "interpretation": "Operational counts and review strata; no human correctness inferred from publication or rejection.",
    }
