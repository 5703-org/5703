"""Fresh producer selection and immutable replay; no external transport or database."""

from copy import deepcopy
from pathlib import Path
import socket
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from app.modules.answering import service
from app.modules.answering.models import AnswerRequest, Job
from contracts.models import ChatMessageCreate
from generation.adapters import LLMAdapter
from generation.repair_citation_coordination_v4 import validate_request
from generation.types import failure
from test_retry_hint_capability209 import pending_request
import test_retry_hint_capability209 as retry_fixtures


@pytest.fixture
def scope():
    yield from retry_fixtures.scope.__wrapped__()


@pytest.fixture(autouse=True)
def offline_only(monkeypatch):
    attempts = []

    def denied(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("Phase212 producer controls allow only in-memory SQLite")

    monkeypatch.setattr(socket, "getaddrinfo", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)
    monkeypatch.setattr(LLMAdapter, "_call", denied)
    root = Path(__file__).parents[2].resolve()
    assert Path(service.__file__).resolve().is_relative_to(root)
    yield
    assert not attempts


def select_policy(**changes):
    return service._repair_submission_policy(
        **{
            "answer_mode": "textbook",
            "verification_mode": "verified",
            "checker_claim_policy": "asserted_support_anchors_v2",
            "teaching": {"teaching_mode": "direct", "turn_role": "user_question"},
            **changes,
        }
    )


@pytest.mark.parametrize(
    "changes,expected",
    [
        ({}, "claim_patch_citation_coordination_v4"),
        ({"verification_mode": "fast"}, "claim_patch_repair_v3"),
        ({"verification_mode": None}, "claim_patch_repair_v3"),
        ({"answer_mode": "general_knowledge"}, "claim_patch_repair_v3"),
        ({"checker_claim_policy": "asserted_support_spans_v1"}, "claim_patch_repair_v3"),
        ({"checker_claim_policy": None}, "claim_patch_repair_v3"),
        ({"teaching": {"teaching_mode": "hint"}}, "claim_patch_repair_v3"),
        ({"reading_context": {"source_unit_id": "synthetic"}}, "claim_patch_repair_v3"),
        (
            {
                "teaching": {
                    "teaching_mode": "direct",
                    "practice_context": {"version": "practice_tutor_context_v1"},
                }
            },
            "claim_patch_repair_v3",
        ),
        (
            {
                "teaching": {
                    "teaching_mode": "hint",
                    "practice_context": {"version": "practice_tutor_context_v1"},
                }
            },
            "practice_hint_repair_v5",
        ),
        ({"teaching": None}, "claim_patch_repair_v3"),
        (
            {"teaching": {"teaching_mode": "direct", "turn_role": "unknown"}},
            "claim_patch_repair_v3",
        ),
        (
            {"teaching": {"teaching_mode": "direct", "turn_role": "learner_attempt"}},
            "claim_patch_repair_v3",
        ),
        (
            {
                "teaching": {
                    "teaching_mode": "direct",
                    "turn_role": "user_question",
                    "learner_attempt": "Synthetic attempt",
                }
            },
            "claim_patch_repair_v3",
        ),
        (
            {
                "teaching": {
                    "teaching_mode": "direct",
                    "turn_role": "user_question",
                    "attempt_history": [{"feedback": "Synthetic"}],
                }
            },
            "claim_patch_repair_v3",
        ),
        (
            {
                "teaching": {
                    "teaching_mode": "direct",
                    "turn_role": "user_question",
                    "practice_context": {"version": "unknown"},
                }
            },
            "claim_patch_repair_v3",
        ),
    ],
)
def test_only_fresh_ordinary_checked_anchor_branch_selects_coordination(changes, expected):
    assert select_policy(**changes) == expected


def test_actual_submission_freezes_new_policy_and_idempotent_replay_keeps_it(scope):
    scope.settings.chat_checker_claim_policy = "asserted_support_anchors_v2"
    body = ChatMessageCreate(content="Explain diffusion.", check_answer=True)
    receipt = service.submit_chat(scope.db, scope.settings, scope.actor, "chat", body, "new")
    req = scope.db.get(AnswerRequest, receipt["request_id"])
    assert req.command["repair_policy"] == "claim_patch_citation_coordination_v4"
    assert req.command["checker_claim_policy"] == "asserted_support_anchors_v2"
    assert req.command["verification_mode"] == "verified"
    assert (
        validate_request(
            SimpleNamespace(
                **{
                    key: req.command[key]
                    for key in (
                        "repair_policy",
                        "answer_mode",
                        "verification_mode",
                        "reliability_policy",
                        "joint_checker_policy",
                        "checker_claim_policy",
                        "source_relation_policy",
                        "teaching_context",
                    )
                },
                mode=req.mode,
                assertion_source_policy=req.command.get("assertion_source_policy"),
                reading_context=req.command.get("reading_context"),
            )
        )
        is True
    )
    saved = deepcopy(req.command)
    scope.settings.chat_checker_claim_policy = None
    assert (
        service.submit_chat(scope.db, scope.settings, scope.actor, "chat", body, "new") == receipt
    )
    assert req.command == saved
    assert scope.db.scalar(select(func.count()).select_from(Job)) == 1


def test_actual_fast_submission_keeps_previous_repair_policy(scope):
    body = ChatMessageCreate(content="Explain diffusion.", check_answer=False)
    receipt = service.submit_chat(scope.db, scope.settings, scope.actor, "chat", body, "fast")
    req = scope.db.get(AnswerRequest, receipt["request_id"])
    assert req.command["repair_policy"] == "claim_patch_repair_v3"
    assert req.command["checker_claim_policy"] is None
    assert req.command["verification_mode"] == "fast"


@pytest.mark.parametrize(
    "field,value",
    [
        ("chat_joint_checker_policy", "typed_joint_v10"),
        ("chat_source_relation_policy", "source_relation_contract_v2"),
    ],
)
def test_actual_configurable_checker_variant_does_not_freeze_incompatible_v4(scope, field, value):
    setattr(scope.settings, field, value)
    body = ChatMessageCreate(content="Explain diffusion.", check_answer=True)
    receipt = service.submit_chat(scope.db, scope.settings, scope.actor, "chat", body, "variant")
    req = scope.db.get(AnswerRequest, receipt["request_id"])
    assert req.command["checker_claim_policy"] is None
    assert req.command["repair_policy"] == "claim_patch_repair_v3"


def test_old_frozen_v3_retry_is_not_reselected_from_current_settings(scope):
    req, job = pending_request(scope)
    req.command = {
        **req.command,
        "repair_policy": "claim_patch_repair_v3",
        "checker_claim_policy": "asserted_support_spans_v1",
    }
    scope.db.commit()
    saved = deepcopy(req.command)
    service.fail_job(
        scope.db, job, failure("PROVIDER_TIMEOUT", "Synthetic timeout", retryable=True)
    )
    scope.db.commit()
    service.retry(scope.db, scope.actor, req.id, "old-retry")
    assert req.command == saved
    assert scope.db.scalar(select(func.count()).select_from(Job)) == 2
