"""Fresh compact snapshot selection and immutable replay; no external transport."""

from copy import deepcopy
from pathlib import Path
import socket
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from app.core.config import Settings
from app.modules.answering import service
from app.modules.answering.models import AnswerRequest, Job
from contracts.models import ChatMessageCreate
from generation import checker_claim_spans_v1 as dispatch
from generation.adapters import LLMAdapter
from generation.repair_citation_coordination_v4 import validate_request as validate_repair
from generation.types import failure
from test_retry_hint_capability209 import pending_request
import test_retry_hint_capability209 as retry_fixtures


@pytest.fixture
def scope():
    yield from retry_fixtures.scope.__wrapped__()


V2 = "asserted_support_anchors_v2"
V3 = "asserted_support_anchors_v3"
DIRECT = {"teaching_mode": "direct", "turn_role": "user_question"}


@pytest.fixture(autouse=True)
def offline_only(monkeypatch):
    attempts = []

    def denied(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("Phase213 allows only in-memory SQLite and local code")

    for name in ("connect", "connect_ex"):
        monkeypatch.setattr(socket.socket, name, denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)
    monkeypatch.setattr(LLMAdapter, "_call", denied)
    root = Path(__file__).parents[2].resolve()
    for module in (service, dispatch):
        assert Path(module.__file__).resolve().is_relative_to(root)
    yield
    assert not attempts


def select_policy(*, setting=V3, settings_changes=None, **changes):
    config = SimpleNamespace(
        **{
            "chat_checker_claim_policy": setting,
            "chat_joint_checker_policy": "typed_joint_v5",
            "chat_source_relation_policy": "off",
            "chat_checker_schema_policy": None,
            "chat_checker_output_policy": None,
            **(settings_changes or {}),
        }
    )
    return dispatch.submission_policy(
        config,
        **{
            "answer_mode": "textbook",
            "verification_mode": "verified",
            "teaching_context": deepcopy(DIRECT),
            **changes,
        },
    )


def snapshot_view(req):
    return SimpleNamespace(
        **{
            **req.command,
            "mode": req.mode,
            "reading_context": req.command.get("reading_context"),
            "assertion_source_policy": req.command.get("assertion_source_policy"),
            "checker_schema_policy": req.command.get("checker_schema_policy"),
            "checker_output_policy": req.command.get("checker_output_policy"),
        }
    )


def test_experimental_compact_selection_requires_an_actual_ordinary_scope():
    assert Settings.model_fields["chat_checker_claim_policy"].default is None
    assert select_policy() == V3


@pytest.mark.parametrize(
    "changes",
    [
        {"teaching_context": None},
        {"teaching_context": {"teaching_mode": "hint", "turn_role": "user_question"}},
        {"teaching_context": {"teaching_mode": "direct", "turn_role": "learner_attempt"}},
        {"teaching_context": {**DIRECT, "learner_attempt": "Synthetic attempt"}},
        {"teaching_context": {**DIRECT, "attempt_history": [{"feedback": "Synthetic"}]}},
        {
            "teaching_context": {
                **DIRECT,
                "practice_context": {"version": "practice_tutor_context_v1"},
            }
        },
        {"teaching_context": {**DIRECT, "practice_context": {"version": "unknown"}}},
        {"reading_context": {"source_unit_id": "synthetic"}},
    ],
)
def test_other_previously_supported_branches_freeze_explicit_prior_v2(changes):
    assert select_policy(**changes) == V2


@pytest.mark.parametrize("setting", ["asserted_support_spans_v1", V2, None])
def test_explicit_prior_checker_selection_is_not_promoted(setting):
    assert select_policy(setting=setting) == setting
    assert select_policy(setting=setting, teaching_context=None) == setting


@pytest.mark.parametrize(
    "changes",
    [
        {"verification_mode": "fast"},
        {"answer_mode": "general_knowledge"},
        {"assertion_source_policy": "assertion_source_v1"},
        {"settings_changes": {"chat_joint_checker_policy": "typed_joint_v10"}},
        {"settings_changes": {"chat_source_relation_policy": "source_relation_contract_v2"}},
    ],
)
def test_incompatible_variants_remain_unselected(changes):
    assert select_policy(**changes) is None


def test_actual_native_command_freezes_v3_v4_and_survives_setting_change(scope):
    scope.settings.chat_checker_claim_policy = V3
    body = ChatMessageCreate(content="Compare diffusion and osmosis.", check_answer=True)
    receipt = service.submit_chat(scope.db, scope.settings, scope.actor, "chat", body, "compact")
    req = scope.db.get(AnswerRequest, receipt["request_id"])
    assert req.command["checker_claim_policy"] == V3
    assert req.command["repair_policy"] == "claim_patch_citation_coordination_v4"
    frozen = deepcopy(req.command)
    view = snapshot_view(req)
    assert dispatch.validate_request(view) is True
    assert dispatch.contract(view).POLICY == V3
    assert validate_repair(view) is True
    scope.settings.chat_checker_claim_policy = V2
    assert (
        service.submit_chat(scope.db, scope.settings, scope.actor, "chat", body, "compact")
        == receipt
    )
    assert req.command == frozen
    assert scope.db.scalar(select(func.count()).select_from(Job)) == 1


@pytest.mark.parametrize(
    "checker,repair",
    [
        (None, "claim_patch_repair_v3"),
        (V2, "claim_patch_repair_v3"),
        (V2, "claim_patch_citation_coordination_v4"),
        (V3, "claim_patch_citation_coordination_v4"),
    ],
)
def test_frozen_legacy_and_new_retry_never_reselect_current_defaults(scope, checker, repair):
    req, job = pending_request(scope)
    req.command = {**req.command, "repair_policy": repair}
    if checker is not None:
        req.command = {**req.command, "checker_claim_policy": checker}
    scope.db.commit()
    frozen = deepcopy(req.command)
    service.fail_job(
        scope.db, job, failure("PROVIDER_TIMEOUT", "Synthetic transient", retryable=True)
    )
    scope.db.commit()
    service.retry(scope.db, scope.actor, req.id, "retry")
    assert req.command == frozen
    assert req.command.get("checker_claim_policy") == checker
    assert scope.db.scalar(select(func.count()).select_from(Job)) == 2
