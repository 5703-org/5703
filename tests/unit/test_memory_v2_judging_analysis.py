"""Synthetic protocol fixtures only; no study outcomes, models or databases."""

from copy import deepcopy
from pathlib import Path
import json

import pytest

from evaluation.enhancement.protocol import digest, freeze
from evaluation.memory_v2 import analysis, judging
from tests.authored_evaluation import question_cases as tasks
from tests.authored_evaluation import memory_trajectories as trajectories
from generation.types import ModelConfig, ProviderResult


def result(study="B", arm="B2", identity="fixture-B2-1", status="answer"):
    response = {
        "response_type": status,
        "answer_text": "Authored answer. [ev_001]",
        "short_answer": None,
        "citations": ["ev_001"],
        "follow_up_questions": [],
    }
    return {
        "id": identity,
        "study": study,
        "case_id": "fixture",
        "family": "authored_family",
        "arm": arm,
        "turn": 1,
        "status": status,
        "outcome": {
            "response": response,
            "error": None,
            "evidence": [
                {
                    "evidence_id": "ev_001",
                    "source_title": "Authored fixture",
                    "section": "One",
                    "pages": [1],
                    "text": "Authored evidence.",
                }
            ],
            "checks": [{"reason": "HIDDEN_ONLINE_VERDICT"}],
            "attempts": [],
        },
        "exposure": {
            "response": response,
            "citation_views": [
                {
                    "evidence_id": "ev_001",
                    "title": "Authored title",
                    "preview": "Protected source text.",
                    "claim_ids": ["HIDDEN_INTERNAL_CLAIM"],
                }
            ],
        },
        "prior_exposure": [],
    }


def payload(study="B"):
    return judging.judge_input(tasks()[0], result(study))


def scores(data):
    return {
        **{k: 1 if k in data["applicable_fields"] else None for k in judging.SCORE_FIELDS},
        "explanation": "Authored test verdict, not a quality measurement.",
        "failure_quote": None,
    }


def config():
    return ModelConfig(provider="mock", max_tokens=1600, window_tokens=100000)


class Adapter:
    def __init__(self, values):
        self.values = iter(values)
        self.calls = []

    def generate(self, messages, **kwargs):
        self.calls.append((deepcopy(messages), kwargs))
        value = next(self.values)
        if callable(value):
            value = value()
        if isinstance(value, Exception):
            raise value
        if isinstance(value, ProviderResult):
            return value
        return ProviderResult(
            provider="authored_fixture",
            model="scripted",
            raw_text=json.dumps(value),
            request_submitted=False,
        )


def test_judge_payload_hides_arm_online_checks_and_private_attribution():
    data = payload()
    serialized = json.dumps(data)
    assert "B2" not in serialized and "HIDDEN_ONLINE_VERDICT" not in serialized
    assert "HIDDEN_INTERNAL_CLAIM" not in serialized
    assert (
        data["current_exposure"]["citation_views"][0]["ordinary_source_text"]
        == "Protected source text."
    )
    assert data["reference_answer"] == tasks()[0]["critical_answer"]


def test_direct_answer_never_receives_hint_disclosure_rules():
    data = payload()
    assert data["mode"] == "direct" and "Complete final answer" in data["help_allowance"]
    assert not judging.HINT_FIELDS & set(data["applicable_fields"])
    assert not judging.MEMORY_FIELDS & set(data["applicable_fields"])


def test_a_correctness_separate_from_sources_and_citation_null_is_explicit():
    item = result("A", "A0")
    item["outcome"]["response"]["citations"] = []
    data = judging.judge_input(tasks()[0], item)
    value = judging.validate_judgment(scores(data), data)
    assert value["factual_correct"] == 1 and value["source_support"] is None
    assert value["citation_mapping"] is None
    assert analysis.composite("A", value, True)


def test_t_all_actual_prior_and_current_surfaces_are_retained():
    item = result("T", "T4")
    item["prior_exposure"] = [deepcopy(item["exposure"])]
    data = judging.judge_input(tasks()[0], item)
    assert judging.HINT_FIELDS <= set(data["applicable_fields"])
    assert data["prior_exposure"][0] == data["current_exposure"]
    assert data["help_allowance"] == tasks()[0]["help_allowances"][0]


def test_m_expectations_do_not_expose_selected_state_or_future_history():
    trajectory = trajectories()[0]
    item = result("M", "M4")
    item["memory_state_trace"] = {"entries": ["HIDDEN_ACTUAL_SELECTION"]}
    task = next(t for t in tasks() if t["id"] == trajectory["probes"][0]["question_id"])
    data = judging.judge_input(task, item, trajectory=trajectory)
    encoded = json.dumps(data)
    assert "HIDDEN_ACTUAL_SELECTION" not in encoded
    assert trajectory["statements"][0] in encoded
    assert trajectory["statements"][1] not in encoded
    assert judging.MEMORY_FIELDS <= set(data["applicable_fields"])


def test_inapplicable_positive_scores_are_rejected_not_counted():
    data = payload()
    value = scores(data)
    value["allowed_disclosure"] = 1
    with pytest.raises(ValueError, match="APPLICABILITY"):
        judging.validate_judgment(value, data)
    value = scores(data)
    value["factual_correct"] = None
    with pytest.raises(ValueError):
        judging.validate_judgment(value, data)


def test_one_schema_repair_shares_two_call_budget(tmp_path):
    data = payload()
    adapter = Adapter([{}, scores(data)])
    out = judging.judge_one(data, config(), None, tmp_path / "events.jsonl", adapter=adapter)
    assert out["state"] == "judged" and out["budget"]["consumed_calls"] == 2
    assert len(out["attempts"]) == 2 and len(adapter.calls) == 2
    assert adapter.calls[0][0][1] == adapter.calls[1][0][1]


def test_no_third_call_after_two_invalid_contracts(tmp_path):
    adapter = Adapter([{}, {}])
    out = judging.judge_one(payload(), config(), None, tmp_path / "events.jsonl", adapter=adapter)
    assert out["state"] == "judge_failed" and out["judgment"] is None
    assert out["budget"]["consumed_calls"] == 2 and len(adapter.calls) == 2


def test_provider_denial_is_retained_without_automatic_retry(tmp_path):
    adapter = Adapter(
        [
            ProviderResult(
                error={"code": "PROVIDER_HTTP_ERROR"},
                diagnostic={"http_status": 401},
                request_submitted=True,
            )
        ]
    )
    out = judging.judge_one(payload(), config(), None, tmp_path / "events.jsonl", adapter=adapter)
    assert out["state"] == "judge_failed" and len(adapter.calls) == 1
    assert out["attempts"][0]["diagnostic"]["http_status"] == 401


def test_late_valid_judgment_is_never_published(tmp_path):
    timer = [0.0]
    data = payload()

    def late():
        timer[0] = 91
        return scores(data)

    out = judging.judge_one(
        data,
        config(),
        None,
        tmp_path / "events.jsonl",
        adapter=Adapter([late]),
        clock=lambda: timer[0],
    )
    assert out["judgment"] is None and out["error"]["code"] == "JUDGE_DEADLINE_EXCEEDED"
    assert len(out["attempts"]) == 1


def test_preprocessing_is_charged_before_any_call(tmp_path, monkeypatch):
    timer = [0.0]

    def count(*args):
        timer[0] = 91
        return 1

    monkeypatch.setattr(judging.TokenCounter, "request_input", count)
    adapter = Adapter([])
    out = judging.judge_one(
        payload(),
        config(),
        None,
        tmp_path / "events.jsonl",
        adapter=adapter,
        clock=lambda: timer[0],
    )
    assert not adapter.calls and out["budget"]["consumed_calls"] == 0
    assert out["error"]["code"] == "JUDGE_DEADLINE_EXCEEDED"


def test_exception_keeps_durable_started_attempt(tmp_path):
    out = judging.judge_one(
        payload(),
        config(),
        None,
        tmp_path / "events.jsonl",
        adapter=Adapter([RuntimeError("private transport details")]),
    )
    assert out["attempts"][0]["error"]["code"] == "UNCERTAIN_EXTERNAL_COMPLETION"
    assert "private transport" not in json.dumps(out)


def fixture_plan(tmp_path, rows):
    planned = []
    for i, item in enumerate(rows):
        p = tmp_path / "generation" / f"{i}.json"
        freeze(p, item)
        data = (
            judging.judge_input(tasks()[0], item)
            if (item.get("outcome") or {}).get("response")
            else None
        )
        planned.append(
            {
                **{k: item[k] for k in ("id", "study", "case_id", "family", "arm", "turn")},
                "result_path": str(p),
                "result_sha256": digest(item),
                "payload": data,
                "payload_sha256": digest(data) if data else None,
            }
        )
    plan = {
        "rows": planned,
        "source_hashes": {"fixture": "unchanged"},
        "model_config": config().to_dict(),
    }
    freeze(tmp_path / "judge-plan.json", plan)
    return plan


def save_rating(tmp_path, plan, row, value=None, state="judged"):
    freeze(
        tmp_path / "judgments" / (row["id"] + ".json"),
        {
            "id": row["id"],
            "plan_sha256": digest(plan),
            "result_sha256": row["result_sha256"],
            "payload_sha256": row["payload_sha256"],
            "state": state,
            "judgment": value,
            "attempts": [],
        },
    )


def test_analysis_keeps_failures_missing_ratings_and_all_planned_denominator(tmp_path):
    good = result()
    failed = result(identity="fixture-B2-2")
    failed.update(
        turn=2, status="failed", outcome={"error": {"code": "PROVIDER_TIMEOUT"}}, exposure=None
    )
    unjudged = result(identity="fixture-B2-3")
    unjudged["turn"] = 3
    plan = fixture_plan(tmp_path, [good, failed, unjudged])
    save_rating(tmp_path, plan, plan["rows"][0], scores(plan["rows"][0]["payload"]))
    report = analysis.analyse(tmp_path)
    arm = report["arms"]["B2"]
    assert arm["planned"] == 3 and arm["answered"] == 2 and arm["judged_answers"] == 1
    assert arm["end_to_end_rate_all_planned"] == 1 / 3
    assert arm["dimensions_among_judged_answers"]["factual_correct"]["rate"] == 1
    assert report["rows"][1]["judgment"] is None


def test_analysis_rejects_rating_for_another_result_hash(tmp_path):
    plan = fixture_plan(tmp_path, [result()])
    row = {**plan["rows"][0], "result_sha256": "wrong"}
    save_rating(tmp_path, plan, row, scores(row["payload"]))
    with pytest.raises(ValueError, match="not bound"):
        analysis.analyse(tmp_path)


def test_bootstrap_resamples_whole_paired_clusters_and_is_repeatable():
    left = {"family1": [1, 1, 0], "family2": [0, 0, 0]}
    right = {"family1": [0, 0, 0], "family2": [1, 1, 1]}
    report = analysis.paired_cluster(left, right)
    assert report == analysis.paired_cluster(left, right)
    assert report["paired_clusters"] == 2 and report["paired_requests"] == 6
    assert report["difference"] == pytest.approx(-1 / 6)
    assert report["bootstrap_samples"] == 10000
    with pytest.raises(ValueError):
        analysis.paired_cluster(left, {"family1": [0, 0, 0]})


def test_summary_missing_usage_stays_unknown(tmp_path):
    item = result()
    item["outcome"]["attempts"] = [{"usage": {"input_tokens": 10}}, {"usage": {}}]
    fixture_plan(tmp_path, [item])
    report = analysis.analyse(tmp_path)
    assert report["usage"]["input_tokens"]["known_sum"] == 10
    assert report["usage"]["input_tokens"]["complete_total"] is None
    assert all(a["cost"] is None for a in report["attempts"])


def test_partial_selection_labels_never_manufacture_precision():
    item = result("M", "M4")
    item["memory_expected"] = {"selected_fields": ["analogies"], "excluded_fields": ["difficulty"]}
    item["memory_state_trace"] = {
        "memory_context": {
            "entries": [
                {"field_key": "analogies", "id": "m", "version": 1, "source_message_id": "s"},
                {"field_key": "unlabelled"},
            ]
        }
    }
    stats = analysis.selected_state_metrics(item)
    assert stats["required_recall"] == 1 and stats["precision"] is None
    assert stats["excluded_selected_count"] == 0


def test_uncertain_judge_reservation_is_not_replayed(tmp_path, monkeypatch):
    plan = fixture_plan(tmp_path, [result()])
    row = plan["rows"][0]
    freeze(tmp_path / "judge-reservations" / (row["id"] + ".json"), {"authored": True})
    monkeypatch.setattr(judging, "source_snapshot", lambda: plan["source_hashes"])
    monkeypatch.setattr(judging, "resolve_frozen_credentials", lambda cfg: None)
    monkeypatch.setattr(
        judging, "judge_one", lambda *a, **kw: pytest.fail("Uncertain request replayed")
    )
    judging.run(tmp_path, allow_live=True)
    saved = judging.load(tmp_path / "judgments" / (row["id"] + ".json"))
    assert saved["state"] == "uncertain_prior_judgment" and saved["judgment"] is None


@pytest.mark.parametrize("arm", ["M0", "M1", "M2"])
def test_legacy_memory_is_not_scored_as_missing_typed_fields(arm):
    item = result("M", arm)
    item["memory_expected"] = {"selected_fields": ["analogy_preference"]}
    item["memory_state_trace"] = {"memory_context": {"entries": [{"content": "Use analogies"}]}}
    value = analysis.selected_state_metrics(item)
    assert value["applicable"] is False and value["required_recall"] is None


def test_a2_without_human_confirmation_retains_planned_but_not_eligible(tmp_path):
    item = result("A", "A2")
    item.update(status="waiting_external", outcome=None, exposure=None)
    fixture_plan(tmp_path, [item])
    arm = analysis.analyse(tmp_path)["arms"]["A2"]
    assert arm["planned"] == arm["waiting_external"] == 1
    assert arm["eligible"] == arm["attempted"] == arm["delivered"] == 0
    assert arm["end_to_end_rate_planned_eligible"] is None
    assert arm["end_to_end_rate_all_planned"] == 0


def test_resumed_auth_failure_halts_remaining_rows_without_replay(tmp_path, monkeypatch):
    plan = fixture_plan(tmp_path, [result(), result(identity="fixture-B2-2")])
    row = plan["rows"][0]
    freeze(
        tmp_path / "judgments" / (row["id"] + ".json"),
        {
            "id": row["id"],
            "plan_sha256": digest(plan),
            "result_sha256": row["result_sha256"],
            "payload_sha256": row["payload_sha256"],
            "state": "judge_failed",
            "judgment": None,
            "attempts": [
                {"diagnostic": {"http_status": 401}, "error": {"code": "PROVIDER_HTTP_ERROR"}}
            ],
            "error": {"code": "PROVIDER_HTTP_ERROR"},
        },
    )
    monkeypatch.setattr(judging, "source_snapshot", lambda: plan["source_hashes"])
    monkeypatch.setattr(judging, "resolve_frozen_credentials", lambda cfg: None)
    monkeypatch.setattr(judging, "judge_one", lambda *a, **kw: pytest.fail("Denial replayed"))
    judging.run(tmp_path, allow_live=True)
    saved = judging.load(tmp_path / "judgments" / "fixture-B2-2.json")
    assert saved["state"] == "not_run" and saved["attempts"] == []
    assert saved["judgment"] is None


def test_source_drift_cannot_publish_a_positive_candidate_rating(tmp_path, monkeypatch):
    plan = fixture_plan(tmp_path, [result()])
    state = {"hash": plan["source_hashes"]}
    monkeypatch.setattr(judging, "source_snapshot", lambda: state["hash"])
    monkeypatch.setattr(judging, "resolve_frozen_credentials", lambda cfg: None)

    def candidate(*args):
        state["hash"] = {"fixture": "changed"}
        return {"state": "judged", "judgment": scores(plan["rows"][0]["payload"]), "attempts": []}

    monkeypatch.setattr(judging, "judge_one", candidate)
    judging.run(tmp_path, allow_live=True)
    saved = judging.load(tmp_path / "judgments" / (plan["rows"][0]["id"] + ".json"))
    assert saved["state"] == "source_drift" and saved["judgment"] is None
    report = analysis.analyse(tmp_path)
    assert report["arms"]["B2"]["judged"] == 0
    assert report["arms"]["B2"]["end_to_end_successes"] == 0


def authored_source(tmp_path):
    tasks = [
        {
            "id": f"synthetic{i}",
            "family": f"authored{i}",
            "source_requirement": {"book": f"authored_book_{i // 6}"},
            "teaching_task": i < 12,
            "question": "Authored offline fixture?",
            "critical_answer": "Authored reference.",
            "turns": ["hint"] * 3,
            "help_allowances": ["Authored allowance"] * 3,
        }
        for i in range(24)
    ]
    trajectories = [{"id": f"synthetic_memory{i}"} for i in range(12)]
    source, run = tmp_path / "source", tmp_path / "run"
    manifest = {
        "tasks_sha256": digest(tasks),
        "trajectories_sha256": digest(trajectories),
        "schedule": judging.schedule(tasks, trajectories),
        "checkpoint": {
            "model_config": config().to_dict(),
            "memory_extraction_sha256": digest([]),
            "memory_gating_sha256": digest([]),
        },
    }
    freeze(source / "study.json", manifest)
    freeze(source / "private-tasks.json", {"tasks": tasks})
    freeze(
        source / "private-trajectories.json",
        {"trajectories": trajectories, "extraction_cases": [], "gating_pairs": []},
    )
    freeze(run / "run-manifest.json", {"study_hash": digest(manifest)})
    return source, run, manifest


def test_prepare_retains_all_missing_scheduled_rows_with_exact_run_binding(tmp_path, monkeypatch):
    source, run, manifest = authored_source(tmp_path)
    monkeypatch.setattr(judging, "source_snapshot", lambda: {"fixture": "immutable"})
    judging.prepare(source, [run], tmp_path / "judge", config())
    plan = judging.load(tmp_path / "judge" / "judge-plan.json")
    assert len(plan["rows"]) == 552
    assert [r["id"] for r in plan["rows"]] == [r["id"] for r in manifest["schedule"]]
    assert all(r["payload"] is None and r["result_path"] is None for r in plan["rows"])
    assert plan["human_ratings"] == 0


@pytest.mark.parametrize(
    "defect", ["wrong_run", "unscheduled_result", "incomplete_schedule", "memory_label_drift"]
)
def test_prepare_rejects_another_study_or_unplanned_denominator(tmp_path, monkeypatch, defect):
    source, run, manifest = authored_source(tmp_path)
    monkeypatch.setattr(judging, "source_snapshot", lambda: {"fixture": "immutable"})
    if defect == "wrong_run":
        path = run / "run-manifest.json"
        value = {"study_hash": "other_study"}
    elif defect == "unscheduled_result":
        freeze(run / "results" / "unscheduled.json", {"authored": True})
    elif defect == "incomplete_schedule":
        manifest["schedule"] = manifest["schedule"][:-1]
        path, value = source / "study.json", manifest
    else:
        path = source / "private-trajectories.json"
        value = judging.load(path)
        value["extraction_cases"] = [{"authored_label": "changed"}]
    if defect != "unscheduled_result":
        path.write_text(json.dumps({**value, "content_sha256": digest(value)}))
    errors = {
        "wrong_run": "does not belong",
        "unscheduled_result": "Unscheduled",
        "incomplete_schedule": "exact registered schedule",
        "memory_label_drift": "labels differ",
    }
    with pytest.raises(ValueError, match=errors[defect]):
        judging.prepare(source, [run], tmp_path / "judge", config())
    assert not (tmp_path / "judge" / "judge-plan.json").exists()
