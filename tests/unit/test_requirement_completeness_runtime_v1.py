"""Native opt-in path and conservative observation controls, no model calls."""

from copy import deepcopy
from dataclasses import asdict
import json
from types import SimpleNamespace

import pytest

from generation import GenerationRequest, GenerationService, RequestBudget
from generation import requirement_completeness_runtime_v1 as runtime
from generation.adapters import chat_value
from test_semantic_binding_repair_routing import AuthoredTransport, request, no_external_io


def run(policy=None):
    value = request(None, "irrelevant")
    value.verification_mode = "fast"
    value.requirement_completeness_policy = policy
    adapter = AuthoredTransport(None, "irrelevant", positive=True)
    return GenerationService(adapter).generate(value, RequestBudget()), adapter, value


def test_default_native_path_unchanged_and_no_observer_receipt():
    outcome, adapter, value = run()
    assert outcome.succeeded
    assert [kw["request_context"]["purpose"] for _, kw in adapter.calls] == ["generation"]
    assert "requirement_completeness_observation" not in outcome.token_budget
    assert all("REQUIREMENT_COMPLETENESS_DATA" not in m["content"] for m in outcome.messages)


def test_explicit_native_fast_path_one_generation_no_check_and_no_answer_rewrite():
    baseline, base_adapter, _ = run()
    observed, adapter, value = run(runtime.POLICY)
    assert observed.succeeded and observed.response == baseline.response
    assert [kw["request_context"]["purpose"] for _, kw in adapter.calls] == ["generation"]
    assert adapter.calls[0][1]["response_schema"] == base_adapter.calls[0][1]["response_schema"]
    assert observed.token_budget["semantic_verification"]["mode"] == "fast"
    report = observed.token_budget["requirement_completeness_observation"]
    assert report["extra_provider_requests"] == 0 and report["semantic_completeness"] is None
    assert not report["response_modified"] and not report["automatic_refusal"]
    assert any("REQUIREMENT_COMPLETENESS_DATA" in m["content"] for m in adapter.calls[0][0])
    assert observed.token_budget["requirement_completeness_prompt"]["applied"]
    # The top-level legacy packing estimate precedes checked prompt assembly.
    # Admission uses the actual assembled generation-stage reservation.
    assert (
        observed.token_budget["stage_token_budgets"][0]["input_reserved_tokens"]
        > baseline.token_budget["stage_token_budgets"][0]["input_reserved_tokens"]
    )


def test_extra_prompt_tokens_obey_existing_window_gate_before_dispatch():
    from dataclasses import replace

    value = request(None, "irrelevant")
    value.verification_mode = "fast"
    value.config = replace(value.config, window_tokens=8300)
    adapter = AuthoredTransport(None, "irrelevant", positive=True)
    baseline = GenerationService(adapter).generate(value)
    assert baseline.succeeded and len(adapter.calls) == 1
    value.requirement_completeness_policy = runtime.POLICY
    adapter = AuthoredTransport(None, "irrelevant", positive=True)
    observed = GenerationService(adapter).generate(value)
    assert not observed.succeeded and observed.error["code"] == "CONTEXT_LIMIT"
    assert not adapter.calls


def test_strict_citation_mismatch_still_rejects_under_opt_in():
    class BadCitation(AuthoredTransport):
        def generate(self, messages, **kwargs):
            result = super().generate(messages, **kwargs)
            value = json.loads(result.raw_text)
            value["citations"] = ["ev_999"]
            result.raw_text = json.dumps(value)
            return result

    failures = []
    for policy in [None, runtime.POLICY]:
        value = request(None, "irrelevant")
        value.verification_mode = "fast"
        value.requirement_completeness_policy = policy
        out = GenerationService(BadCitation(None, "irrelevant", positive=True)).generate(
            value, RequestBudget(max_calls=1)
        )
        assert not out.succeeded and out.response is None
        failures.append(out.error["code"])
    assert failures[0] == failures[1]


@pytest.mark.parametrize(
    "mutation",
    [
        ("verification_mode", "verified"),
        ("answer_mode", "general_knowledge"),
        ("mode", "benchmark_openqa"),
        ("requirement_completeness_policy", "unknown"),
    ],
)
def test_invalid_experimental_scope_fails_before_provider(mutation):
    value = request(None, "irrelevant")
    value.verification_mode = "fast"
    value.requirement_completeness_policy = runtime.POLICY
    setattr(value, *mutation)
    adapter = AuthoredTransport(None, "irrelevant", positive=True)
    out = GenerationService(adapter).generate(value)
    assert not out.succeeded and out.error["code"] == "REQUIREMENT_COMPLETENESS_POLICY_INVALID"
    assert not adapter.calls


def test_hint_cannot_silently_become_unchecked_complete_answer():
    value = request(None, "irrelevant")
    value.verification_mode = "fast"
    value.requirement_completeness_policy = runtime.POLICY
    value.teaching_context.update(teaching_mode="hint", help_level=1)
    with pytest.raises(ValueError):
        runtime.validate_request(value)
    assert (
        runtime.observe(
            "How much per turn?",
            chat_value("answer", "Try the next step.", citations=[]),
            teaching_mode="hint",
        )["status"]
        == "hint_not_completion"
    )


def test_submission_default_and_ineligible_modes_emit_no_new_field():
    args = {
        "verification_mode": "fast",
        "answer_mode": "textbook",
        "teaching": {"teaching_mode": "direct", "help_level": 0},
    }
    assert runtime.submission_fields(None, **args) == {}
    assert runtime.submission_fields(runtime.POLICY, **args) == {
        "requirement_completeness_policy": runtime.POLICY
    }
    for mutation in [
        {"verification_mode": "verified"},
        {"reading_context": {"source": "chosen"}},
        {"teaching": {"teaching_mode": "hint", "help_level": 1}},
        {"answer_mode": "general_knowledge"},
    ]:
        assert runtime.submission_fields(runtime.POLICY, **{**args, **mutation}) == {}


def test_saved_explicit_policy_survives_roundtrip_and_old_request_defaults_off():
    value = request(None, "irrelevant")
    value.verification_mode = "fast"
    value.requirement_completeness_policy = runtime.POLICY
    data = asdict(value)
    config = data.pop("config")
    checker = data.pop("checker_config")
    data = json.loads(json.dumps(data))
    restored = GenerationRequest(**data, config=value.config)
    assert runtime.validate_request(restored) == runtime.POLICY
    data.pop("requirement_completeness_policy")
    assert GenerationRequest(**data, config=value.config).requirement_completeness_policy is None


@pytest.mark.parametrize(
    "unit", ["rotation", "joule", "passenger-kilometre", "trial", "opening", "packet"]
)
def test_cross_domain_missing_rate_is_advisory_not_a_refusal(unit):
    q = f"Give the quantity per {unit}."
    response = {"response_type": "answer", "answer_text": "The device moves three objects."}
    before = deepcopy(response)
    result = runtime.observe(q, response)
    assert result["observations"][0]["status"] == "no_literal_unit_link_found_review_needed"
    assert response == before and not result["automatic_retry"] and not result["automatic_refusal"]


@pytest.mark.parametrize(
    "answer,status",
    [
        ("Three packets per rotation.", "literal_relation_present_unverified"),
        ("One rotation moves three packets.", "quantity_mentioned_relation_unverified"),
        ("No packets move per rotation.", "literal_relation_present_unverified"),
        (
            "The source does not specify packets per rotation.",
            "literal_relation_present_unverified",
        ),
    ],
)
def test_presence_wrong_quantity_negation_and_limitation_never_certify_completeness(answer, status):
    result = runtime.observe(
        "Give packets per rotation.", {"response_type": "answer", "answer_text": answer}
    )
    assert result["observations"][0]["status"] == status
    assert result["semantic_completeness"] is None and result["semantic_support"] is None


@pytest.mark.parametrize(
    "question",
    [
        "Do not give quantities per rotation.",
        'Explain the phrase "per rotation".',
        "Give mass per square metre.",
    ],
)
def test_negative_quoted_and_unsupported_compound_request_abstain(question):
    result = runtime.observe(question, {"response_type": "answer", "answer_text": "A response."})
    assert not result["observations"] and result["status"].startswith("not_assessed")


def test_refusal_is_not_completion_and_quoted_answer_is_not_witness():
    assert (
        runtime.observe(
            "Give packets per rotation.",
            {"response_type": "refusal", "answer_text": "No evidence."},
        )["status"]
        == "non_answer_not_completion"
    )
    result = runtime.observe(
        "Give packets per rotation.",
        {
            "response_type": "answer",
            "answer_text": 'You requested "per rotation"; the device moves three packets.',
        },
    )
    assert result["observations"][0]["answer_span"] is None


def test_default_setting_is_off_and_invalid_policy_is_rejected():
    from app.core.config import Settings

    assert Settings(_env_file=None).chat_requirement_completeness_policy is None
    with pytest.raises(ValueError):
        Settings(_env_file=None, chat_requirement_completeness_policy="unknown")


@pytest.mark.parametrize(
    "extra",
    [
        {"turn_role": "learner_attempt"},
        {"learner_attempt": "An authored attempt"},
        {"attempt_history": [{"feedback": "Authored history"}]},
    ],
)
def test_practice_or_attempt_context_never_silently_enables_candidate(extra):
    value = request(None, "irrelevant")
    value.verification_mode = "fast"
    value.requirement_completeness_policy = runtime.POLICY
    value.teaching_context.update(extra)
    with pytest.raises(ValueError):
        runtime.validate_request(value)
    assert (
        runtime.submission_fields(
            runtime.POLICY,
            verification_mode="fast",
            answer_mode="textbook",
            teaching={"teaching_mode": "direct", **extra},
        )
        == {}
    )


@pytest.mark.parametrize("fallback", ["no_sources", "missing_referent"])
def test_completeness_opt_in_preserves_zero_call_programmatic_fallback(fallback, monkeypatch):
    from dataclasses import replace

    class NoTransport:
        def generate(self, *args, **kwargs):
            pytest.fail("A deterministic fallback must not dispatch a provider")

    original = request(None, "irrelevant")
    original.verification_mode = "fast"
    if fallback == "no_sources":
        original.evidence = []
        original.source_map = {}
    else:
        original.prepared_query = {
            "standalone_query": original.question,
            "needs_clarification": True,
            "intent": "factual",
            "topic_relation": "new_topic",
            "fallback_reason": "missing_referent",
            "clarification_question": "Which monitor do you mean?",
        }
    baseline = GenerationService(NoTransport()).generate(original, RequestBudget(max_calls=1))
    enabled = replace(original, requirement_completeness_policy=runtime.POLICY)
    calls = []
    validate = runtime.validate_request

    def observed(value):
        calls.append((value.requirement_completeness_policy, value.verification_mode))
        return validate(value)

    monkeypatch.setattr(runtime, "validate_request", observed)
    candidate = GenerationService(NoTransport()).generate(enabled, RequestBudget(max_calls=1))
    assert baseline.error is None and baseline.response is not None
    assert candidate.error is None and candidate.response == baseline.response
    assert candidate.response["response_type"] != "answer"
    assert not candidate.response["citations"]
    assert candidate.budget["consumed_calls"] == baseline.budget["consumed_calls"] == 0
    assert enabled.requirement_completeness_policy == runtime.POLICY
    assert enabled.verification_mode == "fast"
    assert (None, "verified") in calls
    assert candidate.token_budget["semantic_verification"]["mode"] == "fast"
    assert (
        candidate.token_budget["requirement_completeness_observation"]["status"]
        == "non_answer_not_completion"
    )
    assert "requirement_completeness_prompt" not in candidate.token_budget
