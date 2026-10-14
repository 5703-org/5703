"""Scheduled denominators and group-level sample planning stay explicit."""

from evaluation.week09.study import distribution, sample_decision, summarize
from evaluation.week09.review import write


def test_generation_latency_quantile_includes_actual_failures():
    assert distribution([])["p95_ms"] is None
    assert distribution([100, 100, 300])["p95_ms"] == 280


def test_missing_outcomes_are_not_removed_from_schedule(tmp_path):
    schedule = [
        {"id": "one", "arm": "A", "family": "group-one"},
        {"id": "two", "arm": "A", "family": "group-two"},
    ]
    write(
        tmp_path / "frozen-study.json",
        {"split": "pilot", "schedule": schedule, "planned_outcomes": 2},
    )
    write(
        tmp_path / "outcomes/one.json",
        {
            "schedule": schedule[0],
            "outcome": {"response": {"explanation": "Example"}, "error": None},
            "elapsed_ms": 100,
            "source_unchanged": True,
        },
    )
    result = summarize(tmp_path)
    assert result["planned"] == 2
    assert result["unstarted"] == 1
    assert result["arms"]["A"]["published"] == 1
    assert result["semantic_correctness_rate"] is None


def test_zero_pilot_variation_does_not_claim_zero_required_groups(tmp_path):
    write(
        tmp_path / "summary.json",
        {
            "split": "pilot",
            "unstarted": 0,
            "comparisons": {"D_minus_A": {"difference": 0, "paired_sd": 0}},
        },
    )
    result = sample_decision(tmp_path, tmp_path / "decision.json")
    assert result["estimated_required_groups"] >= 16
    assert result["quality_endpoint_power"] is None
    assert result["repetitions_replace_independent_groups"] is False
