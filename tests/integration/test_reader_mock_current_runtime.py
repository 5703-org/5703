"""Current reader API/worker/SQL regression with authored data and mock generation."""

import pytest

from app.modules.answering.models import AnswerRequest
from .test_chat_runtime import corpus, finish, session
from .test_reading_answer_core_v5 import context_for, send


@pytest.mark.parametrize(
    "question",
    ["What is photosynthesis?", "What is photosynthesis in this selected passage?"],
)
def test_current_reader_definition_persists_supported_mock_answer(runtime, question):
    rt = runtime
    rt.settings.chat_query_preparation_policy = "anchored_reference_v21"
    doc, build = corpus(rt)
    receipt = send(rt, session(rt), context_for(rt, doc, build), question)
    answer = finish(rt, receipt)
    with rt.db() as db:
        request = db.get(AnswerRequest, receipt["request_id"])
        assert request.command["requirements_version"] == "question_requirements_v7"
        assert request.trace["understanding"]["version"] == "question_requirements_v7"
        assert "Textbook section:" in request.trace["prepared_query"]["standalone_query"]
        assert "Textbook section:" not in request.trace["understanding"]["standalone_query"]
        assert request.state == "answered"
    assert answer["model_mode"] == "mock"
    assert answer["response"]["response_type"] == "answer"
    assert answer["response"]["citations"]
