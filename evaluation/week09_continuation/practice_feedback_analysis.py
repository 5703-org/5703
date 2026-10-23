"""Check frozen practice-study lineage and export aggregate automatic observations."""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import statistics

from .practice_feedback_formal import FREEZE_SCHEMA, RUN_SCHEMA, load_catalogue


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quantile(values: list[float], proportion: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * proportion
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower), 6)


def analyze(frozen_dir: Path, pilot_dir: Path, reserved_dir: Path) -> dict:
    manifest_path = frozen_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != FREEZE_SCHEMA:
        raise ValueError("The candidate practice freeze is invalid")
    catalogue_path = frozen_dir / "catalogue.json"
    catalogue = load_catalogue(catalogue_path)
    if digest(catalogue_path) != manifest["catalogue_sha256"]:
        raise ValueError("Frozen practice catalogue changed")
    if digest(Path(__file__).with_name("practice_feedback_formal.py")) != manifest["runner_sha256"]:
        raise ValueError("The execution runner differs from the frozen runner")
    planned = {case["id"]: case for case in catalogue["cases"]}
    runs = {}
    for split, directory in (("pilot", pilot_dir), ("reserved", reserved_dir)):
        start = json.loads((directory / "run-start.json").read_text(encoding="utf-8"))
        result = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
        if (
            start.get("schema") != RUN_SCHEMA
            or result.get("schema") != RUN_SCHEMA
            or start.get("split") != split
            or result.get("split") != split
            or start.get("manifest_sha256") != digest(manifest_path)
            or result.get("frozen_manifest_sha256") != digest(manifest_path)
            or result.get("catalogue_sha256") != manifest["catalogue_sha256"]
            or result.get("candidate_archive_sha256") != manifest["package_archive_sha256"]
        ):
            raise ValueError(f"Study run lineage mismatch: {split}")
        selected = {cid: case for cid, case in planned.items() if case["split"] == split}
        by_id = {case["id"]: case for case in result["case_records"]}
        if set(by_id) != set(selected):
            raise ValueError(f"Study cases differ from the freeze: {split}")
        for cid, case in selected.items():
            record = by_id[cid]
            terminal_file = directory / "case-terminals" / f"{cid}.json"
            if (
                not terminal_file.is_file()
                or json.loads(terminal_file.read_text(encoding="utf-8")) != record
            ):
                raise ValueError(f"Private terminal record is absent or changed: {cid}")
            if len(record["attempts"]) != len(case["attempts"]):
                raise ValueError(f"Attempt count differs from the frozen case: {cid}")
            for ordinal, (actual, frozen) in enumerate(
                zip(record["attempts"], case["attempts"], strict=True), 1
            ):
                if (
                    actual["ordinal"] != ordinal
                    or actual["response"] != frozen["response"]
                    or actual["expected_rule_outcome"] != frozen["expected_rule_outcome"]
                ):
                    raise ValueError(f"Attempt or private label changed: {cid}/{ordinal}")
                if not (directory / "terminals" / f"{cid}-attempt-{ordinal}.json").is_file():
                    raise ValueError(f"No durable attempt terminal: {cid}/{ordinal}")
        if (
            result["scheduled_cases"] != manifest["planned"][split]["cases"]
            or result["scheduled_attempts"] != manifest["planned"][split]["attempts"]
            or result["terminal_cases"] != len(selected)
            or result["terminal_attempts"] != sum(len(c["attempts"]) for c in selected.values())
        ):
            raise ValueError(f"Study denominator or terminal count changed: {split}")
        runs[split] = result

    automatic = {}
    for split, result in runs.items():
        latencies: list[float] = []
        kinds: dict[str, list[dict]] = defaultdict(list)
        observation_counts: Counter[str] = Counter()
        for case in result["case_records"]:
            kinds[case["kind"]].append(case)
            for attempt in case["attempts"]:
                latencies.append(attempt["elapsed_s"])
                observation_counts[attempt["observed_outcome"]] += 1
        automatic[split] = {
            "scheduled_cases": result["scheduled_cases"],
            "terminal_cases": result["terminal_cases"],
            "scheduled_attempts": result["scheduled_attempts"],
            "terminal_attempts": result["terminal_attempts"],
            "rule_concordant_attempts": result["rule_concordant_attempts"],
            "published_and_source_verified_items": result["source_and_publication_passed"],
            "public_answer_key_isolation_passed_items": result["answer_key_isolation_passed"],
            "completed_items": result["completed_practice_items"],
            "review_entries_created": result["review_entries_created"],
            "outcomes": dict(observation_counts),
            "by_type": {
                kind: {
                    "items": len(records),
                    "attempts": sum(len(row["attempts"]) for row in records),
                    "rule_concordant": sum(
                        sum(a["rule_concordant"] for a in row["attempts"]) for row in records
                    ),
                }
                for kind, records in sorted(kinds.items())
            },
            "attempt_post_latency_s": {
                "p50": quantile(latencies, 0.50),
                "p95": quantile(latencies, 0.95),
                "mean": round(statistics.mean(latencies), 6) if latencies else None,
            },
            "provider_calls": result["provider_calls"],
            "provider_cost_usd": result["provider_cost_usd"],
            "http_failures": result["http_failures"],
            "unretired_items": result["unretired_item_count"],
            "human_reviews_completed": result["human_reviews_completed"],
        }
    source_summary = Counter(row["title"] for row in manifest["source_audit"]["sources"])
    return {
        "schema": "week09_practice_feedback_formal_addendum_v1",
        "candidate_scope": "published_V11_isolated_HTTP_candidate_only",
        "protocol_role": "small_frozen_source_grounded_practice_feedback_addendum",
        "freeze_sha256": digest(manifest_path),
        "catalogue_sha256": manifest["catalogue_sha256"],
        "execution_runner_sha256": manifest["runner_sha256"],
        "candidate_archive_sha256": manifest["package_archive_sha256"],
        "corpus_release_id": manifest["source_audit"]["release_id"],
        "official_source_units_verified_before_pilot": manifest["source_audit"][
            "verified_source_units"
        ],
        "source_books": dict(source_summary),
        "pilot_gate_passed": all(
            (
                automatic["pilot"]["terminal_cases"] == manifest["planned"]["pilot"]["cases"],
                automatic["pilot"]["rule_concordant_attempts"]
                == manifest["planned"]["pilot"]["attempts"],
                automatic["pilot"]["http_failures"] == 0,
                automatic["pilot"]["unretired_items"] == 0,
            )
        ),
        "automatic": automatic,
        "source_lineage": manifest["source_audit"]["sources"],
        "known_semantic_limitation": {
            "case_id": "PF-R08",
            "probe": "A response says a eukaryotic cell has no membrane-bound nucleus but has organelles.",
            "observed_rule_outcome": "insufficient",
            "error_category": "ambiguous_negation",
            "interpretation": "The rule flags a contradiction as requiring clarification; it does not certify the response as correct. Independent reviewers must assess whether feedback should instead label the explicit misconception incorrect.",
        },
        "interpretation_limits": [
            "Rule concordance compares actual feedback with authored program-derived rule expectations; it is not semantic answer accuracy.",
            "Choice and numeric keys are source-grounded author designs; item solvability, equivalence coverage and feedback pedagogy have no independent human labels.",
            "Wrong then corrected attempts are paired inside each item, so any second-attempt success is not a measured learning gain.",
            "The ten reserved items are below the approximately 160-question planning scale; this addendum is not a population-level estimate.",
            "Only the V11 candidate was executed; no previous-release practice baseline exists in the registered family.",
            "The measured latency is the learner attempt POST only; it excludes item authoring, validation, publication and learner reading time.",
        ],
        "human_ratings": 0,
        "invoice_reconciled": False,
        "formal_family_result_status": "small_automatic_candidate_only",
    }
