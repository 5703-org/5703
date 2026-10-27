"""New admission and immutable legacy execution, with no provider/network I/O."""

from pathlib import Path
from copy import deepcopy
import json, pytest
from sqlalchemy import select
from app.modules.answering import service
from app.modules.answering.models import AnswerRequest, Job, Snapshot
from app.modules.knowledge.models import CorpusRelease, ActiveCorpus
from contracts.models import ChatMessageCreate
from conversation import reference_ownership, query_v25
from test_retry_hint_capability209 import no_external_io, scope as scope_fixture
from test_reference_ownership import POSITIVE, AMBIGUOUS, HIST

H = Path(__file__).resolve().parent


@pytest.fixture
def scope():
    yield from scope_fixture.__wrapped__()


@pytest.mark.parametrize("question", POSITIVE + AMBIGUOUS + ["Why does it expand?"])
@pytest.mark.parametrize("legacy_saved", [False, True])
def test_native_frozen_admission(scope, monkeypatch, tmp_path, question, legacy_saved):
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
    receipt = service.submit_chat(
        scope.db,
        scope.settings,
        scope.actor,
        "chat",
        ChatMessageCreate(content=question, use_profile=False),
        "one-request",
    )
    scope.db.commit()
    req = scope.db.get(AnswerRequest, receipt["request_id"])
    assert req.command["current_reference_policy"] == reference_ownership.POLICY
    if legacy_saved:
        # Authored pre-upgrade command shape: absence is an immutable legacy identity.
        command = deepcopy(req.command)
        command.pop("current_reference_policy")
        command.pop("targeted_query_encoding_policy")
        req.command = command
    snap = scope.db.get(Snapshot, req.context_snapshot_id)
    v = deepcopy(snap.payload)
    v["messages"] = deepcopy(HIST)
    snap.payload = v
    snap.content_hash = service.digest(v)
    scope.db.commit()
    frozen = deepcopy(req.command)
    job = scope.db.scalar(select(Job).where(Job.request_id == req.id))
    job.state = "running"
    job.execution_token = "offline"
    scope.db.commit()
    scope.settings.experimental_current_reference_enabled = True
    captured = {}
    retrieved = []
    monkeypatch.setattr(service, "retrieve", lambda *a, **kw: retrieved.append(a[1]) or [])
    monkeypatch.setattr(service, "resolve_device", lambda *a, **kw: "cpu")

    class Capture(BaseException):
        pass

    def intercept(**kw):
        captured.update(kw)
        raise Capture()

    monkeypatch.setattr(service, "GenerationRequest", intercept)
    with pytest.raises(Capture):
        service.execute_answer(scope.db.get_bind(), scope.settings, job.id, job.execution_token)
    p = captured["prepared_query"]
    if legacy_saved:
        assert p == query_v25.prepare_query(question, HIST).model_dump()
    elif question in POSITIVE:
        assert (
            not p["needs_clarification"]
            and p["standalone_query"] == question
            and not p["referenced_message_ids"]
        )
        assert retrieved and all("ocean tides" not in str(q).lower() for q in retrieved)
        assert captured["understanding"]["requirement_source_text"] == question
    elif question in AMBIGUOUS:
        assert (
            p["needs_clarification"]
            and p["standalone_query"] is None
            and not p["referenced_message_ids"]
            and not retrieved
        )
    else:
        assert (
            p == query_v25.prepare_query(question, HIST).model_dump()
            and p["referenced_message_ids"]
        )
    scope.db.expire_all()
    assert scope.db.get(AnswerRequest, req.id).command == frozen
    out = tmp_path / "native-after"
    out.mkdir(exist_ok=True)
    import hashlib

    name = hashlib.sha256(question.encode()).hexdigest()[:12] + (
        "-legacy" if legacy_saved else "-new"
    )
    (out / (name + ".json")).write_text(
        json.dumps(
            {
                "question": question,
                "legacy_saved": legacy_saved,
                "frozen_policy": frozen.get("current_reference_policy"),
                "prepared": p,
                "retrieved": retrieved,
                "understanding": captured.get("understanding"),
                "provider_requests": 0,
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )


def test_owner_and_session_admission_no_global_context(scope):
    from app.modules.learning.models import ChatSession
    from app.modules.identity.models import User
    from app.core.exceptions import AppError

    scope.db.add(
        User(
            id="other",
            email="other@fixture.invalid",
            hashed_password="unused",
            role_id=1,
            workspace_id="workspace",
        )
    )
    scope.db.add_all(
        [
            ChatSession(id="own-two", user_id="owner", workspace_id="workspace", title="Second"),
            ChatSession(
                id="other-chat",
                user_id="other",
                workspace_id="workspace",
                title="Other",
            ),
        ]
    )
    scope.db.commit()
    with pytest.raises(AppError):
        service.submit_chat(
            scope.db,
            scope.settings,
            scope.actor,
            "other-chat",
            ChatMessageCreate(content=POSITIVE[0]),
            "blocked",
        )
    one = service.submit_chat(
        scope.db,
        scope.settings,
        scope.actor,
        "chat",
        ChatMessageCreate(content=POSITIVE[0]),
        "first",
    )
    scope.db.commit()
    two = service.submit_chat(
        scope.db,
        scope.settings,
        scope.actor,
        "own-two",
        ChatMessageCreate(content="Why does it expand?"),
        "second",
    )
    scope.db.commit()
    first = scope.db.get(AnswerRequest, one["request_id"])
    second = scope.db.get(AnswerRequest, two["request_id"])
    assert (
        first.session_id != second.session_id
        and first.context_snapshot_id != second.context_snapshot_id
    )
    context = scope.db.get(Snapshot, second.context_snapshot_id).payload
    assert not context["messages"]
    prepared = query_v25.prepare_query(second.command["question"], context["messages"]).model_dump()
    guarded, _ = reference_ownership.apply(prepared, second.command["current_reference_policy"])
    assert guarded["needs_clarification"] and not guarded["referenced_message_ids"]
