"""Optional state preparation can degrade; access revocation cannot be bypassed."""

from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import select, func

from app.core.exceptions import AppError
from app.modules.answering.models import AnswerRequest, Message
from personalisation.memory_v2 import MemoryPreparationUnavailable
from .test_chat_runtime import call, corpus, session, submit, finish


def test_optional_preparation_failure_is_recorded_and_answer_still_executes(runtime):
    corpus(runtime)
    current = session(runtime)
    with patch(
        "app.modules.learning_state.memory.freeze_memory",
        side_effect=MemoryPreparationUnavailable("MEMORY_CONTEXT_BUDGET_EXCEEDED"),
    ):
        receipt = submit(runtime, current)
    answer = finish(runtime, receipt)
    assert answer["response"]["response_type"] == "answer"
    with runtime.db() as db:
        request = db.get(AnswerRequest, receipt["request_id"])
        assert request.command["memory_snapshot_id"] is None
        assert request.trace["memory_stage"]["status"] == "unavailable"
    detail = call(
        runtime,
        "GET",
        "/admin/failures/" + receipt["request_id"],
        headers=runtime.headers("admin@example.com"),
    )
    assert detail["processing"]["memory"] == {
        "status": "unavailable",
        "policy_version": "query_conditioned_memory_v2",
        "error_code": "MEMORY_CONTEXT_BUDGET_EXCEEDED",
    }


def test_revocation_conflict_rolls_back_submission_instead_of_optional_fallback(runtime):
    current = session(runtime)
    headers = {**runtime.headers(), "Idempotency-Key": str(uuid4())}
    with patch("app.modules.learning_state.memory.freeze_memory", side_effect=AppError("CONFLICT")):
        response = runtime.client.post(
            f"/api/v1/sessions/{current['id']}/messages",
            json={"content": "What is photosynthesis?"},
            headers=headers,
        )
    assert response.status_code == 409
    with runtime.db() as db:
        assert (
            db.scalar(
                select(func.count()).select_from(Message).where(Message.session_id == current["id"])
            )
            == 0
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(AnswerRequest)
                .where(AnswerRequest.session_id == current["id"])
            )
            == 0
        )
