"""Blindness, strict human import and finite model-judge software tests."""

import csv
import json
from copy import deepcopy

import pytest

from evaluation.enhancement import memory_review as review
from evaluation.enhancement.protocol import freeze
from generation.types import ModelConfig, ProviderResult


def item():
    return {
        "review_id": "blind_1",
        "learner_events": [{"action": "statement", "text": "I prefer examples."}],
        "current_question": "Compare cells.",
        "use_profile": True,
        "saved_settings": {"level": "intermediate"},
        "context_delivered_to_generator": "Examples first.",
        "published_response": {"response_type": "answer", "answer_text": "One example."},
        "execution_status": "answer_available",
    }


def scores():
    return {
        **{key: 1 for key in review.SCORES},
        "inappropriate_memory_used": 0,
        "reason": "Authored transport fixture only.",
    }


def test_blinded_inputs_exclude_condition_expected_state_and_online_checker():
    case = {
        "steps": [{"action": "statement", "text": "I prefer examples."}],
        "expect": {"context": "present"},
    }
    result = {
        "condition": "structured_memory",
        "question": "Compare cells.",
        "profile": {"use_profile": True, "profile": {"level": "intermediate"}},
        "state": {"context_text": "Examples first."},
        "state_checks": [{"passed": True}],
        "outcome": {
            "response": {"response_type": "answer", "answer_text": "An example."},
            "checks": [{"supported": True}],
        },
    }
    blind = review.blinded_item(case, result, "blind_1")
    assert blind["execution_status"] == "answer_available"
    for forbidden in ("structured_memory", "state_checks", '"expect"', '"checks"', '"condition"'):
        assert forbidden not in json.dumps(blind)
    result["outcome"]["error"] = {"code": "SEMANTIC_CHECK_FAILED"}
    blind = review.blinded_item(case, result, "blind_1")
    assert (
        blind["published_response"] is None and blind["execution_status"] == "no_published_answer"
    )


class Transport:
    def __init__(self, rows):
        self.rows, self.calls = iter(rows), []

    def generate(self, messages, **kwargs):
        self.calls.append(deepcopy(messages))
        return next(self.rows)


def test_separate_model_judge_hides_identity_and_records_its_own_purpose():
    transport = Transport([ProviderResult(raw_text=json.dumps(scores()))])
    events = []
    result = review.judge_one(item(), ModelConfig(), None, events.append, adapter=transport)
    assert result["state"] == "judged" and result["budget"]["consumed_calls"] == 1
    assert "blind_1" not in json.dumps(transport.calls)
    assert all(event["purpose"] == "memory_use_judge" for event in events)


def test_two_invalid_judgments_remain_failed():
    transport = Transport([ProviderResult(raw_text="bad"), ProviderResult(raw_text="{}")])
    result = review.judge_one(item(), ModelConfig(), None, lambda event: None, adapter=transport)
    assert result["state"] == "judge_failed" and result["judgment"] is None
    assert result["budget"]["consumed_calls"] == len(transport.calls) == 2


def test_late_valid_judgment_is_never_published(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(review.time, "monotonic", lambda: clock[0])

    class Late:
        def generate(self, *args, **kwargs):
            clock[0] = 91.0
            return ProviderResult(raw_text=json.dumps(scores()))

    result = review.judge_one(item(), ModelConfig(), None, lambda event: None, adapter=Late())
    assert result["judgment"] is None and result["budget"]["consumed_calls"] == 1
    assert result["error_code"] == "MEMORY_JUDGE_DEADLINE_EXCEEDED"


def forms(tmp_path):
    freeze(
        tmp_path / "coordinator-only-key.json",
        {"items": [{"review_id": "blind_1"}, {"review_id": "blind_2"}]},
    )
    freeze(tmp_path / "blinded-items.json", {"items": [item(), {**item(), "review_id": "blind_2"}]})
    return [
        {
            "review_id": identity,
            "rubric_version": review.VERSION,
            **{key: "" for key in review.FIELDS if key not in {"review_id", "rubric_version"}},
        }
        for identity in ("blind_1", "blind_2")
    ]


def write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=review.FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def complete(row, reviewer):
    return {
        **row,
        **{key: "1" for key in review.SCORES},
        "reviewer_id": reviewer,
        "reason": "Explicit test fixture; no human review.",
        "completed_at": "2026-01-01T00:00:00+00:00",
    }


def test_blank_human_forms_cannot_be_imported_as_ratings(tmp_path):
    rows = forms(tmp_path)
    path = tmp_path / "blank.csv"
    write_csv(path, rows)
    with pytest.raises(ValueError, match="No actual"):
        review.import_review(tmp_path, path, "fixture-reviewer")


@pytest.mark.parametrize(
    "change", ["duplicate", "missing", "partial", "rubric", "future", "reviewer"]
)
def test_import_rejects_false_identity_partial_or_unverifiable_ratings(tmp_path, change):
    rows = forms(tmp_path)
    rows[0] = complete(rows[0], "fixture-reviewer")
    if change == "duplicate":
        rows[1] = rows[0]
    if change == "missing":
        rows.pop()
    if change == "partial":
        rows[0][review.SCORES[0]] = ""
    if change == "rubric":
        rows[0]["rubric_version"] = "wrong"
    if change == "future":
        rows[0]["completed_at"] = "2999-01-01T00:00:00Z"
    if change == "reviewer":
        rows[0]["reviewer_id"] = "other"
    path = tmp_path / "ratings.csv"
    write_csv(path, rows)
    with pytest.raises(ValueError):
        review.import_review(tmp_path, path, "fixture-reviewer")


def test_import_preserves_two_distinct_reviewers_and_prevents_third(tmp_path):
    base = forms(tmp_path)
    for reviewer in ("fixture-A", "fixture-B"):
        rows = [complete(base[0], reviewer), base[1]]
        path = tmp_path / (reviewer + ".csv")
        write_csv(path, rows)
        assert review.import_review(tmp_path, path, reviewer)["ratings_imported"] == 1
    assert len(list((tmp_path / "imports").glob("*.json"))) == 2
    assert len(list((tmp_path / "imports").glob("*.csv"))) == 2
    path = tmp_path / "third.csv"
    write_csv(path, [complete(base[0], "fixture-C"), base[1]])
    with pytest.raises(ValueError, match="Two independent"):
        review.import_review(tmp_path, path, "fixture-C")


def test_model_judging_needs_explicit_live_flag_before_any_file_or_secret_read(tmp_path):
    with pytest.raises(ValueError, match="allow-live"):
        review.judging(tmp_path, allow_live=False)


def test_changed_source_invalidates_public_scores_but_retains_private_candidate():
    sealed = review.seal_judgment({"state": "judged", "judgment": scores()}, False)
    assert sealed["judgment"] is None and sealed["invalidated_candidate_judgment"] == scores()
    public = review.public_result(sealed)
    assert public["scores"] is None and "invalidated_candidate_judgment" not in public
    assert "reason" not in json.dumps(public)


def test_empty_forms_have_zero_humans_and_no_invented_agreement(tmp_path):
    forms(tmp_path)
    result = review.agreement(tmp_path)
    assert result["actual_reviewers"] == result["actual_ratings"] == 0
    assert all(
        value["agreement"] is None and value["cohen_kappa"] is None
        for value in result["dimensions"].values()
    )
    assert result["automatic_to_human"] == []


def test_actual_two_reviewer_disagreement_is_retained_separately(tmp_path):
    base = forms(tmp_path)
    for reviewer in ("fixture-A", "fixture-B"):
        row = complete(base[0], reviewer)
        row[review.SCORES[0]] = "0" if reviewer == "fixture-B" else "1"
        path = tmp_path / (reviewer + ".csv")
        write_csv(path, [row, base[1]])
        review.import_review(tmp_path, path, reviewer)
    freeze(tmp_path / "judgments" / "blind_1.json", {"judgment": scores()})
    result = review.agreement(tmp_path)
    assert result["actual_reviewers"] == 2 and result["actual_ratings"] == 2
    assert result["dimensions"][review.SCORES[0]]["agreement"] == 0
    assert result["disagreements"] == [{"review_id": "blind_1", "dimensions": [review.SCORES[0]]}]
    assert len(result["automatic_to_human"]) == 2
