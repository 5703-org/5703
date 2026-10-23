"""Native grammar and zero-provider fallback controls; no factual verdict is authored."""

from copy import deepcopy
from dataclasses import replace
import importlib.util
from pathlib import Path
import socket
from urllib import request as urllib_request

import pytest

from conversation import query_v22 as native
from generation import GenerationRequest, GenerationService, ModelConfig, RequestBudget
from generation import checked
from generation.adapters import LLMAdapter

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/query201"
N1 = "What are isotopes of an element? Include one example."
HISTORY = [
    {
        "role": "user",
        "message_id": "prior-user",
        "content": "What is photosynthesis?",
        "state": "completed",
    },
    {
        "role": "assistant",
        "message_id": "prior-answer",
        "content": "Authored history only.",
        "state": "completed",
        "answer_id": "prior-owned-answer",
        "answer_response_type": "answer",
        "latest_exchange_available": True,
    },
]


def baseline(package, filename):
    spec = importlib.util.spec_from_file_location(
        package + "._phase201_before_" + filename[:-3], FIXTURES / filename
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def no_external_io(monkeypatch):
    attempts = []

    def blocked(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("Phase201 forbids network, database and model calls")

    for owner, name in [
        (socket, "create_connection"),
        (socket, "getaddrinfo"),
        (socket.socket, "connect"),
        (socket.socket, "connect_ex"),
        (urllib_request, "urlopen"),
        (LLMAdapter, "generate"),
    ]:
        monkeypatch.setattr(owner, name, blocked)
    from sqlalchemy.engine import Engine

    monkeypatch.setattr(Engine, "connect", blocked)
    assert Path(native.__file__).resolve() == ROOT / "conversation/query_v22.py"
    assert Path(checked.__file__).resolve() == ROOT / "generation/checked.py"
    yield
    assert attempts == []


@pytest.mark.parametrize("history", [[], HISTORY])
@pytest.mark.parametrize(
    "question",
    [
        N1,
        "What is osmosis? Give an example.",
        "Why does ice float on liquid water? Please provide one example.",
        "Compare diffusion and osmosis? Show an example.",
    ],
)
def test_complete_current_question_owns_example_without_old_topic(question, history):
    before = deepcopy(history)
    out = native.prepare_query(question, history).model_dump()
    assert not out["needs_clarification"] and out["fallback_reason"] == native.EXAMPLE_ANCHOR
    assert out["original_message"] == out["standalone_query"] == question
    assert out["topic_relation"] == "new_topic" and out["referenced_message_ids"] == []
    requirements = native.describe_requirements(question, out, history)
    assert requirements["requirement_source_text"] == requirements["standalone_query"] == question
    points = requirements["required_knowledge"] + requirements["presentation_requests"]
    assert any("example" in row["request"].casefold() for row in points)
    for row in points:
        span = row.get("request_span")
        if span:
            assert question[span["start"] : span["end"]] == row["request"]
    assert history == before


@pytest.mark.parametrize(
    "question",
    [
        "Include one example.",
        "Give one example.",
        "Explain that with an example.",
        "What are these? Include one example.",
        "Why does that happen? Include one example.",
    ],
)
def test_unowned_requests_still_need_a_referent(question):
    old = baseline("conversation", "query_v22.py").prepare_query(question).model_dump()
    out = native.prepare_query(question).model_dump()
    assert out == old and out["needs_clarification"]
    assert out["fallback_reason"] == "missing_referent"


@pytest.mark.parametrize(
    "question",
    [
        "Include one example.",
        "Explain that with an example.",
        "What are these? Include one example.",
    ],
)
@pytest.mark.parametrize("comparison", [False, True])
def test_history_and_comparison_ambiguity_remain_frozen(question, comparison):
    history = deepcopy(HISTORY)
    if comparison:
        history[0]["content"] = "Compare diffusion and osmosis."
    old = baseline("conversation", "query_v22.py").prepare_query(question, history).model_dump()
    assert native.prepare_query(question, history).model_dump() == old
    if comparison:
        assert (
            old["needs_clarification"]
            and old["fallback_reason"] == "ambiguous_referent_after_comparison"
        )
    else:
        assert old["referenced_message_ids"] == ["prior-user"]


@pytest.mark.parametrize(
    "question",
    [
        "What are isotopes? Include one example of that earlier process.",
        "Describe diffusion, including examples of gases.",
        "What are isotopes? Explain radioactive decay as another process.",
    ],
)
def test_other_clauses_are_not_clipped_or_newly_resolved(question):
    old = baseline("conversation", "query_v22.py").prepare_query(question).model_dump()
    assert native.prepare_query(question).model_dump() == old


def test_actual_failure_is_reproduced_before_repair():
    old = baseline("conversation", "query_v22.py").prepare_query(N1).model_dump()
    assert old["needs_clarification"] and old["fallback_reason"] == "missing_referent"
    assert old["standalone_query"] is None


class ForbiddenAdapter:
    def __init__(self):
        self.calls = 0

    def generate(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError("Deterministic fallback must never invoke a provider")


class RecordingService(GenerationService):
    def __init__(self, adapter):
        super().__init__(adapter, checker_adapter=adapter)
        self.entries = []

    def generate(self, request, budget=None, on_attempt=None, *, programmatic_only=False):
        self.entries.append((deepcopy(request), programmatic_only))
        return super().generate(request, budget, on_attempt, programmatic_only=programmatic_only)


def request_for(state, mode="verified", policy="json_source_citations_v3"):
    question = (
        "Include one example." if state == "clarification" else "What are isotopes of an element?"
    )
    return GenerationRequest(
        request_id="phase201-native-control",
        mode="interactive_chat",
        condition="E1",
        question=question,
        prepared_query=native.prepare_query(question).model_dump(),
        config=ModelConfig(
            provider="openai",
            model="gpt-6-luna",
            window_tokens=65536,
            tokenizer_provider="estimate",
            max_tokens=1024,
            temperature=None,
        ),
        enhancement_version="learning_enhancement_v1",
        reliability_policy="evidence_reliability_v5",
        assertion_source_policy="assertion_source_v1",
        checker_payload_policy="lossless_assertion_checker_tables_v3",
        provider_output_policy=policy,
        verification_mode=mode,
        teaching_context={"turn_role": "user_question", "teaching_mode": "direct", "help_level": 0},
    )


@pytest.mark.parametrize("state", ["clarification", "no_source"])
@pytest.mark.parametrize("mode", ["fast", "verified"])
def test_actual_programmatic_child_preserves_zero_rpc_parent_and_choice(state, mode):
    request = request_for(state, mode)
    original = deepcopy(request)
    adapter = ForbiddenAdapter()
    service = RecordingService(adapter)
    budget = RequestBudget(max_calls=2)
    out = service.generate(request, budget)
    assert out.succeeded, out.error
    assert out.response["response_type"] == (
        "clarification" if state == "clarification" else "refusal"
    )
    assert len(service.entries) == 2 and service.entries[-1][1] is True
    child = service.entries[-1][0]
    assert child.enhancement_version is None
    assert child.provider_output_policy == "json_field_contract_v2"
    assert child.checker_payload_policy == "legacy_fragment_table_v1"
    assert child.request_id == request.request_id
    assert request == original and adapter.calls == budget.consumed_calls == 0
    assert out.budget["consumed_calls"] == 0 and out.evidence == [] and out.attempts == []
    report = out.token_budget["semantic_verification"]
    assert report["mode"] == mode and report["check_executed"] is False
    assert report["check_requested"] is (mode == "verified")


@pytest.mark.parametrize("state", ["clarification", "no_source"])
def test_before_child_really_fails_native_admission_without_provider(state):
    old = baseline("generation", "checked.py")
    adapter = ForbiddenAdapter()
    service = RecordingService(adapter)
    out = old.generate_checked(service, request_for(state), RequestBudget(max_calls=2))
    assert not out.succeeded and out.error["code"] == "PROVIDER_OUTPUT_POLICY_INCOMPATIBLE"
    assert len(service.entries) == 1 and service.entries[0][1] is True
    assert service.entries[0][0].provider_output_policy == "json_source_citations_v3"
    assert adapter.calls == out.budget["consumed_calls"] == 0


@pytest.mark.parametrize("policy", ["strict_v1", "json_field_contract_v2"])
@pytest.mark.parametrize("state", ["clarification", "no_source"])
def test_older_output_policies_keep_same_native_zero_rpc_reply(policy, state):
    old = baseline("generation", "checked.py")
    request = request_for(state, policy=policy)
    left_service, right_service = (
        RecordingService(ForbiddenAdapter()),
        RecordingService(ForbiddenAdapter()),
    )
    before = old.generate_checked(left_service, deepcopy(request), RequestBudget(max_calls=2))
    after = right_service.generate(request, RequestBudget(max_calls=2))
    assert before.succeeded and after.succeeded
    assert after.response == before.response
    assert (
        right_service.entries[-1][0].provider_output_policy
        == left_service.entries[-1][0].provider_output_policy
        == policy
    )
    assert after.budget["consumed_calls"] == before.budget["consumed_calls"] == 0


@pytest.mark.parametrize("programmatic_only", [False, True])
def test_forged_nonenhanced_v3_still_cannot_bypass_admission(programmatic_only):
    adapter = ForbiddenAdapter()
    request = replace(
        request_for("clarification"),
        enhancement_version=None,
        checker_payload_policy="legacy_fragment_table_v1",
    )
    out = GenerationService(adapter, checker_adapter=adapter).generate(
        request, RequestBudget(max_calls=2), programmatic_only=programmatic_only
    )
    assert not out.succeeded and out.error["code"] == "PROVIDER_OUTPUT_POLICY_INCOMPATIBLE"
    assert adapter.calls == out.budget["consumed_calls"] == 0


def test_already_shipped_named_multi_question_content_remains_verbatim():
    """RC1 V22 already admits explicit questions; phase201's old fixture does not."""
    question = "What is osmosis? What is diffusion? Include one example."
    result = native.prepare_query(question).model_dump()
    assert not result["needs_clarification"]
    assert result["standalone_query"] == result["original_message"] == question
    assert result["referenced_message_ids"] == []
    assert result["fallback_reason"] == native.CONTENT_ANCHOR
