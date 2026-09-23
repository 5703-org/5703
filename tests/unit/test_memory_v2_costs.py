"""Authored projections of actual runner journals, never private study fixtures."""

import json

import pytest

from evaluation.enhancement.protocol import digest, freeze
from evaluation.memory_v2.costs import Collector, collect


CONFIG = {
    "provider": "openai_compatible",
    "model": "deepseek-flash",
    "base_url": "https://api.deepseek.com/v1",
    "configuration_id": "managed:answer",
}
USAGE = {
    "input_tokens": 100,
    "output_tokens": 10,
    "total_tokens": 110,
    "cache_hit_input_tokens": 60,
    "cache_miss_input_tokens": 40,
}
START = "2026-09-21T13:02:09+00:00"
FINISH = "2026-09-21T13:02:12+00:00"


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def journal(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(v) for v in rows) + "\n", encoding="utf-8")


def attempt(identity="Q:attempt:1", **changes):
    return {
        "attempt_id": identity,
        "purpose": "generation",
        "provider": CONFIG["provider"],
        "model": CONFIG["model"],
        "configuration_id": CONFIG["configuration_id"],
        "request_submitted": True,
        "usage": USAGE,
        **changes,
    }


def pilot(root, *, saved=None, events=None):
    freeze(root / "pilot.json", {"checkpoint": {"model_config": CONFIG}})
    a = attempt()
    freeze(
        root / "results/Q.json",
        saved
        or {
            "id": "Q",
            "status": "answer",
            "outcome": {"attempts": [a], "budget": {"consumed_calls": 1}},
        },
    )
    journal(
        root / "events/Q.jsonl",
        events
        if events is not None
        else [
            {
                "phase": "start",
                "recorded_at": START,
                "attempt_id": a["attempt_id"],
                "purpose": a["purpose"],
                "messages": "PRIVATE_PROMPT",
            },
            {"phase": "finish", "recorded_at": FINISH, **a, "raw_text": "PRIVATE_ANSWER"},
        ],
    )


def test_pilot_journal_and_saved_outcome_count_once_with_exact_times_and_private_projection(
    tmp_path,
):
    pilot(tmp_path)
    result = collect(runs=[tmp_path, tmp_path])
    assert result["total"]["attempts"] == 1
    assert result["total"]["tokens"]["total_tokens"]["known_subtotal"] == 110
    assert result["total"]["estimated_cny_complete"] == pytest.approx(0.0000812)
    row = result["rows"][0]
    assert row["timestamp_basis"] == "attempt_completion" and row["completed_at"] == FINISH
    assert len(row["observations"]) == 3
    output = json.dumps(result)
    assert all(s not in output for s in ("PRIVATE_PROMPT", "PRIVATE_ANSWER", str(tmp_path)))


def test_missing_usage_and_unfinished_reservations_are_unknown_not_zero(tmp_path):
    pilot(
        tmp_path,
        saved={
            "id": "Q",
            "status": "error",
            "outcome": {"attempts": [], "budget": {"consumed_calls": 2}},
        },
        events=[{"phase": "start", "attempt_id": "Q:attempt:1", "recorded_at": START}],
    )
    result = collect(runs=[tmp_path])
    assert result["total"]["attempts"] == 2
    assert result["total"]["unknown_cost_attempts"] == 2
    assert result["total"]["estimated_cny_complete"] is None
    assert result["total"]["unfinished_attempts"] == 2


@pytest.mark.parametrize("submitted,expected", [(False, 0.0), (True, None), (None, None)])
def test_explicit_non_submission_is_distinct_from_submitted_or_uncertain(
    tmp_path, submitted, expected
):
    a = attempt(request_submitted=submitted, usage={})
    pilot(tmp_path, saved={"id": "Q", "outcome": {"attempts": [a]}}, events=[])
    result = collect(runs=[tmp_path])
    assert result["rows"][0]["estimated_cny"] == expected
    assert result["rows"][0]["request_submitted"] is submitted


@pytest.mark.parametrize(
    "bad_usage",
    [
        {**USAGE, "cache_miss_input_tokens": 41},
        {**USAGE, "total_tokens": 111},
        {**USAGE, "cache_hit_input_tokens": True},
    ],
)
def test_inconsistent_or_boolean_tokens_cannot_produce_complete_cost(tmp_path, bad_usage):
    a = attempt(usage=bad_usage)
    pilot(
        tmp_path, saved={"id": "Q", "completed_at": FINISH, "outcome": {"attempts": [a]}}, events=[]
    )
    assert collect(runs=[tmp_path])["total"]["estimated_cny_complete"] is None


def test_conflicting_result_and_journal_usage_fail_closed(tmp_path):
    pilot(
        tmp_path,
        saved={"id": "Q", "outcome": {"attempts": [attempt(usage={**USAGE, "output_tokens": 11})]}},
    )
    with pytest.raises(ValueError, match="Conflicting usage"):
        collect(runs=[tmp_path])


def test_memory_extraction_m1_m2_and_shared_m3_m4_do_not_duplicate_calls(tmp_path):
    freeze(tmp_path / "extraction-manifest.json", {"configuration": CONFIG, "planned": 24})
    freeze(tmp_path / "state-manifest.json", {"worker_alias": CONFIG})
    extraction = {
        "sequence": 1,
        "purpose": "memory_extraction_v2",
        "usage": USAGE,
        "request_submitted": True,
    }
    freeze(
        tmp_path / "extraction/M01-E1.json",
        {"id": "M01-E1", "attempts": [extraction], "completed_at": FINISH},
    )
    journal(
        tmp_path / "events/M01-E1.jsonl",
        [
            {"sequence": 1, "phase": "start", "recorded_at": START},
            {**extraction, "phase": "finish", "recorded_at": FINISH},
        ],
    )
    summary = {"purpose": "rolling_summary", "usage": USAGE}
    writer = {"phase": "finish", "sequence": 1, "purpose": "memory_extraction", "usage": USAGE}
    freeze(
        tmp_path / "states/M01.json",
        {
            "id": "M01",
            "status": "ready",
            "completed_at": FINISH,
            "summary_updates": [{"calls": 1, "usage": [USAGE]}],
            "provider_outcomes": [{"attempts": [summary]}, {"attempts": [writer]}],
            "accounting": {"M2": {"consumed_call_reservations": 2, "records_readable": True}},
            "probes": [
                {"states": {"M3": {"PRIVATE_MEMORY": "secret"}, "M4": {"PRIVATE_MEMORY": "secret"}}}
            ],
        },
    )
    journal(
        tmp_path / "events/M01-state.jsonl",
        [
            {"phase": "started", "purpose": "rolling_summary", "recorded_at": START},
            {"phase": "finished", **summary, "recorded_at": FINISH},
        ],
    )
    result = collect(runs=[tmp_path])
    assert result["total"]["attempts"] == 4  # extractor + summary + M2 finish + M2 unresolved
    assert result["by_role"]["memory_writer_M2"]["attempts"] == 2
    assert result["by_role"]["memory_summary_M1"]["attempts"] == 1
    assert result["total"]["unknown_cost_attempts"] == 1
    assert "PRIVATE_MEMORY" not in json.dumps(result)
    m2 = next(r for r in result["rows"] if r["purpose"] == "memory_extraction" and r["has_finish"])
    assert m2["timestamp_basis"] == "result_completion_proxy"


def test_m1_missing_journal_uses_saved_usage_once_and_retains_missing_reservation(tmp_path):
    freeze(tmp_path / "state-manifest.json", {"worker_alias": CONFIG})
    freeze(
        tmp_path / "states/M01.json",
        {
            "id": "M01",
            "completed_at": FINISH,
            "summary_updates": [{"calls": 2, "usage": [USAGE]}],
            "provider_outcomes": [{"attempts": [{"usage": USAGE}]}],
        },
    )
    result = collect(runs=[tmp_path])
    assert result["total"]["attempts"] == 2 and result["total"]["unknown_cost_attempts"] == 1


def test_separate_checker_model_endpoint_is_not_priced_as_deepseek(tmp_path):
    checker = {
        **CONFIG,
        "configuration_id": "managed:checker",
        "model": "another-model",
        "base_url": "https://example.org/v1",
    }
    freeze(
        tmp_path / "pilot.json", {"checkpoint": {"model_config": CONFIG, "checker_config": checker}}
    )
    a = attempt(
        purpose="joint_check", configuration_id=checker["configuration_id"], model=checker["model"]
    )
    freeze(
        tmp_path / "results/Q.json",
        {"id": "Q", "completed_at": FINISH, "outcome": {"attempts": [a]}},
    )
    row = collect(runs=[tmp_path])["rows"][0]
    assert row["endpoint"] == "https://example.org" and row["estimated_cny"] is None


def test_judge_plan_binding_and_unfinished_attempt_are_preserved(tmp_path):
    plan = {"model_config": CONFIG, "rows": [{"id": "B1-Q"}, {"id": "B2-Q"}]}
    freeze(tmp_path / "judge-plan.json", plan)
    a = attempt("offline-1", purpose="offline_memory_v2_judge")
    freeze(
        tmp_path / "judgments/B1-Q.json",
        {"id": "B1-Q", "plan_sha256": digest(plan), "state": "judged", "attempts": [a]},
    )
    journal(
        tmp_path / "judge-events/B1-Q.jsonl",
        [
            {"phase": "start", "attempt_id": "offline-1", "recorded_at": START},
            {"phase": "finish", **a, "recorded_at": FINISH},
        ],
    )
    journal(
        tmp_path / "judge-events/B2-Q.jsonl",
        [{"phase": "start", "attempt_id": "offline-1", "recorded_at": START}],
    )
    result = collect(judges=[tmp_path])
    assert result["total"]["attempts"] == 2 and result["total"]["unfinished_attempts"] == 1
    put(tmp_path / "judgments/B1-Q.json", {"plan_sha256": "wrong"})
    with pytest.raises(ValueError, match="different plan"):
        collect(judges=[tmp_path])


def test_provider_diagnostics_not_run_started_failed_are_distinct_and_no_raw_error_echo(tmp_path):
    plan = {
        "candidate_config": {**CONFIG, "model": "gpt-test", "base_url": "https://api.openai.com/v1"}
    }
    put(tmp_path / "plan.json", plan)
    for index, status in enumerate(("not_run", "started", "failed")):
        put(
            tmp_path / f"attempt-{index}.json",
            {
                "stage_id": str(index),
                "plan_hash": digest(plan),
                "tier": "project",
                "role": "checker",
                "status": status,
                "started_at": START,
                "diagnostic": {"message": "SECRET_PROMPT", "request_submitted": True}
                if status == "failed"
                else {},
            },
        )
    result = collect(accounting=[tmp_path])
    assert result["total"]["attempts"] == 2 and result["total"]["unfinished_attempts"] == 1
    assert result["total"]["unknown_cost_attempts"] == 2
    assert result["request_status_counts"]["not_run"] == 1
    assert "SECRET_PROMPT" not in json.dumps(result)


def test_generic_safe_exports_deduplicate_stable_execution_and_actual_provider_receipts(tmp_path):
    row = {
        **CONFIG,
        **attempt(),
        "execution_id": "run1",
        "request_id": "Q",
        "completed_at": FINISH,
        "provider_request_id": "actual-call-123",
        "messages": "PRIVATE",
    }
    put(tmp_path / "one.json", {"rows": [row]})
    put(tmp_path / "two.json", {"rows": [row, {**row, "execution_id": "copy2"}]})
    result = collect(accounting=[tmp_path / "one.json", tmp_path / "two.json"])
    assert result["total"]["attempts"] == 1
    assert "PRIVATE" not in json.dumps(result)


@pytest.mark.parametrize(
    "at,expected",
    [
        ("2026-09-21T01:00:00Z", 0.0001624),
        ("2026-09-21T04:00:00Z", 0.0000812),
        ("2026-09-20T01:00:00Z", 0.0000812),
    ],
)
def test_dated_tariff_peak_boundaries_and_weekend(at, expected):
    c = Collector()
    c.request(
        __import__("pathlib").Path("fixture"),
        "Q",
        {"attempts": [attempt(completed_at=at)]},
        None,
        CONFIG,
    )
    assert c.report()["total"]["estimated_cny_complete"] == pytest.approx(expected)


def test_malformed_or_duplicate_journal_refuses_false_complete_report(tmp_path):
    pilot(tmp_path)
    with (tmp_path / "events/Q.jsonl").open("a", encoding="utf-8") as stream:
        stream.write('{"phase":')
    with pytest.raises(ValueError, match="Malformed"):
        collect(runs=[tmp_path])


def test_unreadable_m2_accounting_prevents_complete_total_even_without_visible_attempts(tmp_path):
    freeze(tmp_path / "state-manifest.json", {"worker_alias": CONFIG})
    freeze(
        tmp_path / "states/M01.json",
        {
            "id": "M01",
            "accounting": {"M2": {"records_readable": False, "consumed_call_reservations": 0}},
        },
    )
    result = collect(runs=[tmp_path])
    assert result["total"]["estimated_cny_complete"] is None
    assert result["warnings"]


@pytest.mark.parametrize("with_result", [False, True])
def test_request_reservation_without_call_journal_is_unknown_without_inventing_calls(
    tmp_path, with_result
):
    freeze(tmp_path / "pilot.json", {"checkpoint": {"model_config": CONFIG}})
    freeze(tmp_path / "reservations/Q.json", {"id": "Q", "reserved_at": START})
    if with_result:
        freeze(
            tmp_path / "results/Q.json",
            {
                "id": "Q",
                "status": "error",
                "reason": "uncertain_external_completion_preserved",
                "recovered_attempts": [],
            },
        )
    result = collect(runs=[tmp_path])
    assert result["total"]["attempts"] == 0
    assert result["total"]["estimated_cny_complete"] is None
    assert not result["total"]["completeness_established"]


def test_m1_incomplete_journal_honors_durable_total(tmp_path):
    freeze(tmp_path / "state-manifest.json", {"worker_alias": CONFIG})
    freeze(
        tmp_path / "states/M01.json",
        {
            "id": "M01",
            "accounting": {"summary": {"records_readable": True, "consumed_call_reservations": 2}},
        },
    )
    journal(
        tmp_path / "events/M01-state.jsonl",
        [
            {"phase": "started", "recorded_at": START},
            {"phase": "finished", "recorded_at": FINISH, "usage": USAGE},
        ],
    )
    result = collect(runs=[tmp_path])
    assert result["total"]["attempts"] == 2
    assert result["total"]["unknown_cost_attempts"] == 1


def test_actual_staged_dto_and_single_debug_diagnosis_use_exact_config_and_ignore_aggregate(
    tmp_path,
):
    run = tmp_path / "pilot"
    freeze(run / "pilot.json", {"checkpoint": {"model_config": CONFIG}})
    stage = {
        "id": "stage-1",
        "tier": "project",
        "status": "failed",
        "started_at": START,
        "completed_at": FINISH,
        "metadata": {"configuration_id": CONFIG["configuration_id"]},
        "provider": CONFIG["provider"],
        "model": CONFIG["model"],
        "usage": USAGE,
        "request_submitted": True,
        "diagnostic_code": "INVALID",
    }
    suite = {
        "id": "suite-1",
        "status": "failed",
        "role": "checker",
        "stages": [stage],
        "usage": {"input_tokens": 999999},
        "message": "PRIVATE_ERROR",
    }
    put(tmp_path / "suite.json", suite)
    put(
        tmp_path / "diagnosis.json",
        {
            "actual_generate_calls": 1,
            "metadata": {"configuration_id": CONFIG["configuration_id"]},
            "completed_at": FINISH,
            "usage": USAGE,
            "diagnostic": {"request_submitted": True, "message": "PRIVATE_DEBUG"},
        },
    )
    result = collect(runs=[run], accounting=[tmp_path / "suite.json", tmp_path / "diagnosis.json"])
    assert result["total"]["attempts"] == 2
    assert result["total"]["tokens"]["input_tokens"]["known_subtotal"] == 200
    assert result["total"]["unknown_cost_attempts"] == 0
    assert "PRIVATE_" not in json.dumps(result)


def test_changed_inputs_fail_and_untrusted_role_is_hashed(tmp_path):
    path = tmp_path / "input.json"
    put(
        path,
        {
            "rows": [
                {
                    **CONFIG,
                    **attempt(),
                    "execution_id": "E",
                    "request_id": "Q",
                    "role": "PRIVATE ROLE TEXT",
                }
            ]
        },
    )
    c = Collector()
    c.accounting(path)
    assert "PRIVATE ROLE TEXT" not in json.dumps(c.report())
    put(path, {})
    with pytest.raises(ValueError, match="changed"):
        c.report()
