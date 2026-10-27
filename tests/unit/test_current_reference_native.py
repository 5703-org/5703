"""Saved native commands/worker entry; synthetic SQLite, no retrieval/model I/O."""

from copy import deepcopy
import pytest
from sqlalchemy import select
from app.modules.answering import service
from app.modules.answering.models import AnswerRequest, Job
from app.modules.knowledge.models import ActiveCorpus, CorpusRelease
from contracts.models import ChatMessageCreate
from conversation import current_reference as cr, reference_ownership
from test_retry_hint_capability209 import no_external_io  # noqa: F401
from test_retry_hint_capability209 import scope as scope_fixture


@pytest.fixture
def scope():
    yield from scope_fixture.__wrapped__()


WATER = "Using Chemistry 2e Table 9.2, compare the vapor pressure of liquid water at 20 degrees Celsius and at 40 degrees Celsius. Give both pressures with their units, explicitly pair each pressure with its temperature, and state which is higher. These are water-vapor pressures, not the total atmospheric pressure."
ACID = "Using Chemistry 2e Table 14.2 and its two numbered notes, compare the pH of the HCl and CH3CO2H titrations after 25.0 mL of NaOH has been added. Give both pH values and which is higher. State the initial volume and concentration of each acid, the concentration of the NaOH, and the amount of NaOH added in moles at that table row. Do not generalize these pH values to all acid concentrations."


@pytest.mark.parametrize(
    "question,enabled,expected",
    [
        (WATER, False, True),
        (WATER, True, True),
        (ACID, False, True),
        (ACID, True, True),
        ("Compare copper and aluminium. Why is it denser?", True, False),
        (
            "Give both frequencies with their units. Pair each frequency with its amplitude.",
            True,
            True,
        ),
    ],
)
def test_saved_policy_controls_original_question(scope, monkeypatch, question, enabled, expected):
    CorpusRelease.__table__.create(scope.db.get_bind())
    scope.db.add(
        CorpusRelease(
            id="synthetic-public",
            name="Authored source placeholder",
            state="ready",
            configuration={},
        )
    )
    scope.db.add(ActiveCorpus(id=1, release_id="synthetic-public"))
    scope.db.commit()
    scope.settings.experimental_current_reference_enabled = enabled
    scope.settings.chat_query_preparation_policy = "anchored_reference_v25"
    receipt = service.submit_chat(
        scope.db,
        scope.settings,
        scope.actor,
        "chat",
        ChatMessageCreate(content=question, use_profile=False),
        "authored-current-reference",
    )
    scope.db.commit()
    req = scope.db.get(AnswerRequest, receipt["request_id"])
    frozen = deepcopy(req.command)
    assert frozen.get("current_reference_policy") == (
        cr.POLICY if enabled else reference_ownership.POLICY
    )
    job = scope.db.scalar(select(Job).where(Job.request_id == req.id))
    job.state = "running"
    job.execution_token = "zero-network"
    scope.db.commit()
    scope.settings.experimental_current_reference_enabled = not enabled
    retrieved, captured = [], {}
    monkeypatch.setattr(service, "retrieve", lambda *a, **kw: retrieved.append(a[1]) or [])
    monkeypatch.setattr(service, "resolve_device", lambda *a, **kw: "cpu")

    class Captured(BaseException):
        pass

    def intercept(**kw):
        captured.update(kw)
        raise Captured()

    monkeypatch.setattr(service, "GenerationRequest", intercept)
    with pytest.raises(Captured):
        service.execute_answer(scope.db.get_bind(), scope.settings, job.id, job.execution_token)
    assert captured["prepared_query"]["needs_clarification"] is (not expected)
    assert bool(retrieved) is expected
    # Empty retrieval spy: this proves entry, not real ranking or source packing.
    if expected:
        assert captured["prepared_query"]["standalone_query"] == question
        assert captured["understanding"]["requirement_source_text"] == question
        assert captured["prepared_query"]["referenced_message_ids"] == []
    if enabled and question == WATER:
        assert captured["understanding"]["current_message_reference_audit"]["eligible"]
    scope.db.expire_all()
    assert scope.db.get(AnswerRequest, req.id).command == frozen


def test_default_off(scope):
    assert scope.settings.experimental_current_reference_enabled is False


@pytest.mark.parametrize(
    "question",
    [
        WATER,
        "Give both voltages with their units. Pair each voltage with its frequency.",
    ],
)
def test_current_question_does_not_continue_unrelated_task(scope, question):
    from app.modules.answering.models import Message
    from app.modules.learning_state.models import LearningTask
    from app.modules.learning.models import ChatSession
    from app.modules.learning_state import tasks

    old = Message(
        id="old-question",
        session_id="chat",
        sequence=1,
        role="user",
        content="Explain ocean tides.",
        state="answered",
    )
    scope.db.add(old)
    scope.db.flush()
    task = LearningTask(
        id="old-task",
        owner_id="owner",
        session_id="chat",
        initial_message_id=old.id,
        question=old.content,
        task_type="process_reasoning",
        teaching_mode="direct",
        help_level=0,
        requirements={"original_question": old.content},
    )
    scope.db.add(task)
    current = Message(
        id="new-question",
        session_id="chat",
        sequence=2,
        role="user",
        content=question,
        state="queued",
    )
    scope.db.add(current)
    scope.db.flush()
    context = {"messages": [{"id": old.id, "role": "user", "content": old.content}]}
    result = tasks.resolve_task(
        scope.db,
        scope.actor,
        scope.db.get(ChatSession, "chat"),
        current,
        ChatMessageCreate(content=question),
        context,
        current_reference_policy=cr.POLICY,
    )
    assert result["continuing"] is False
    assert result["current_problem"] == question
    assert result["task_id"] != task.id
    assert task.state == "completed"
