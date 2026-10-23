"""Native command/worker scope, synthetic SQLite and no provider dispatch."""

from copy import deepcopy
from dataclasses import replace
import pytest
from sqlalchemy import select
from app.modules.answering import service
from app.modules.answering.models import AnswerRequest, Job
from app.modules.model_settings import service as models
from contracts.models import ChatMessageCreate
from generation.types import GenerationRequest, ModelConfig
from generation import assertion_task_scope as scope_policy
from generation import assertion_bounded_revision_v1 as revision
from generation import assertion_provenance_v1 as assertions
from test_retry_hint_capability209 import no_external_io  # noqa: F401
from test_retry_hint_capability209 import scope as scope_fixture
from test_current_reference_native import WATER, ACID


@pytest.fixture
def scope():
    yield from scope_fixture.__wrapped__()


@pytest.mark.parametrize(
    "question,kind",
    [
        (WATER, "concept_comparison"),
        (ACID, "concept_comparison"),
        (
            "Calculate the force needed for 2 kg at 3 metres per second squared.",
            "simple_calculation",
        ),
    ],
)
@pytest.mark.parametrize("enabled", [False, True])
def test_real_task_type_preserved_and_scope_frozen(scope, monkeypatch, question, kind, enabled):
    config = ModelConfig(
        provider="local",
        model="authored-offline-scope",
        base_url="http://127.0.0.1:9/v1",
        window_tokens=32768,
        max_tokens=1024,
        tokenizer_provider="estimate",
    )
    monkeypatch.setattr(models, "resolve_active_model_config", lambda *a: config)
    monkeypatch.setattr(
        models, "resolve_active_checker_model_config", lambda *a: replace(config, max_tokens=4096)
    )
    scope.settings.experimental_assertion_revision_enabled = enabled
    scope.settings.experimental_current_reference_enabled = True
    scope.settings.chat_query_preparation_policy = "anchored_reference_v25"
    receipt = service.submit_chat(
        scope.db,
        scope.settings,
        scope.actor,
        "chat",
        ChatMessageCreate(content=question, check_answer=True, use_profile=False),
        "authored-scope",
    )
    scope.db.commit()
    req = scope.db.get(AnswerRequest, receipt["request_id"])
    saved = deepcopy(req.command)
    assert saved["teaching_context"]["task_type"] == kind
    assert saved["teaching_context"]["question"] == question
    assert (scope_policy.KEY in saved["teaching_context"]) is enabled
    assert saved.get("assertion_source_policy") == (assertions.POLICY if enabled else None)
    job = scope.db.scalar(select(Job).where(Job.request_id == req.id))
    job.state = "running"
    job.execution_token = "zero-network"
    scope.db.commit()
    scope.settings.experimental_assertion_revision_enabled = not enabled
    monkeypatch.setattr(service, "resolve_device", lambda *a: "cpu")
    monkeypatch.setattr(service, "retrieve", lambda *a, **kw: [])
    captured = {}

    class Captured(BaseException):
        pass

    def capture(**kw):
        captured["request"] = GenerationRequest(**kw)
        raise Captured()

    monkeypatch.setattr(service, "GenerationRequest", capture)
    with pytest.raises(Captured):
        service.execute_answer(scope.db.get_bind(), scope.settings, job.id, job.execution_token)
    native = captured["request"]
    assert native.teaching_context["task_type"] == kind
    assert native.question == question
    assert revision.context_free(native) is enabled
    if enabled:
        assert assertions.eligible(native, {"teaching_mode": "direct", "online_check": True})
    scope.db.expire_all()
    assert scope.db.get(AnswerRequest, req.id).command == saved
