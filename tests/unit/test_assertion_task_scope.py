"""Fresh task-scope admission, preserving real task kind and strict sources."""

from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
import pytest

from conversation.task_kind import classify
from generation import assertion_task_scope as scope
from generation import assertion_bounded_revision_v1 as revision
from generation import assertion_reselection_v1 as legacy
from generation import assertion_provenance_v1 as assertions


def context(question="Compare copper and aluminium."):
    return {
        "task_id": "authored-task",
        "task_version": 1,
        "task_revision": 1,
        "exposure_epoch": 0,
        "task_type": classify(question),
        "question": question,
        "current_problem": question,
        "current_request": question,
        "teaching_mode": "direct",
        "help_level": 0,
        "turn_role": "user_question",
        "pending_tutor_question_id": None,
        "pending_tutor_question": None,
        "pending_tutor_question_version": 0,
        "pending_validation_id": None,
        "pending_validation_version": 0,
        "expected_response_kind": None,
        "current_step": 1,
        "learner_attempt": None,
        "last_attempt_evaluation": None,
        "requested_help": "auto",
        "continuing": False,
        "requirements": {"original_question": question},
        "delivered_turns": [],
        "disclosure_events": [],
        "policy_version": "learning_task_v3",
        "attempt_history": [],
    }


def request(teaching):
    from generation.types import GenerationRequest, ModelConfig

    return GenerationRequest(
        request_id="authored-request",
        mode="interactive_chat",
        condition="E1",
        question=teaching["question"],
        config=ModelConfig(
            provider="local", model="authored-no-network", base_url="http://127.0.0.1:9/v1"
        ),
        teaching_context=teaching,
        history=[],
        profile=None,
        verification_mode="verified",
    )


@pytest.mark.parametrize(
    "question,kind",
    [
        ("Compare copper and aluminium.", "concept_comparison"),
        ("What is the difference between evaporation and condensation?", "concept_comparison"),
        ("Calculate the energy for 2 kg of material.", "simple_calculation"),
        ("How many moles are in 4 grams?", "simple_calculation"),
        ("Explain diffusion.", "process_reasoning"),
        ("Define pressure.", "process_reasoning"),
    ],
)
def test_preserved_native_classification(question, kind):
    assert classify(question) == kind


@pytest.mark.parametrize(
    "question", ["Compare copper and aluminium.", "Calculate the distance after 3 seconds."]
)
def test_opt_in_scope_keeps_original_kind_question_and_legacy_boundary(question):
    original = context(question)
    before = deepcopy(original)
    assert scope.freeze(original, enabled=False) == original
    marked = scope.freeze(original, enabled=True)
    assert original == before and marked["task_type"] == before["task_type"]
    assert marked["question"] == question and scope.valid(marked)
    req = request({**marked, "verification_mode": "verified"})
    before_hash = revision.request_sha256(req)
    assert revision.context_free(req)
    assert revision.request_sha256(req) == before_hash
    assert not legacy.context_free(req)
    # Even without verified metadata, old source-reselection stays ineligible.
    assert not legacy.context_free(replace(req, teaching_context=marked))


@pytest.mark.parametrize(
    "field,value",
    [
        ("task_version", 2),
        ("task_revision", 2),
        ("exposure_epoch", 1),
        ("help_level", 1),
        ("current_step", 2),
        ("continuing", True),
        ("turn_role", "learner_attempt"),
        ("teaching_mode", "hint"),
        ("requested_help", "continue"),
        ("pending_tutor_question", "Authored question"),
        ("pending_tutor_question_version", 1),
        ("pending_validation_id", "authored"),
        ("learner_attempt", "authored"),
        ("last_attempt_evaluation", {}),
        ("delivered_turns", [{}]),
        ("disclosure_events", [{}]),
        ("attempt_history", [{}]),
        ("current_problem", "Different question"),
        ("current_request", "Different question"),
        ("task_type", "simple_calculation"),
        ("policy_version", "unknown"),
        ("task_id", ""),
        ("requirements", {}),
        ("private_extra", "not permitted"),
        ("verification_mode", "fast"),
    ],
)
def test_changed_or_nonfresh_context_cannot_gain_assertion_scope(field, value):
    marked = scope.freeze(context(), enabled=True)
    marked[field] = value
    assert not scope.valid(marked)
    assert not scope.permitted(marked)
    assert not revision.context_free(request(marked))


@pytest.mark.parametrize(
    "fault",
    ["marker_hash", "marker_version", "marker_kind", "missing_marker", "extra_marker_field"],
)
def test_marker_is_exact_and_server_derived(fault):
    marked = scope.freeze(context(), enabled=True)
    if fault == "missing_marker":
        marked.pop(scope.KEY)
    elif fault == "extra_marker_field":
        marked[scope.KEY]["allow_anything"] = True
    else:
        marked[scope.KEY][
            {
                "marker_hash": "question_sha256",
                "marker_version": "version",
                "marker_kind": "task_type",
            }[fault]
        ] = "changed"
    assert not scope.valid(marked)
    assert not revision.context_free(request(marked))


@pytest.mark.parametrize(
    "field,value",
    [
        ("history", [{"role": "user", "content": "prior"}]),
        ("summary", "prior"),
        ("memory_context", {"private": "value"}),
        ("reading_context", {"selection": "value"}),
        ("profile", {"use_profile": True, "profile": {"goal": "private"}}),
    ],
)
def test_scope_never_authorizes_private_context(field, value):
    req = request(scope.freeze(context(), enabled=True))
    setattr(req, field, value)
    assert not revision.context_free(req)


def test_submission_and_consumer_keep_strict_contract_requirements():
    marked = scope.freeze(context(), enabled=True)
    settings = SimpleNamespace(
        chat_joint_checker_policy="typed_joint_v5", chat_source_relation_policy="off"
    )
    fields = assertions.submission_fields(
        settings,
        answer_mode="textbook",
        teaching=marked,
        reading_context=None,
        provider="local",
        checker_provider="local",
    )
    assert fields == {"assertion_source_policy": assertions.POLICY}
    req = request(marked)
    req.mode = "interactive_chat"
    req.condition = "E1"
    req.answer_mode = "textbook"
    req.reliability_policy = "evidence_reliability_v5"
    req.joint_checker_policy = "typed_joint_v5"
    req.assertion_source_policy = assertions.POLICY
    assert assertions.eligible(req, {"teaching_mode": "direct", "online_check": True})
    req.source_relation_policy = "different-contract"
    with pytest.raises(ValueError, match="INCOMPATIBLE"):
        assertions.eligible(req, {"teaching_mode": "direct", "online_check": True})
