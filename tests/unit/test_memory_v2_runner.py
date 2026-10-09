"""Research recovery must preserve charges, stop conditions and private labels."""

from evaluation.memory_v2.runner import update_stop_state, make_request
from generation.types import ModelConfig


def attempt(provider="deepseek", code=None, status=None):
    return {
        "provider": provider,
        "request_submitted": True,
        "error": {"code": code} if code else None,
        "diagnostic": {"http_status": status},
    }


def record(*attempts):
    return {"outcome": {"attempts": list(attempts)}}


def test_transport_streak_is_per_provider_and_replays_across_restart():
    rows = [
        record(attempt(code="PROVIDER_NETWORK_ERROR")),
        record(attempt("openai")),
        record(attempt(code="PROVIDER_TIMEOUT")),
        record(attempt(status=503, code="PROVIDER_HTTP_ERROR")),
    ]
    live = {}
    reasons = [update_stop_state(row, live) for row in rows]
    resumed = {}
    for row in rows[:3]:
        assert update_stop_state(row, resumed) is None
    assert update_stop_state(rows[3], resumed) == reasons[-1]
    assert reasons[-1] == "three_consecutive_provider_transport_failures"


def test_success_resets_only_its_provider_and_auth_denial_stops():
    state = {"deepseek": 2, "openai": 2}
    assert update_stop_state(record(attempt()), state) is None
    assert state == {"deepseek": 0, "openai": 2}
    assert update_stop_state(record(attempt(status=401, code="PROVIDER_HTTP_ERROR")), state)
    assert update_stop_state({"recovered_attempts": [attempt(status=402)]}, {})


def test_terminal_missing_rows_never_clear_existing_stop():
    assert update_stop_state({"status": "not_run"}, {}, "runtime_changed") == "runtime_changed"


def test_generation_request_excludes_private_gold_and_oracle_metadata():
    task = {
        "id": "case",
        "question": "Compare two tissues.",
        "turns": ["A hint"],
        "task_type": "comparison",
        "critical_answer": "PRIVATE GOLD",
        "oracle_confirmation": {"reviewer_id": "PRIVATE REVIEWER"},
    }
    row = {"id": "case-B2-1", "study": "B", "turn": 1, "arm": "B2"}
    checkpoint = {
        "model_config": ModelConfig().to_dict(),
        "checker_config": ModelConfig().to_dict(),
    }
    request = make_request(row, task, {"evidence": []}, checkpoint, [], [])
    assert "PRIVATE" not in repr(request)
    assert request.reliability_policy == "evidence_reliability_v2"
    assert request.memory_context is None
    assert request.teaching_context["teaching_mode"] == "direct"
