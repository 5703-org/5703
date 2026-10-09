"""Check actual serializers keep bound repair traces in private draft records."""

from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from contracts.models import AnswerOut
from generation.types import GenerationOutcome

PRIVATE_TRACE = "private-bound-repair-target-span-and-feedback"


def repair_trace():
    return {
        "bound_repair_plan": {
            "draft_digest": "fictional-draft-digest",
            "targets": [{"start": 2, "end": 8, "original_text": PRIVATE_TRACE}],
        },
        "precheck_transformations": [{"kind": "bound_patch", "detail": PRIVATE_TRACE}],
        "repair_feedback": PRIVATE_TRACE,
    }


def public_response():
    return {
        "schema_version": "chat_response_v1",
        "response_type": "answer",
        "answer_text": "Assess whether the supplied candidate fits the stated conditions.",
        "short_answer": None,
        "citations": [],
        "refusal_reason": None,
        "follow_up_questions": [],
        "confidence": 0.5,
    }


@pytest.fixture
def projection_fixture(monkeypatch):
    from app.modules.answering import service
    from app.modules.answering.models import AnswerRequest
    from app.modules.learning_state import sources

    req = SimpleNamespace(
        id="fictional-request",
        mode="interactive_chat",
        command={"answer_mode": "textbook", "enhancement_version": "learning_enhancement_v1"},
        trace={
            "token_budget": repair_trace(),
            "drafts": [repair_trace()],
            "checks": [repair_trace()],
            "repair_feedback": PRIVATE_TRACE,
        },
        profile_snapshot_id=None,
        context_snapshot_id=None,
        release_id=None,
    )
    answer = SimpleNamespace(
        id="fictional-answer",
        request_id=req.id,
        job_id="fictional-job",
        message_id=None,
        response_schema="chat_response_v1",
        response=public_response(),
        model_mode="mock",
        timing={"total_ms": 2.0},
    )

    class FakeDB:
        def get(self, model, key):
            assert model is AnswerRequest and key == req.id
            return req

        def scalars(self, query):
            return []

    monkeypatch.setattr(sources, "presentation_for", lambda db, answer_id: None)
    monkeypatch.setattr(service, "can_regenerate", lambda db, value: False)
    return FakeDB(), req, answer


def test_private_draft_persistence_retains_bound_plan_and_transformation():
    from app.modules.learning_state.models import PrivateAnswerDraft
    from app.modules.learning_state.sources import persist_private_records

    result = GenerationOutcome(
        response=public_response(),
        drafts=[{"response": public_response(), **repair_trace()}],
        checks=[{"checker_result": {"accepted": False}, "repair_feedback": PRIVATE_TRACE}],
    )
    req = SimpleNamespace(id="fictional-request", command={"memory_snapshot_id": None})
    rows = []
    persist_private_records(SimpleNamespace(add=rows.append), req, result)
    assert len(rows) == 2
    assert all(isinstance(row, PrivateAnswerDraft) for row in rows)
    assert [row.phase for row in rows] == ["generated_draft", "online_check"]
    assert rows[0].payload == result.drafts[0]
    assert rows[1].payload == result.checks[0]
    assert rows[0].payload["precheck_transformations"][0]["detail"] == PRIVATE_TRACE


def test_actual_answer_out_does_not_project_private_repair_records(projection_fixture):
    from app.modules.answering.service import answer_out

    db, req, answer = projection_fixture
    before = deepcopy(req.trace)
    raw = answer_out(db, answer)
    serialized = AnswerOut.model_validate(raw).model_dump_json()
    assert req.trace == before
    assert PRIVATE_TRACE not in serialized
    assert (
        not {"drafts", "checks", "token_budget", "bound_repair_plan", "repair_feedback"}
        & raw.keys()
    )
    assert raw["answer_completeness"] is None
    assert raw["response"] == public_response()


def test_actual_processing_projection_omits_private_target_and_feedback(projection_fixture):
    from app.modules.answering.diagnostics import processing_projection

    _, req, answer = projection_fixture
    req.trace["token_budget"]["teaching_plan"] = {
        "level": "hint",
        "style": "guided",
        "mode": "hint",
        **repair_trace(),
    }
    value = processing_projection(req, answer)
    assert value.teaching.mode == "hint"
    assert PRIVATE_TRACE not in value.model_dump_json()
    assert "bound_repair_plan" not in value.model_dump_json()


def test_actual_admin_draft_review_projects_text_without_patch_targets(monkeypatch):
    from app.modules.answering.draft_review import review_drafts

    req = SimpleNamespace(id="fictional-request", trace={}, state="failed", release_id=None)
    row = SimpleNamespace(
        id="fictional-draft",
        created_at=datetime(2026, 10, 5, tzinfo=timezone.utc),
        payload={"response": public_response(), "revision": 1, **repair_trace()},
    )

    class FakeDB:
        def scalar(self, query):
            return req

        def scalars(self, query):
            return [row]

    actor = SimpleNamespace(
        id="fictional-admin",
        workspace_id="fictional-workspace",
        role=SimpleNamespace(name="admin"),
    )
    value = review_drafts(FakeDB(), actor, req.id)
    assert value.items[0].answer_text == public_response()["answer_text"]
    assert value.items[0].source_status == "no_sources"
    assert PRIVATE_TRACE not in value.model_dump_json()
    assert "precheck_transformations" not in value.model_dump_json()


def test_actual_experiment_outcome_uses_the_same_answer_projection(projection_fixture):
    from app.modules.answering.models import Answer
    from app.modules.experiment.bridge import item_outcome

    db, req, answer = projection_fixture
    job = SimpleNamespace(id=answer.job_id, state="succeeded", answer_id=answer.id)
    original_get = db.get

    def get(model, key):
        if model is Answer and key == answer.id:
            return answer
        return original_get(model, key)

    db.get = get
    db.scalar = lambda query: job
    value = item_outcome(db, SimpleNamespace(request_id=req.id))
    assert value["status"] == "completed"
    assert value["response"] == public_response()
    assert PRIVATE_TRACE not in str(value)
    assert "token_budget" not in value and "drafts" not in value and "checks" not in value


def test_answer_contract_rejects_new_top_level_patch_trace(projection_fixture):
    from app.modules.answering.service import answer_out

    db, _, answer = projection_fixture
    raw = answer_out(db, answer)
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        AnswerOut.model_validate({**raw, "bound_repair_plan": repair_trace()})


def test_timing_is_public_and_cannot_hold_private_patch_trace(projection_fixture):
    from app.modules.answering.service import answer_out

    db, _, answer = projection_fixture
    answer.timing["repair_feedback"] = PRIVATE_TRACE
    value = AnswerOut.model_validate(answer_out(db, answer)).model_dump_json()
    # Timing is an existing unfiltered public dictionary, so the generator must
    # keep all repair targets and feedback in drafts/checks, outside this field.
    assert PRIVATE_TRACE in value
