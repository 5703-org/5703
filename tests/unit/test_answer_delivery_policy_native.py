"""Frozen native command and job identity; no external transport."""

from copy import deepcopy
from dataclasses import replace
import pytest
from sqlalchemy import select
from app.modules.answering import service
from app.modules.answering.models import AnswerRequest, Job
from app.modules.model_settings import service as models
from contracts.models import ChatMessageCreate
from generation.types import GenerationRequest, ModelConfig
from generation import answer_delivery_v1 as audit, answer_delivery_target_v1 as target
from test_retry_hint_capability209 import no_external_io, scope as scope_fixture
from test_current_reference_native import WATER


@pytest.fixture
def scope():
    yield from scope_fixture.__wrapped__()


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("policy", [audit.POLICY, target.POLICY])
def test_saved_policy_and_trusted_identity_survive_live_setting_changes(
    scope, monkeypatch, enabled, policy
):
    config = ModelConfig(
        provider="local",
        model="offline-native-audit",
        base_url="http://127.0.0.1:9/v1",
        window_tokens=32768,
        max_tokens=1024,
        tokenizer_provider="estimate",
    )
    monkeypatch.setattr(models, "resolve_active_model_config", lambda *a: config)
    monkeypatch.setattr(
        models, "resolve_active_checker_model_config", lambda *a: replace(config, max_tokens=4096)
    )
    scope.settings.experimental_assertion_revision_enabled = True
    scope.settings.experimental_current_reference_enabled = True
    scope.settings.experimental_answer_delivery_audit_enabled = enabled
    scope.settings.experimental_answer_delivery_audit_policy = policy
    scope.settings.chat_query_preparation_policy = "anchored_reference_v25"
    receipt = service.submit_chat(
        scope.db,
        scope.settings,
        scope.actor,
        "chat",
        ChatMessageCreate(content=WATER, check_answer=True, use_profile=False),
        "audit-admission",
    )
    scope.db.commit()
    req = scope.db.get(AnswerRequest, receipt["request_id"])
    saved = deepcopy(req.command)
    assert saved.get("answer_delivery_policy") == (policy if enabled else None)
    job = scope.db.scalar(select(Job).where(Job.request_id == req.id))
    job.state = "running"
    job.execution_token = "offline"
    scope.db.commit()
    scope.settings.experimental_answer_delivery_audit_enabled = not enabled
    scope.settings.experimental_answer_delivery_audit_policy = target.POLICY if policy == audit.POLICY else audit.POLICY
    # Reload the persisted command before the recovered worker reads it.
    scope.db.expire_all()
    replay = service.submit_chat(
        scope.db, scope.settings, scope.actor, "chat",
        ChatMessageCreate(content=WATER, check_answer=True, use_profile=False),
        "audit-admission",
    )
    assert replay["request_id"] == receipt["request_id"]
    assert scope.db.get(AnswerRequest, receipt["request_id"]).command == saved
    monkeypatch.setattr(service, "resolve_device", lambda *a: "cpu")
    monkeypatch.setattr(service, "retrieve", lambda *a, **kw: [])
    captured = {}

    class Captured(BaseException):
        pass

    def capture(**kwargs):
        captured["request"] = GenerationRequest(**kwargs)
        raise Captured()

    monkeypatch.setattr(service, "GenerationRequest", capture)
    with pytest.raises(Captured):
        service.execute_answer(scope.db.get_bind(), scope.settings, job.id, "offline")
    native = captured["request"]
    assert native.answer_delivery_policy == (policy if enabled else None)
    if enabled:
        assert native.answer_delivery_identity == {
            "owner": req.owner_id,
            "session": req.session_id,
            "request": req.id,
            "job": job.id,
        }
    scope.db.expire_all()
    assert scope.db.get(AnswerRequest, req.id).command == saved
