"""Actual SQLite submission/retry proof for the disabled experimental policy."""

from copy import deepcopy
import socket

import pytest
from sqlalchemy import func, select

import test_retry_hint_capability209 as fixtures
from app.modules.answering import service
from app.modules.answering.models import AnswerRequest, Job
from contracts.models import ChatMessageCreate
from generation.adapters import LLMAdapter
from generation.requirement_completeness_runtime_v1 import POLICY
from generation.types import failure


@pytest.fixture
def native_scope(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Only in-memory SQLite and local code are allowed")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(LLMAdapter, "_call", denied)
    source = fixtures.scope.__wrapped__()
    value = next(source)
    try:
        yield value
    finally:
        source.close()


@pytest.mark.parametrize(
    "enabled,check,mode,expected",
    [
        (False, False, "textbook", None),
        (True, False, "textbook", POLICY),
        (True, True, "textbook", None),
        (True, False, "general_knowledge", None),
    ],
)
def test_actual_command_selection_and_idempotent_reuse(
    native_scope, enabled, check, mode, expected
):
    v = native_scope
    v.settings.chat_requirement_completeness_policy = POLICY if enabled else None
    body = ChatMessageCreate(
        content="Give the quantity per rotation.", check_answer=check, answer_mode=mode
    )
    result = service.submit_chat(v.db, v.settings, v.actor, "chat", body, "same-request")
    req = v.db.get(AnswerRequest, result["request_id"])
    assert req.command.get("requirement_completeness_policy") == expected
    frozen = deepcopy(req.command)
    v.settings.chat_requirement_completeness_policy = None if enabled else POLICY
    assert service.submit_chat(v.db, v.settings, v.actor, "chat", body, "same-request") == result
    assert req.command == frozen
    assert v.db.scalar(select(func.count()).select_from(Job)) == 1


@pytest.mark.parametrize("policy", [None, POLICY])
def test_retry_preserves_frozen_policy_without_reselection(native_scope, policy):
    v = native_scope
    req, job = fixtures.pending_request(v)
    if policy:
        req.command = {**req.command, "requirement_completeness_policy": policy}
    frozen = deepcopy(req.command)
    v.settings.chat_requirement_completeness_policy = None if policy else POLICY
    service.fail_job(v.db, job, failure("PROVIDER_TIMEOUT", "Synthetic", retryable=True))
    v.db.commit()
    service.retry(v.db, v.actor, req.id, "retry-request")
    assert req.command == frozen
    assert v.db.scalar(select(func.count()).select_from(Job)) == 2
