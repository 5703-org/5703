"""Read-only real prefix preflight and authored denominator-report regression."""

from types import SimpleNamespace
from copy import deepcopy

import pytest

from scripts.verify import sciq_live_comparison as comparison


def scheduled_runs():
    runs = []
    for split in ("validation", "test"):
        for condition in ("E0", "E1"):
            spec = {"split": split, "condition": condition, "run_id": split + condition}
            rows = []
            for index in range(64):
                passed = condition == "E1" and index == 0
                rows.append(
                    {
                        "item_id": f"item_{index:06}",
                        "question_id": f"sciq:{split}:{index:06}",
                        "status": "completed" if passed else "error",
                        "scores": {
                            "em": int(passed),
                            "token_f1": int(passed),
                            "valid_response": passed,
                            "compact_answer_present": passed,
                        },
                        "receipt": None,
                        "outcome": {"usage": None},
                    }
                )
            runs.append((spec, SimpleNamespace(state={"items": rows})))
    return runs


def test_all_scheduled_failures_stay_in_denominator_and_paired_identity(monkeypatch):
    monkeypatch.setattr(comparison, "sha", lambda _: "authored-hash")
    monkeypatch.setattr(
        comparison, "read_json", lambda _: {"limits": ["authored-limit", "not-yet-executed"]}
    )
    runs = scheduled_runs()
    result = comparison.summarize(runs, {})
    assert result["scheduled_conditions"] == len(result["rows"]) == 256
    assert result["status_counts"] == {"error": 254, "completed": 2}
    assert result["reports"]["validation"]["E1"]["metrics"]["em"] == 1 / 64
    assert result["reports"]["pooled"]["E0"]["metrics"]["em"] == 0
    assert result["reports"]["pooled"]["paired"]["em"]["n_pairs"] == 128
    assert result["reports"]["pooled"]["paired"]["em"]["mcnemar"]["improved"] == 2
    assert result["provider_reported_cost"] is None
    assert result["reports"]["pooled"]["E0"]["usage"]["cost"]["total"] is None
    runs[1][1].state["items"][0]["question_id"] = "different-item"
    with pytest.raises(AssertionError):
        comparison.summarize(runs, {})


def test_unresolved_item_prevents_final_paired_statistics(monkeypatch):
    monkeypatch.setattr(comparison, "sha", lambda _: "authored-hash")
    monkeypatch.setattr(
        comparison, "read_json", lambda _: {"limits": ["authored-limit", "not-yet-executed"]}
    )
    runs = scheduled_runs()
    runs[0][1].state["items"][0]["status"] = "uncertain"
    result = comparison.summarize(runs, {})
    assert result["status"] == "provisional"
    assert len(result["rows"]) == 256
    assert all(value["paired"] is None for value in result["reports"].values())


def test_preflight_binds_exact_schedule_public_plan_and_frozen_runs(monkeypatch):
    schedule = []
    for ordinal in range(64):
        for split_index, split in enumerate(("validation", "test")):
            conditions = ("E0", "E1") if (ordinal + split_index) % 2 == 0 else ("E1", "E0")
            schedule.extend(
                {
                    "split": split,
                    "condition": condition,
                    "source_ordinal": ordinal,
                    "item_id": f"item_{ordinal:06}",
                }
                for condition in conditions
            )
    runs = [
        {"split": split, "condition": condition, "run_id": split + condition}
        for split in ("validation", "test")
        for condition in ("E0", "E1")
    ]
    public = {"schedule_hash": comparison.fingerprint(schedule), "runs": runs, "splits": []}
    private = {**deepcopy(public), "schedule": schedule, "private_splits": []}
    monkeypatch.setattr(comparison, "read_json", lambda _: public)
    monkeypatch.setattr(comparison, "sha", lambda _: "original-public-hash")
    comparison.verify_plan(private)
    changed = deepcopy(private)
    changed["schedule"][0], changed["schedule"][1] = changed["schedule"][1], changed["schedule"][0]
    with pytest.raises(RuntimeError, match="schedule changed"):
        comparison.verify_plan(changed)
    frozen = {"plan_sha256": "original-public-hash", "runs": deepcopy(runs)}
    comparison.verify_plan(private, frozen)
    frozen["runs"][0]["run_id"] = "unexpected-run"
    with pytest.raises(RuntimeError, match="Frozen run identities"):
        comparison.verify_plan(private, frozen)
    frozen["plan_sha256"] = "different-public-hash"
    with pytest.raises(RuntimeError, match="public plan changed"):
        comparison.verify_plan(private, frozen)


def test_mcq_report_uses_separate_accuracy_and_all_scheduled_denominators(monkeypatch):
    monkeypatch.setattr(comparison, "sha", lambda _: "authored-hash")
    monkeypatch.setattr(comparison, "read_json", lambda _: {"limits": ["authored", "planning"]})
    monkeypatch.setattr(comparison, "PROTOCOL", "sciq_mcq")
    monkeypatch.setattr(comparison, "MODE", "benchmark_mcq")
    monkeypatch.setattr(comparison, "METRICS", ("accuracy",))
    runs = scheduled_runs()
    for _, run in runs:
        for item in run.state["items"]:
            item["scores"] = {
                "accuracy": item["scores"]["em"],
                "valid_response": item["status"] == "completed",
            }
    result = comparison.summarize(runs, {})
    assert result["protocol_id"] == "sciq_mcq"
    assert result["status_counts"] == {"error": 254, "completed": 2}
    assert result["reports"]["validation"]["E1"]["metrics"] == {"accuracy": 1 / 64}
    assert set(result["reports"]["pooled"]["paired"]) == {"accuracy"}
    assert result["reports"]["pooled"]["paired"]["accuracy"]["n_pairs"] == 128
    assert result["reports"]["pooled"]["paired"]["accuracy"]["mcnemar"]["improved"] == 2


def test_protocol_selection_separates_artifact_roots_and_rejects_cross_protocol_plan(monkeypatch):
    for name in ("PROTOCOL", "MODE", "METRICS", "PRIVATE", "PUBLIC"):
        monkeypatch.setattr(comparison, name, getattr(comparison, name))
    original = (comparison.PRIVATE, comparison.PUBLIC)
    comparison.select_protocol("sciq_mcq")
    assert (comparison.PRIVATE, comparison.PUBLIC) != original
    assert "live_mcq" in str(comparison.PRIVATE)
    assert "live-mcq" in str(comparison.PUBLIC)
    monkeypatch.setattr(comparison, "read_json", lambda _: {"protocol_id": "sciq_openqa"})
    with pytest.raises(RuntimeError, match="selected execution protocol"):
        comparison.verify_plan({})
    comparison.select_protocol("sciq_openqa")
    assert (comparison.PRIVATE, comparison.PUBLIC) == original
