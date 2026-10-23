"""Ordinary checkbox control retains local gates; fixtures do not measure quality."""

from copy import deepcopy
from dataclasses import asdict, replace
import json

import pytest

from generation import GenerationService, RequestBudget
from generation import assertion_reselection_v1 as reselection
from generation import verification_mode
from generation.checked import generate_unchecked_research
from generation.types import ProviderResult, failure

from test_assertion_provenance161 import (
    authored_full_checker,
    compiled,
    mapped_request,
    private_draft,
)


class FiniteTransport:
    def __init__(self, values):
        self.values = list(values)
        self.calls = []

    def generate(self, messages, **kwargs):
        if len(self.calls) >= len(self.values):
            raise AssertionError("Unexpected provider interface invocation")
        value = self.values[len(self.calls)]
        self.calls.append((deepcopy(messages), deepcopy(kwargs)))
        if callable(value):
            value = value(messages)
        if isinstance(value, ProviderResult):
            return value
        return ProviderResult(
            raw_text=value if isinstance(value, str) else json.dumps(value),
            provider="openai",
            model="authored-offline-fixture",
            finish_reason="stop",
            request_submitted=False,
            usage={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        )


def request(**changes):
    return mapped_request(**changes)


def test_default_preserves_checked_execution_and_only_accepted_leg_reports_passed():
    adapter = FiniteTransport([private_draft(extra=True), authored_full_checker])
    out = GenerationService(adapter).generate(request(), RequestBudget(max_calls=2))
    assert out.succeeded, out.error
    assert len(adapter.calls) == out.budget["consumed_calls"] == 2
    report = out.token_budget["semantic_verification"]
    assert report["mode"] == "verified" and report["status"] == "passed"
    assert report["check_requested"] and report["check_executed"]
    assert len(out.checks) == 1 and out.checks[0]["accepted"] is True


@pytest.mark.parametrize("current_pair", [False, True])
def test_fast_retains_local_binding_and_skips_checker_adapter_and_reservation(current_pair):
    adapter = FiniteTransport([private_draft(extra=True)])
    service = GenerationService(adapter)
    original_factory = service.make_adapter

    def factory(config, **kwargs):
        assert not kwargs.get("checker"), "Fast cannot construct a checker adapter"
        return original_factory(config, **kwargs)

    service.make_adapter = factory
    extra = (
        {
            "source_block_policy": "raw_corroborated_prose_context_candidate_v1",
            "generation_context_policy": "literal_coverage_complementary_context_candidate_v1",
        }
        if current_pair
        else {}
    )
    out = service.generate(request(verification_mode="fast", **extra), RequestBudget(max_calls=1))
    assert out.succeeded, out.error
    assert len(adapter.calls) == out.budget["consumed_calls"] == 1
    assert not out.checks and out.timing["checking_ms"] == 0
    assert out.attribution["check_state"] == verification_mode.FAST_CHECK_STATE
    assert all(row["support"]["status"] is None for row in out.attribution["claims"])
    report = out.token_budget["semantic_verification"]
    assert report["status"] == "not_requested" and report["check_status"] == "skipped"
    assert report["check_requested"] is report["check_executed"] is False
    assert report["semantic_support"] is None and report["local_source_binding_checked"]
    assert out.drafts[0]["local_source_bindings"]


@pytest.mark.parametrize(
    "defect", ["invalid_json", "foreign_citation", "unknown_source", "changed_hash"]
)
def test_fast_never_bypasses_parse_citation_or_source_identity_faults(defect):
    req = request(verification_mode="fast")
    draft = private_draft(extra=True)
    if defect == "invalid_json":
        draft = "not JSON"
    elif defect == "foreign_citation":
        draft["citations"] = ["ev_999"]
    elif defect == "unknown_source":
        draft["answer_text"][0]["source_ids"] = ["F999"]
    else:
        first = next(iter(req.source_map.values()))
        first["chunk_hash"] = "0" * 64
    adapter = FiniteTransport([draft])
    out = GenerationService(adapter).generate(req, RequestBudget(max_calls=1))
    assert not out.succeeded and out.response is None and out.delivered_projection == {}
    assert len(adapter.calls) <= 1 and not out.checks
    assert out.token_budget["semantic_verification"]["status"] == "not_requested"


def test_fast_invalid_private_draft_retains_existing_finite_terminal_behavior():
    adapter = FiniteTransport(["not JSON"])
    out = GenerationService(adapter).generate(
        request(verification_mode="fast"), RequestBudget(max_calls=2)
    )
    assert out.response is None and out.error["code"] == "INVALID_JSON"
    assert len(adapter.calls) == 1 and out.budget["format_repairs"] == 0
    assert [row["stage"] for row in out.attempts] == ["generation"]
    assert not out.checks and out.token_budget["semantic_verification"]["check_executed"] is False


@pytest.mark.parametrize(
    "defect",
    [
        "hint",
        "pending",
        "attempt",
        "practice",
        "goal",
        "nested_goal",
        "benchmark",
        "special_checker",
        "source_relation",
        "reselection",
        "research_arm",
        "unknown_mode",
    ],
)
def test_forged_fast_protected_or_special_scope_is_rejected_before_generation(defect):
    req = request(verification_mode="fast")
    if defect == "hint":
        req.teaching_context.update(teaching_mode="hint", help_level=1)
    elif defect == "pending":
        req.teaching_context["pending_tutor_question_id"] = "pending-control"
    elif defect == "attempt":
        req.teaching_context["learner_attempt"] = "An answer to grade"
    elif defect == "practice":
        req.teaching_context["practice_context"] = {}
    elif defect == "goal":
        req.teaching_context["goal_id"] = "goal-control"
    elif defect == "nested_goal":
        req.teaching_context["requirements"] = {"practice_goal_context": {}}
    elif defect == "benchmark":
        req.mode = "benchmark_openqa"
    elif defect == "special_checker":
        req.joint_checker_policy = "scoped_compact_v6"
    elif defect == "source_relation":
        req.source_relation_policy = "claim_source_relations_v2"
    elif defect == "reselection":
        req.assertion_reselection = {}
    elif defect == "research_arm":
        req.generation_policy = {"arm": "A"}
    else:
        req.verification_mode = "unknown"
    adapter = FiniteTransport([])
    out = GenerationService(adapter).generate(req)
    assert out.response is None and out.error["code"] == "VERIFICATION_MODE_INVALID"
    assert not adapter.calls and out.budget["consumed_calls"] == 0


def test_fast_research_entry_cannot_reuse_the_ordinary_choice():
    with pytest.raises(ValueError, match="FAST_VERIFICATION_SCOPE_INVALID"):
        generate_unchecked_research(
            GenerationService(FiniteTransport([])), request(verification_mode="fast")
        )


def test_shared_mapping_guard_allows_general_knowledge_and_reading_context():
    req = request(verification_mode="fast")
    req.answer_mode = "general_knowledge"
    req.assertion_source_policy = None
    req.reading_context = {"source": "owned-reading-control"}
    assert verification_mode.validate_request(asdict(req)) == "fast"


def test_general_knowledge_fast_uses_its_explicit_uncited_generation_path():
    req = request(verification_mode="fast")
    req.answer_mode = "general_knowledge"
    req.assertion_source_policy = None
    req.evidence, req.source_map = [], {}
    value = {
        "schema_version": "chat_response_v1",
        "response_type": "answer",
        "answer_text": "This is an authored general-knowledge control.",
        "short_answer": None,
        "citations": [],
        "refusal_reason": None,
        "follow_up_questions": [],
        "confidence": None,
        "tutor_question": None,
        "learner_attempt_evaluation": None,
    }
    adapter = FiniteTransport([value])
    out = GenerationService(adapter).generate(req, RequestBudget(max_calls=1))
    assert out.succeeded, out.error
    assert len(adapter.calls) == 1 and not out.checks and out.evidence == []
    assert out.token_budget["source_provenance"] == "model_general_knowledge_unverified"
    assert out.token_budget["semantic_verification"]["status"] == "not_requested"


def test_mock_direct_without_semantic_dispatch_never_becomes_verified_passed():
    req = request()
    req.assertion_source_policy = None
    req.config = replace(req.config, provider="mock")
    value = {
        "schema_version": "chat_response_v1",
        "response_type": "answer",
        "answer_text": "An authored explanation. [ev_001]",
        "short_answer": None,
        "citations": ["ev_001"],
        "refusal_reason": None,
        "follow_up_questions": [],
        "confidence": None,
        "tutor_question": None,
        "learner_attempt_evaluation": None,
    }
    adapter = FiniteTransport([value])
    service = GenerationService()
    service.make_adapter = lambda *args, **kwargs: adapter
    out = service.generate(req, RequestBudget(max_calls=1))
    assert out.succeeded, out.error
    assert len(adapter.calls) == 1 and not out.checks
    report = out.token_budget["semantic_verification"]
    assert report["status"] == "not_performed" and report["check_executed"] is False


def test_no_evidence_remains_zero_call_and_never_claims_semantic_verification():
    req = request(verification_mode="fast")
    req.evidence, req.source_map = [], {}
    adapter = FiniteTransport([])
    out = GenerationService(adapter).generate(req)
    assert out.succeeded and out.response["response_type"] == "refusal"
    assert not adapter.calls and out.budget["consumed_calls"] == 0
    assert out.token_budget["semantic_verification"]["check_executed"] is False


@pytest.mark.parametrize("verdict", ["rejected", "uncertain"])
def test_verified_failure_retains_check_dispatch_and_never_reports_passed(verdict):
    def check(messages):
        if verdict == "uncertain":
            return ProviderResult(
                provider="openai",
                error=failure("PROVIDER_TIMEOUT", "Authored timeout", uncertain=True),
                request_submitted=True,
            )
        value = authored_full_checker(messages)
        value["body_ok"] = False
        value["claims"][0]["status"] = "partial"
        value["claims"][0]["proof_audit"].update(
            all_predicates_entailed=False,
            causal_bridges_entailed=False,
            missing_predicates=["Authored missing bridge control."],
        )
        return value

    adapter = FiniteTransport([private_draft(extra=True), check])
    out = GenerationService(adapter).generate(request(), RequestBudget(max_calls=2))
    assert out.response is None and len(adapter.calls) == 2
    report = out.token_budget["semantic_verification"]
    assert report["status"] != "passed" and report["check_requested"] and report["check_executed"]
    assert report["status"] == ("unknown" if verdict == "uncertain" else "failed")


@pytest.mark.parametrize("prior_check", [False, True])
def test_check_cancelled_before_submission_preserves_actual_execution_history(prior_check):
    cancelled = ProviderResult(
        provider="openai",
        error=failure("CANCELLED", "Authored cancellation before submission"),
        request_submitted=False,
    )
    req = request(assertion_source_policy=None) if prior_check else request()
    values = [compiled(extra=True)[0] if prior_check else private_draft(extra=True)]
    if prior_check:
        values.append(
            ProviderResult(
                provider="openai",
                raw_text='{"bad":"schema"}',
                finish_reason="stop",
                request_submitted=True,
            )
        )
    values.append(cancelled)
    adapter = FiniteTransport(values)
    out = GenerationService(adapter).generate(req, RequestBudget(max_calls=3))
    assert out.response is None and len(adapter.calls) == (3 if prior_check else 2)
    report = out.token_budget["semantic_verification"]
    assert report["status"] == ("failed" if prior_check else "not_performed")
    assert report["check_executed"] is prior_check


def test_default_field_does_not_change_historical_reselection_request_digest():
    req = request()
    old = asdict(req)
    old.pop("verification_mode")
    old.pop("assertion_reselection")
    assert reselection.request_sha256(req) == reselection.canonical_sha256(old)
    assert reselection.request_sha256(
        replace(req, verification_mode="fast")
    ) != reselection.request_sha256(req)


def test_report_cannot_fabricate_a_pass_for_a_skipped_check():
    with pytest.raises(ValueError, match="VERIFICATION_RECEIPT_INVALID"):
        verification_mode.receipt("fast", "passed", check_executed=True)
    with pytest.raises(ValueError, match="VERIFICATION_RECEIPT_INVALID"):
        verification_mode.receipt("verified", "passed")
