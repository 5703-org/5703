"""Native immutable submission and worker dispatch; SQLite and no provider calls."""

from copy import deepcopy

import pytest
from sqlalchemy import select

from app.modules.answering import service
from app.modules.answering.models import AnswerRequest, Job
from app.modules.knowledge.models import ActiveCorpus, CorpusRelease
from contracts.models import ChatMessageCreate
from test_retry_hint_capability209 import no_external_io  # noqa: F401
from test_retry_hint_capability209 import scope as scope_fixture


@pytest.fixture
def scope():
    yield from scope_fixture.__wrapped__()


QUESTIONS = [
    "Using Chemistry 2e Table 16.2, compare the standard entropies of liquid methanol and liquid ethanol. Give both values with the full units, identify the larger value, and state the temperature and measured pressure specified by the table. Distinguish the measured pressure from the current standard-pressure convention mentioned in its note.",
    "Using Table 7.3, compare the recorded speeds. State the measurement conditions specified in its footnote.",
    "Using Ecology Figure 8.4, describe the plotted trend. Explain the uncertainty convention mentioned in its caption.",
]


@pytest.mark.parametrize("question", QUESTIONS)
@pytest.mark.parametrize(
    "policy,expected",
    [
        ("anchored_reference_v25", False),
        ("anchored_reference_v26", False),
        ("anchored_reference_v27", False),
        ("anchored_reference_v28", True),
    ],
)
def test_saved_policy_drives_native_worker_and_retrieval(
    scope, monkeypatch, question, policy, expected
):
    engine = scope.db.get_bind()
    CorpusRelease.__table__.create(engine)
    scope.db.add(
        CorpusRelease(id="public-fixture", name="Authored", state="ready", configuration={})
    )
    scope.db.add(ActiveCorpus(id=1, release_id="public-fixture"))
    scope.db.commit()
    scope.settings.chat_query_preparation_policy = policy
    receipt = service.submit_chat(
        scope.db,
        scope.settings,
        scope.actor,
        "chat",
        ChatMessageCreate(content=question, check_answer=False, use_profile=False),
        "local-reference",
    )
    scope.db.commit()
    request = scope.db.get(AnswerRequest, receipt["request_id"])
    # This test exercises an already saved pre-ownership-policy command.
    # New admissions have separate native tests; removing this new field here
    # recreates the immutable historical command shape, not product behavior.
    if policy == "anchored_reference_v25":
        legacy_command = deepcopy(request.command)
        legacy_command.pop("current_reference_policy")
        legacy_command.pop("targeted_query_encoding_policy")
        request.command = legacy_command
        scope.db.commit()
    frozen = deepcopy(request.command)
    assert frozen["preparation_version"] == "conversation_preparer_" + policy.rsplit("_", 1)[1]
    assert frozen["requirements_version"] == "question_requirements_v8"
    job = scope.db.scalar(select(Job).where(Job.request_id == request.id))
    job.state = "running"
    job.execution_token = "local-only"
    scope.db.commit()
    # New settings cannot rewrite an already accepted request.
    scope.settings.chat_query_preparation_policy = "anchored_reference_v25"
    retrieved = []
    monkeypatch.setattr(service, "retrieve", lambda *a, **k: retrieved.append(a[1]) or [])
    monkeypatch.setattr(service, "resolve_device", lambda *a, **k: "cpu")
    captured = {}

    class Captured(BaseException):
        pass

    def intercept(**kwargs):
        captured.update(kwargs)
        raise Captured()

    monkeypatch.setattr(service, "GenerationRequest", intercept)
    with pytest.raises(Captured):
        service.execute_answer(engine, scope.settings, job.id, job.execution_token)
    assert bool(retrieved) is expected
    assert captured["prepared_query"]["needs_clarification"] is (not expected)
    if expected:
        assert captured["prepared_query"]["standalone_query"] == question
        assert captured["understanding"]["requirement_source_text"] == question
        assert "current_source_part_reference_audit" in captured["understanding"]
    scope.db.expire_all()
    assert scope.db.get(AnswerRequest, request.id).command == frozen
