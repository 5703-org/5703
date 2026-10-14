"""Record a pilot-based size and quality decision before opening reserved groups."""

from __future__ import annotations

import json
import math
from pathlib import Path

from . import PROTOCOL_VERSION
from .outcomes import summarize
from .protocol import canonical, digest_bytes, load_frozen


def sample_decision(
    pilot_folder: Path,
    output: Path,
    *,
    independent_ratings: Path,
    quality_thresholds: Path,
    calibration_result: Path,
) -> dict:
    if output.exists():
        raise ValueError("Preserve the prior pilot decision")
    manifest = load_frozen(pilot_folder)
    if manifest["split"] != "pilot":
        raise ValueError("Only an integrated pilot can determine reserved sample size")
    summary = summarize(pilot_folder, ratings_path=independent_ratings)
    thresholds = json.loads(quality_thresholds.read_text(encoding="utf-8"))
    if digest_bytes(quality_thresholds.read_bytes()) != manifest["candidate"].get(
        "quality_thresholds_sha256"
    ):
        raise ValueError("Quality thresholds differ from the pre-pilot candidate freeze")
    if thresholds.get("schema") != PROTOCOL_VERSION + "_quality_thresholds":
        raise ValueError("Quality threshold contract is not versioned")
    if not 0 < thresholds.get("target_95_half_width", 0) < 1:
        raise ValueError("A declared target interval half-width in (0, 1) is required")
    contrast = summary["teaching_quality_contrasts"]["D_minus_A"]
    sd = contrast["paired_sd"]
    conservative_sd = max(sd or 0, 0.25)
    estimate = math.ceil((1.96 * conservative_sd / thresholds["target_95_half_width"]) ** 2)
    required = max(16, estimate)
    all_terminal = summary["terminal"] == summary["planned"]
    enough_pairs = contrast["paired_concept_groups"] >= 2
    ratings_complete = all(
        metrics.get("teaching_primary_scheduled", {}).get("rate") is not None
        for arm, metrics in summary["families"].get("joint_tutoring", {}).items()
        if arm in {"A", "B", "C", "D"}
    ) and {"A", "B", "C", "D"} <= set(summary["families"].get("joint_tutoring", {}))
    calibration = json.loads(calibration_result.read_text(encoding="utf-8"))
    calibrated, calibration_checks = calibration_pass(
        calibration, thresholds.get("independent_judge_calibration")
    )
    ready = all_terminal and enough_pairs and ratings_complete and calibrated
    result = {
        "schema": PROTOCOL_VERSION + "_pilot_decision",
        "pilot_manifest_sha256": digest_bytes((pilot_folder / "manifest.json").read_bytes()),
        "independent_ratings_sha256": digest_bytes(independent_ratings.read_bytes()),
        "thresholds_sha256": digest_bytes(quality_thresholds.read_bytes()),
        "calibration_result_sha256": digest_bytes(calibration_result.read_bytes()),
        "calibration_checks": calibration_checks,
        "target_95_half_width": thresholds["target_95_half_width"],
        "paired_group_difference": contrast["estimate"],
        "paired_group_sd": sd,
        "variance_floor_sd": 0.25,
        "estimated_required_concept_groups": required,
        "normal_approximation_only": True,
        "repeated_turns_are_independent_groups": False,
        "terminal_outcomes": summary["terminal"],
        "planned_outcomes": summary["planned"],
        "rated_teaching_arms_complete": ratings_complete,
        "independent_judge_calibration_passed": calibrated,
        "ready_for_reserved": ready,
        "interpretation": "This estimates precision for a paired concept-level difference, not power for real student learning gain. Quality/latency thresholds remain attached and independently frozen.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical(result))
    return result


def calibration_pass(observed: dict, criteria: dict | None) -> tuple[bool, dict]:
    """Compare post-run observations with thresholds frozen before pilot calls."""
    variants = ("source_order", "length_neutral", "wording_frame", "untrusted_instruction")
    if (
        observed.get("schema") != PROTOCOL_VERSION + "_judge_calibration"
        or not isinstance(criteria, dict)
        or type(criteria.get("min_evaluable_pairs")) is not int
        or criteria["min_evaluable_pairs"] < 1
    ):
        raise ValueError("Versioned judge calibration and prespecified criteria are required")
    checks = {}
    for variant in variants:
        threshold = criteria.get("minimum_agreement", {}).get(variant)
        if type(threshold) not in (float, int) or not 0 <= threshold <= 1:
            raise ValueError("Each judge calibration variant needs a fixed threshold")
        row = observed.get("comparisons", {}).get(variant) or {}
        pairs = row.get("evaluable_pairs")
        rate = row.get("agreement_rate")
        passed = (
            type(pairs) is int
            and pairs >= criteria["min_evaluable_pairs"]
            and type(rate) in (float, int)
            and rate >= threshold
        )
        checks[variant] = {
            "evaluable_pairs": pairs,
            "observed_agreement": rate,
            "threshold": threshold,
            "passed": passed,
        }
    return all(row["passed"] for row in checks.values()), checks
