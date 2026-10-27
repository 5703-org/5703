"""Native task and saved worker routing; no external provider or retrieval I/O."""

from copy import deepcopy
import pytest
from sqlalchemy import select
from contracts.models import ChatMessageCreate
from app.modules.answering import service
from app.modules.answering.models import Message, AnswerRequest, Job, Snapshot
from app.modules.learning.models import ChatSession
from app.modules.learning_state.models import LearningTask
from app.modules.learning_state import tasks
from app.modules.knowledge.models import CorpusRelease, ActiveCorpus
from conversation import ordinal_reference, reference_ownership
from test_retry_hint_capability209 import no_external_io, scope as scope_fixture
from test_ordinal_reference import FOLLOW, PAIRS, history


@pytest.fixture
def scope():
    yield from scope_fixture.__wrapped__()


def test_native_task_continues_without_changing_original_problem(scope):
    old = Message(
        id="old-u",
        session_id="chat",
        sequence=1,
        role="user",
        content=PAIRS[0][0],
        state="answered",
    )
    scope.db.add(old)
    scope.db.flush()
    task = LearningTask(
        id="old-task",
        owner_id=scope.actor.id,
        session_id="chat",
        initial_message_id=old.id,
        question=old.content,
        task_type="comparison",
        teaching_mode="direct",
        help_level=0,
        requirements={"original_question": old.content},
    )
    scope.db.add(task)
    msg = Message(
        id="next-u", session_id="chat", sequence=3, role="user", content=FOLLOW, state="queued"
    )
    scope.db.add(msg)
    scope.db.flush()
    result = tasks.resolve_task(
        scope.db,
        scope.actor,
        scope.db.get(ChatSession, "chat"),
        msg,
        ChatMessageCreate(content=FOLLOW),
        {
            "messages": [{**m, "sequence": i + 1} for i, m in enumerate(history())],
            "cutoff_sequence": 2,
        },
        current_reference_policy=reference_ownership.POLICY,
        ordinal_reference_policy=ordinal_reference.POLICY,
    )
    assert result["continuing"] and result["task_id"] == task.id
    assert result["current_problem"] == old.content and result["current_request"] == FOLLOW


@pytest.mark.parametrize("enabled", [True, False])
def test_saved_worker_policy_binds_exact_completed_history(scope, monkeypatch, enabled):
    CorpusRelease.__table__.create(scope.db.get_bind())
    scope.db.add(
        CorpusRelease(id="public", name="Software source", state="ready", configuration={})
    )
    scope.db.add(ActiveCorpus(id=1, release_id="public"))
    scope.db.commit()
    receipt = service.submit_chat(
        scope.db,
        scope.settings,
        scope.actor,
        "chat",
        ChatMessageCreate(content=FOLLOW, use_profile=False),
        "ordinal-native",
    )
    req = scope.db.get(AnswerRequest, receipt["request_id"])
    assert req.command["ordinal_reference_policy"] == ordinal_reference.POLICY
    if not enabled:
        command = deepcopy(req.command)
        command.pop("ordinal_reference_policy")
        req.command = command
    snap = scope.db.get(Snapshot, req.context_snapshot_id)
    value = deepcopy(snap.payload)
    value["messages"] = [{**m, "sequence": i + 1} for i, m in enumerate(history())]
    value["cutoff_sequence"] = 2
    snap.payload = value
    snap.content_hash = service.digest(value)
    job = scope.db.scalar(select(Job).where(Job.request_id == req.id))
    job.state = "running"
    job.execution_token = "ordinal-test"
    scope.db.commit()
    frozen = deepcopy(req.command)
    captured = {}
    retrieved = []
    monkeypatch.setattr(service, "retrieve", lambda *a, **kw: retrieved.append(a[1]) or [])
    monkeypatch.setattr(service, "resolve_device", lambda *a, **kw: "cpu")

    class Capture(BaseException):
        pass

    def capture(**kw):
        captured.update(kw)
        raise Capture()

    monkeypatch.setattr(service, "GenerationRequest", capture)
    with pytest.raises(Capture):
        service.execute_answer(scope.db.get_bind(), scope.settings, job.id, job.execution_token)
    prepared = captured["prepared_query"]
    assert prepared["original_message"] == FOLLOW
    if enabled:
        assert prepared["referenced_message_ids"] == ["u", "a"]
        assert PAIRS[0][0] in prepared["standalone_query"]
        assert captured["understanding"]["ordinal_reference_audit"]["eligible"]
    else:
        assert prepared["standalone_query"] == FOLLOW and not prepared["referenced_message_ids"]
    scope.db.expire_all()
    assert scope.db.get(AnswerRequest, req.id).command == frozen


def test_continuing_native_admission_retains_ordinal_policy(scope, monkeypatch):
    CorpusRelease.__table__.create(scope.db.get_bind())
    scope.db.add(
        CorpusRelease(id="public", name="Software source", state="ready", configuration={})
    )
    scope.db.add(ActiveCorpus(id=1, release_id="public"))
    old = Message(
        id="u", session_id="chat", sequence=1, role="user", content=PAIRS[0][0], state="answered"
    )
    scope.db.add(old)
    scope.db.flush()
    task = LearningTask(
        id="task",
        owner_id=scope.actor.id,
        session_id="chat",
        initial_message_id="u",
        question=old.content,
        task_type="comparison",
        teaching_mode="direct",
        help_level=0,
        requirements={"original_question": old.content},
    )
    scope.db.add(task)
    scope.db.commit()
    rows = [
        {**m, "id": m["message_id"], "session_id": "chat", "state": "answered", "sequence": i + 1}
        for i, m in enumerate(history())
    ]
    monkeypatch.setattr(service, "history_rows", lambda *args: rows)
    receipt = service.submit_chat(
        scope.db,
        scope.settings,
        scope.actor,
        "chat",
        ChatMessageCreate(content=FOLLOW, use_profile=False),
        "ordinal-continuing",
    )
    req = scope.db.get(AnswerRequest, receipt["request_id"])
    assert req.command["teaching_context"]["continuing"]
    assert req.command["ordinal_reference_policy"] == ordinal_reference.POLICY
    assert "current_reference_policy" not in req.command
