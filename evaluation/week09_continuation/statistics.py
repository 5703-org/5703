"""Paired, concept-clustered estimates for repeated study observations."""

from __future__ import annotations

from collections import defaultdict
import math
import random
import statistics


def quantile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    if not 0 <= fraction <= 1:
        raise ValueError("Quantile fraction is outside [0, 1]")
    ordered = sorted(values)
    if any(not math.isfinite(item) for item in ordered):
        raise ValueError("Quantiles require finite observations")
    point = (len(ordered) - 1) * fraction
    below = math.floor(point)
    above = math.ceil(point)
    return ordered[below] + (ordered[above] - ordered[below]) * (point - below)


def distribution(values: list[float]) -> dict:
    return {"n": len(values), "p50": quantile(values, 0.5), "p95": quantile(values, 0.95)}


def clustered_contrast(
    observations: list[dict],
    weights: dict[str, float],
    *,
    seed: int = 57030930,
    draws: int = 4000,
) -> dict:
    """Average repeats within a concept/arm before paired cluster resampling."""
    if draws < 100 or not weights:
        raise ValueError("Declare at least 100 bootstrap draws and a contrast")
    grouped: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for item in observations:
        value = item.get("value")
        if value is None:
            continue
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError("Scored contrast values must be finite numbers")
        grouped[item["concept_group"]][item["arm"]].append(float(value))
    eligible, incomplete = [], []
    for group, arms in sorted(grouped.items()):
        if set(weights) <= set(arms):
            eligible.append(
                sum(weight * statistics.mean(arms[arm]) for arm, weight in weights.items())
            )
        else:
            incomplete.append(group)
    if not eligible:
        return {
            "estimate": None,
            "cluster_bootstrap_95": None,
            "paired_concept_groups": 0,
            "incomplete_groups": incomplete,
            "repeat_handling": "averaged within concept and arm",
        }
    rng = random.Random(seed)
    boot = sorted(statistics.mean(rng.choices(eligible, k=len(eligible))) for _ in range(draws))
    return {
        "estimate": statistics.mean(eligible),
        "cluster_bootstrap_95": [quantile(boot, 0.025), quantile(boot, 0.975)],
        "paired_concept_groups": len(eligible),
        "incomplete_groups": incomplete,
        "paired_sd": statistics.stdev(eligible) if len(eligible) > 1 else None,
        "repeat_handling": "averaged within concept and arm",
        "bootstrap_draws": draws,
        "seed": seed,
    }


def teaching_contrasts(observations: list[dict]) -> dict:
    factors = {
        "B_minus_A": {"B": 1.0, "A": -1.0},
        "C_minus_A": {"C": 1.0, "A": -1.0},
        "D_minus_A": {"D": 1.0, "A": -1.0},
        "interaction": {"D": 1.0, "B": -1.0, "C": -1.0, "A": 1.0},
    }
    return {name: clustered_contrast(observations, weights) for name, weights in factors.items()}


def holm_adjust(p_values: dict[str, float]) -> dict[str, float]:
    """Family-wise adjustment for explicitly secondary tests only."""
    for value in p_values.values():
        if not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("Secondary p-values must be in [0, 1]")
    ordered = sorted(p_values, key=p_values.get)
    adjusted = {}
    running = 0.0
    for index, name in enumerate(ordered):
        running = max(running, min(1.0, p_values[name] * (len(ordered) - index)))
        adjusted[name] = running
    return adjusted
