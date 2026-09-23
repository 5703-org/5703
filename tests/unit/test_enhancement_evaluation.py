"""Scientific isolation, all-planned metrics, privacy and actual-human imports."""

import csv
from datetime import datetime, timezone
import json

import pytest

from evaluation.enhancement.analysis import analyse, cost_estimate, paired_interval
from evaluation.enhancement.catalogue import tasks
from evaluation.enhancement.judge import judge_input
from evaluation.enhancement.protocol import (
    freeze,
    generation_task,
    hint_schedule,
    validate_tasks,
    verify_frozen,
)
from evaluation.enhancement.review import FIELDS, SCORES, agreement, import_review


def test_frozen_input_rejects_mutation_and_keeps_private_labels_out(tmp_path):
    rows = tasks()
    validate_tasks(rows, split="development")
    scheduled = hint_schedule(rows)
    assert len(scheduled) == 180
    assert len({r["id"] for r in scheduled}) == 180
    assert set(generation_task(rows[0])) == {"id", "question", "turns"}
    value = freeze(tmp_path / "frozen.json", {"items": rows})
    assert verify_frozen(value)["items"] == rows
    original = (tmp_path / "frozen.json").read_bytes()
    with pytest.raises(ValueError):
        freeze(tmp_path / "frozen.json", {"items": []})
    assert (tmp_path / "frozen.json").read_bytes() == original
    value["items"][0]["critical_answer"] = "tampered"
    with pytest.raises(ValueError):
        verify_frozen(value)


def test_pairing_is_by_task_and_missing_conditions_are_rejected():
    result = paired_interval({"a": 1.0, "b": 0.0}, {"a": 0.0, "b": 0.0}, samples=100)
    assert result["difference"] == 0.5
    assert result["paired_tasks"] == 2
    with pytest.raises(ValueError):
        paired_interval({"a": 1.0}, {"b": 1.0})


def test_failed_and_missing_requests_remain_in_denominator(tmp_path):
    manifest = {
        "planned": [
            {"id": "one", "task_id": "a", "condition": "T2", "turn": 1},
            {"id": "two", "task_id": "a", "condition": "T2", "turn": 2},
        ],
        "model_config": {"model": "mock", "base_url": None},
        "experiment": "hints",
        "split": "development",
        "created_at": "2026-09-20T00:00:00+00:00",
    }
    freeze(tmp_path / "run-manifest.json", manifest)
    freeze(
        tmp_path / "results" / "one.json",
        {"outcome": {"error": {"code": "TIMEOUT"}}, "exposure": None, "wall_seconds": 60},
    )
    summary = analyse(tmp_path)
    metric = summary["metrics"]["T2"]
    assert metric["planned"] == 2 and metric["completed"] == 1
    assert metric["valid_hint_rate_all_planned"] == 0
    assert metric["judge_state"] if "judge_state" in metric else metric["judged"] == 0
    assert summary["human_evaluation"]["completed_ratings"] == 0


def test_offline_judge_sees_actual_exposure_not_condition_or_online_score():
    task = tasks()[0]
    result = {
        "turn": 1,
        "experiment": "hints",
        "condition": "T2",
        "outcome": {"evidence": [], "checks": [{"accepted": True}], "response": {"citations": []}},
        "exposure": {"response": "hint"},
        "prior_exposure": [{"source": "already revealed"}],
    }
    payload = judge_input(task, result)
    assert payload["protected_reference_answer"] == task["critical_answer"]
    assert payload["prior_exposure"] == result["prior_exposure"]
    assert "checks" not in payload and "condition" not in payload


def test_cost_requires_measured_cache_split_and_approved_endpoint():
    kwargs = {"model": "deepseek-flash", "base_url": "https://api.deepseek.com/v1"}
    assert cost_estimate({"input_tokens": 100}, "2026-09-20T00:00:00Z", **kwargs) is None
    usage = {"cache_hit_input_tokens": 100, "cache_miss_input_tokens": 200, "output_tokens": 50}
    assert cost_estimate(usage, "2026-09-20T00:00:00Z", **kwargs) == pytest.approx(0.000402)
    assert cost_estimate(usage, "2026-09-21T02:00:00Z", **kwargs) == pytest.approx(0.000804)


def write_ratings(path, row):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerow(row)


def test_human_import_rejects_blank_or_invalid_scores_and_preserves_independence(tmp_path):
    from evaluation.enhancement.protocol import RUBRIC_VERSION

    freeze(tmp_path / "coordinator-only-condition-key.json", {"items": [{"review_id": "a"}]})
    ratings = tmp_path / "ratings.csv"
    write_ratings(ratings, {"review_id": "a", "rubric_version": RUBRIC_VERSION})
    with pytest.raises(ValueError, match="No actual"):
        import_review(tmp_path, ratings, "alice")
    row = {
        "review_id": "a",
        "reviewer_id": "alice",
        "rubric_version": RUBRIC_VERSION,
        **dict.fromkeys(SCORES, "1"),
        "reason": "Unit test fixture rating, not research data",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    row["supported"] = "2"
    write_ratings(ratings, row)
    with pytest.raises(ValueError, match="binary"):
        import_review(tmp_path, ratings, "alice")
    row["supported"] = "1"
    write_ratings(ratings, row)
    imported = import_review(tmp_path, ratings, "alice")
    original = json.loads(open(imported["artifact"], encoding="utf-8").read())
    row.update(reviewer_id="bob", supported="0")
    write_ratings(ratings, row)
    import_review(tmp_path, ratings, "bob")
    summary = agreement(tmp_path)
    assert summary["actual_reviewers"] == 2 and summary["actual_ratings"] == 2
    assert summary["agreement"]["supported"]["agreement"] == 0
    assert len(summary["disagreements"]) == 1
    assert json.loads(open(imported["artifact"], encoding="utf-8").read()) == original
