"""Comparator scheduling, failure denominators and controls without model calls."""

from copy import deepcopy
import json

import pytest

from evaluation.enhancement import memory_study as study
from evaluation.enhancement.protocol import freeze
from generation.types import ModelConfig, ProviderResult
from personalisation.compiler import compile_profile


def case(identity):
    return next(row for row in study.cases() if row["id"] == identity)


def test_complete_schedule_rotates_every_condition_and_preserves_identical_cases():
    rows = study.schedule(study.cases())
    assert len(rows) == len({row["id"] for row in rows}) == 36
    for item in study.cases():
        assert {r["condition"] for r in rows if r["case_id"] == item["id"]} == set(
            study.MEMORY_CONDITIONS
        )
    starts = [rows[i]["condition"] for i in range(0, 36, 3)]
    assert all(starts.count(condition) == 4 for condition in study.MEMORY_CONDITIONS)


def test_profile_only_never_calls_updater_or_replays_history():
    def forbidden(*args):
        pytest.fail("Profile-only condition must never summarize")

    state = study.baseline(case("M03"), "profile_session", None, None, None, updater=forbidden)
    assert state["summary"] is None and state["memory_context"] is None
    assert state["context_text"] == "" and [u["calls"] for u in state["updates"]] == [0, 0]


@pytest.mark.parametrize("identity", ["M06", "M07", "M08", "M09"])
def test_baseline_explicit_controls_remove_context_and_prevent_disabled_updates(identity):
    calls = []

    def updater(previous, statement, *args):
        calls.append(statement)
        return {"summary": "Examples before formulas.", "calls": 1, "error": None, "usage": []}

    state = study.baseline(case(identity), "rolling_summary", None, None, None, updater=updater)
    assert state["summary"] is None and state["context_text"] == ""
    assert len(calls) == 1
    if identity in {"M07", "M08"}:
        assert state["updates"][-1]["calls"] == 0


def test_retained_wrong_memory_and_update_error_are_separate_from_semantic_ratings():
    item = case("M03")
    state = {
        "context_text": "Use equations and analogies.",
        "updates": [{"calls": 1, "error": {"code": "TIMEOUT"}}],
        "superseded_source_absent": False,
    }
    checks = {
        row["name"]: row["passed"]
        for row in study.check_state(
            item, "structured_memory", state, compile_profile(study.PROFILE)
        )
    }
    assert checks["required_literal_screen"] is True
    assert checks["retained_wrong_memory_literal_screen"] is False
    assert checks["superseded_source_absent"] is False
    assert checks["updates_completed_without_error"] is False
    assert not any("human" in name or "supported" in name for name in checks)


class Transport:
    def __init__(self, results):
        self.results, self.calls = iter(results), []

    def generate(self, messages, **kwargs):
        self.calls.append(deepcopy(messages))
        return next(self.results)


def test_real_summary_adapter_path_retains_two_format_failures_without_false_success():
    transport = Transport(
        [ProviderResult(raw_text="invalid"), ProviderResult(raw_text='{"wrong":"field"}')]
    )
    events = []
    result = study.update_summary(
        "Previous summary",
        "I prefer examples.",
        ModelConfig(),
        None,
        events.append,
        adapter=transport,
    )
    assert result["summary"] == "Previous summary"
    assert result["error"]["code"] == "SUMMARY_FORMAT_INVALID"
    assert result["calls"] == len(transport.calls) == 2
    assert len(events) == 4
    assert all("learner_statement" not in json.dumps(event) for event in events)


def test_summary_transport_error_is_terminal_and_never_retried():
    transport = Transport([ProviderResult(error={"code": "NETWORK_ERROR"})])
    result = study.update_summary(
        "Old", "I prefer examples.", ModelConfig(), None, lambda event: None, adapter=transport
    )
    assert result["calls"] == 1 and result["error"]["code"] == "NETWORK_ERROR"


def test_late_valid_summary_never_publishes_and_no_repair_follows(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(study.time, "monotonic", lambda: clock[0])

    class LateTransport:
        def generate(self, *args, **kwargs):
            clock[0] = 91.0
            return ProviderResult(raw_text='{"summary":"Late replacement"}')

    events = []
    result = study.update_summary(
        "Prior", "I prefer examples.", ModelConfig(), None, events.append, adapter=LateTransport()
    )
    assert result["summary"] == "Prior" and result["calls"] == 1
    assert result["error"]["code"] == "SUMMARY_DEADLINE_EXCEEDED"
    assert events[-1]["error_code"] == "SUMMARY_DEADLINE_EXCEEDED"


def test_summary_preprocessing_consumes_the_same_active_deadline(monkeypatch):
    from generation.token_counting import TokenCounter

    clock = [0.0]
    monkeypatch.setattr(study.time, "monotonic", lambda: clock[0])

    def slow_count(self, *args):
        clock[0] = 91.0
        return 10

    monkeypatch.setattr(TokenCounter, "request_input", slow_count)
    transport = Transport([])
    result = study.update_summary(
        "Prior", "I prefer examples.", ModelConfig(), None, lambda event: None, adapter=transport
    )
    assert result["summary"] == "Prior" and result["calls"] == 0 and transport.calls == []
    assert result["error"]["code"] == "SUMMARY_DEADLINE_EXCEEDED"


def test_summary_receives_only_earlier_summary_and_same_current_statement():
    transport = Transport([ProviderResult(raw_text='{"summary":"Use equations."}')])
    result = study.update_summary(
        "Use analogies.",
        "Correction: I prefer equations.",
        ModelConfig(),
        None,
        lambda event: None,
        adapter=transport,
    )
    supplied = json.loads(transport.calls[0][1]["content"])
    assert supplied == {
        "previous_summary": "Use analogies.",
        "learner_statement": "Correction: I prefer equations.",
    }
    assert result["error"] is None and result["summary"] == "Use equations."


@pytest.mark.parametrize(
    "target",
    [
        "sqlite:///test.db",
        "postgresql://u:p@localhost/main",
        "postgresql://u:p@localhost/cs30_memory_study_existing",
    ],
)
def test_target_rejects_nonpostgres_main_and_same_database(target):
    with pytest.raises(ValueError):
        study.validate_target(target, "postgresql://u:p@localhost/cs30_memory_study_existing")


def test_target_allows_only_explicit_separate_disposable_database():
    assert (
        study.validate_target(
            "postgresql+psycopg://u:p@localhost:15432/cs30_memory_study_run1",
            "postgresql+psycopg://u:p@localhost:15432/learning",
        )
        == "cs30_memory_study_run1"
    )


def test_no_live_flag_fails_before_reading_plan_credentials_or_database(tmp_path):
    with pytest.raises(ValueError, match="allow-live"):
        study.run(tmp_path, tmp_path / "absent", tmp_path / "outputs", database_env="ABSENT")
    assert not (tmp_path / "outputs").exists()


def test_reports_keep_failed_uncertain_and_pending_in_all_36_denominator(tmp_path):
    plan = {"schedule": study.schedule(study.cases())}
    first, second = plan["schedule"][:2]
    freeze(
        tmp_path / "results" / (first["id"] + ".json"),
        {
            **first,
            "status": "answer_error",
            "state_checks": [],
            "outcome": {
                "response": None,
                "error": {"code": "TIMEOUT"},
                "budget": {"consumed_calls": 1},
            },
        },
    )
    freeze(tmp_path / "reservations" / (second["id"] + ".json"), second)
    report = study.summarize(tmp_path, plan)
    assert len(report["rows"]) == report["planned_conditions"] == 36
    assert [r["status"] for r in report["rows"][:3]] == [
        "answer_error",
        "interrupted_reservation",
        "pending",
    ]
    assert report["rows"][0]["answer_calls"] == 1
    assert report["rows"][1]["answer_calls"] is None
    assert report["independent_reviews"] == 0


def test_frozen_plan_rejects_duplicate_or_changed_cases(tmp_path):
    for identity in ("W8E-D01", "W8E-D12"):
        freeze(
            tmp_path / "retrieval" / (identity + ".json"),
            {
                "question": identity,
                "evidence": [{"text": "Authored fixture"}],
                "source_map": {"fixture": {}},
            },
        )
    frozen = study.prepare(tmp_path, tmp_path / "plan.json")
    plan = {k: v for k, v in frozen.items() if k != "content_sha256"}
    study.validate_plan(plan)
    changed = deepcopy(plan)
    changed["cases"][-1] = changed["cases"][0]
    with pytest.raises(ValueError, match="case inputs"):
        study.validate_plan(changed)
    changed = deepcopy(plan)
    changed["schedule"].pop()
    with pytest.raises(ValueError, match="schedule"):
        study.validate_plan(changed)


def test_attempt_recovery_keeps_unfinished_reservation_and_reports_only_known_usage(tmp_path):
    events = [
        {"phase": "start", "purpose": "generation"},
        {"phase": "finish", "purpose": "generation", "usage": {"total_tokens": 27}},
        {"phase": "started", "purpose": "rolling_summary"},
    ]
    path = tmp_path / "events.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in events), encoding="utf-8")
    report = study.attempt_accounting(path)
    assert report["consumed_call_reservations"] == 2
    assert report["finished_calls"] == 1 and report["unfinished_reservations"] == 1
    assert report["status"] == "uncertain" and report["recorded_total_tokens"] == 27
    assert report["cost"] is None
    path.write_text(path.read_text(encoding="utf-8") + '\n{"phase":', encoding="utf-8")
    assert study.attempt_accounting(path)["records_readable"] is False


def test_frozen_code_fingerprint_includes_prompt_schema_provider_and_exact_source_mapping():
    hashes = study.source_hashes()
    for path in (
        "generation/checked_schemas.py",
        "generation/prompts/chat_v1.txt",
        "generation/providers.py",
        "retrieval/source_spans.py",
        "personalisation/memory.py",
    ):
        assert path in hashes and len(hashes[path]) == 64
