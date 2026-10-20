"""Implicit task navigation must not capture a newly named learning problem."""

from uuid import uuid4
import pytest
from app.modules.answering.models import AnswerRequest
from .test_chat_runtime import call, corpus, session


@pytest.mark.parametrize(
    "question,new_problem",
    [
        ("Give a complete explanation of osmosis.", True),
        ("Another question: what is osmosis?", True),
        ("Another photosynthesis question: how does the Calvin cycle use ATP?", True),
        ("Give me the full explanation.", False),
        ("Give me another hint.", False),
        ("Could you please provide a complete explanation for this problem?", False),
        ("Give me another hint for this problem, please.", False),
    ],
)
def test_auto_task_navigation_does_not_capture_new_named_problem(runtime, question, new_problem):
    rt = runtime
    corpus(rt)
    s = session(rt)

    def send(content, **extra):
        return call(
            rt,
            "POST",
            f"/sessions/{s['id']}/messages",
            {"content": content, "use_profile": False, **extra},
            {**rt.headers(), "Idempotency-Key": str(uuid4())},
            202,
        )

    original = "Give me a first hint: why does photosynthesis need light?"
    first = send(original, teaching_mode="hint")
    call(rt, "POST", "/jobs/" + first["job_id"] + "/cancel", {})
    second = send(question)
    call(rt, "POST", "/jobs/" + second["job_id"] + "/cancel", {})
    with rt.db() as db:
        initial = db.get(AnswerRequest, first["request_id"]).command["teaching_context"]
        current = db.get(AnswerRequest, second["request_id"]).command["teaching_context"]
        if new_problem:
            assert current["task_id"] != initial["task_id"]
            assert current["current_problem"] == question
            assert current["teaching_mode"] == "direct"
        else:
            assert current["task_id"] == initial["task_id"]
            assert current["current_problem"] == original
        assert type(current["continuing"]) is bool
        assert db.get(AnswerRequest, second["request_id"]).budget["consumed_calls"] == 0
