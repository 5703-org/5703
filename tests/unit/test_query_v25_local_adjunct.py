"""Current named explanation eligibility, immutable dispatch and negative controls."""

from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
import socket
from types import SimpleNamespace
from typing import Literal
from urllib import request as urllib_request

import pytest

from conversation import query as historical
from conversation import query_v22, query_v24, query_v25
from conversation.query import evidence_strategy

ROOT = Path(__file__).resolve().parents[2]
QUESTION = "Explain microtubules in detail, including what it is, how it works, and why it matters."
HISTORY = [
    {"message_id": "prior-user", "role": "user", "content": "What is osmosis?"},
    {
        "message_id": "prior-answer",
        "role": "assistant",
        "content": "Authored prior answer.",
        "state": "completed",
        "answer_id": "owned-answer",
        "answer_response_type": "answer",
        "latest_exchange_available": True,
    },
]


@pytest.fixture(autouse=True)
def no_external_io(monkeypatch):
    attempts = []

    def forbidden(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("Query controls forbid network, database and model calls")

    for owner, name in [
        (socket, "create_connection"),
        (socket, "getaddrinfo"),
        (socket.socket, "connect"),
        (socket.socket, "connect_ex"),
        (urllib_request, "urlopen"),
    ]:
        monkeypatch.setattr(owner, name, forbidden)
    from sqlalchemy.engine import Engine
    from generation.adapters import LLMAdapter

    monkeypatch.setattr(Engine, "connect", forbidden)
    monkeypatch.setattr(LLMAdapter, "generate", forbidden)
    monkeypatch.setattr(LLMAdapter, "_call", forbidden)
    assert Path(query_v25.__file__).resolve() == ROOT / "conversation/query_v25.py"
    yield
    assert attempts == []


@pytest.mark.parametrize(
    "subject",
    [
        "microtubules",
        "the cytoskeleton",
        "a digital monitor",
        "a hydraulic lever",
    ],
)
@pytest.mark.parametrize("history", [[], HISTORY])
def test_named_current_subject_owns_local_adjunct_without_historical_rewrite(subject, history):
    question = QUESTION.replace("microtubules", subject)
    before = deepcopy(history)
    prepared = query_v25.prepare_query(question, history).model_dump()
    assert prepared["standalone_query"] == prepared["original_message"] == question
    assert not prepared["needs_clarification"]
    assert prepared["referenced_message_ids"] == []
    assert prepared["topic_relation"] == "new_topic" and prepared["intent"] == "factual"
    assert prepared["fallback_reason"] == query_v25.LOCAL_ADJUNCT
    assert evidence_strategy(question, prepared) == "retrieve"
    assert history == before


def test_confirmed_baseline_failure_and_history_contamination_remain_reproducible():
    for old in [query_v22, query_v24]:
        initial = old.prepare_query(QUESTION).model_dump()
        assert initial["needs_clarification"] and initial["fallback_reason"] == "missing_referent"
        historical_result = old.prepare_query(QUESTION, HISTORY).model_dump()
        assert "how osmosis works" in historical_result["standalone_query"]
        assert historical_result["referenced_message_ids"] == ["prior-user"]


@pytest.mark.parametrize(
    "question",
    [
        "Explain a monitor, including how it works.",
        "Describe a monitor, including what it does and why it is important.",
        "What are microtubules, including what they are, how they work and why they matter?",
        "Please explain a monitor in 3 sentences, including what it is and how it functions.",
    ],
)
def test_bounded_grammar_keeps_every_requested_word_and_requirement_span(question):
    prepared = query_v25.prepare_query(question).model_dump()
    assert not prepared["needs_clarification"] and prepared["standalone_query"] == question
    requirements = query_v25.describe_requirements(question, prepared)
    assert requirements["requirement_source_text"] == requirements["standalone_query"] == question
    assert requirements["rewrite_audit"]["missing"] == []
    audit = requirements["current_named_explanation_adjunct"]
    assert audit["source_text"] == question
    assert audit["coreference_resolution"] is None and audit["semantic_sufficiency"] is None
    for span in [audit["subject_span"], audit["adjunct_span"], *audit["dependent_spans"]]:
        assert question[span["start"] : span["end"]] == span["text"]
    for point in requirements["required_knowledge"] + requirements["presentation_requests"]:
        span = point.get("request_span")
        if span:
            assert question[span["start"] : span["end"]] == point["request"]


@pytest.mark.parametrize(
    "question",
    [
        "What does it do?",
        "Explain it, including how it works.",
        "Explain the complex process, including how it works.",
        "Explain an object, including how it works.",
        "Explain a monitor and a sensor, including how it works.",
        "Explain a monitor or a sensor, including how it works.",
        "Compare a monitor and a sensor, including how it works.",
        "Explain a monitor near a sensor, including how it works.",
        "Explain a monitor with a sensor, including how it works.",
        "Explain a monitor, including how that works.",
        "Explain a monitor, including how it works and why that matters.",
        "Explain a monitor, including how it works and how a sensor works.",
        "Explain a monitor, including what it is and why they matter.",
        "Explain the previous monitor, including how it works.",
        "Explain the same monitor, including how it works.",
        "Explain the selected monitor, including how it works.",
        "Explain the second monitor, including how it works.",
        "Explain the attached monitor, including how it works.",
        "Explain yours, including what it is and why it matters.",
        "Explain our findings, including what they are and why they matter.",
        "Explain your monitor, including how it works.",
        "Explain RAG, including what it is.",
        "Explain a monitor, including how it works. What did it mean earlier?",
        "Explain a monitor, including how it works without the previous diagram.",
        "Explain a monitor, including how it works only when its sensor is active.",
    ],
)
@pytest.mark.parametrize("history", [[], HISTORY])
def test_unmatched_ambiguous_foreign_and_conditional_requests_keep_native_behavior(
    question, history
):
    previous = query_v22.prepare_query(question, history).model_dump()
    result = query_v25.prepare_query(question, history).model_dump()
    assert result == {**previous, "preparation_version": query_v25.VERSION}
    assert result["fallback_reason"] != query_v25.LOCAL_ADJUNCT
    if not history and question == "What does it do?":
        assert result["needs_clarification"] and evidence_strategy(question, result) == "none"


@pytest.mark.parametrize(
    "question",
    [
        "Define osmosis and give one example.",
        "What is photosynthesis?",
        "Explain diffusion and osmosis.",
        "Hello!",
        "Why does it need light?",
    ],
)
@pytest.mark.parametrize("history", [[], HISTORY])
def test_previously_accepted_or_historical_turns_remain_native(question, history):
    previous = query_v22.prepare_query(question, history).model_dump()
    assert query_v25.prepare_query(question, history).model_dump() == {
        **previous,
        "preparation_version": query_v25.VERSION,
    }


def test_current_named_subject_outweighs_an_old_comparison_and_summary():
    history = deepcopy(HISTORY)
    history[0]["content"] = "Compare diffusion and osmosis."
    prepared = query_v25.prepare_query(QUESTION, history, "An unrelated old topic.").model_dump()
    assert prepared["standalone_query"] == QUESTION and prepared["referenced_message_ids"] == []
    assert not prepared["needs_clarification"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("standalone_query", "Explain osmosis."),
        ("referenced_message_ids", ["foreign-id"]),
        ("needs_clarification", True),
        ("intent", "comparison"),
        ("topic_relation", "same_topic"),
    ],
)
def test_requirement_anchor_rejects_changed_text_identity_or_behavior(field, value):
    prepared = query_v25.prepare_query(QUESTION).model_dump()
    prepared[field] = value
    with pytest.raises(ValueError, match="adjunct is unavailable"):
        query_v25.describe_requirements(QUESTION, prepared)


def _tree(relative):
    return ast.parse((ROOT / relative).read_text(encoding="utf-8"))


def _function(tree, name):
    return next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name
    )


def _assignment(function, name):
    values = [
        node.value
        for node in ast.walk(function)
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)
    ]
    assert len(values) == 1
    return values[0]


def _evaluate(expression, namespace):
    return eval(
        compile(ast.Expression(body=expression), "actual_candidate_service", "eval"), namespace
    )


def _namespace(version, policy="anchored_reference_v25"):
    namespace = {
        "req": SimpleNamespace(
            command={
                "preparation_version": version,
                "requirements_version": "question_requirements_v8",
            },
            mode="interactive_chat",
        ),
        "settings": SimpleNamespace(chat_query_preparation_policy=policy),
        "PREPARATION_VERSION": historical.VERSION,
        "REQUIREMENTS_V4": "question_requirements_v4",
        "current_core": True,
        "prepared": {"preparation_version": version},
        "practice_query": None,
    }
    for number in range(14, 29):
        namespace[f"query_v{number}"] = SimpleNamespace(
            VERSION=f"conversation_preparer_v{number}",
            prepare_query=f"prepare-{number}",
            describe_requirements=f"requirements-{number}",
        )
    namespace.update(
        prepare_query="historical-prepare",
        describe_requirements="historical-requirements",
        describe_requirements_v4="v4-requirements",
        describe_question="old-understanding",
    )
    return namespace


def test_registered_default_and_template_select_v25_without_removing_old_policies():
    setting = next(
        node
        for node in ast.walk(_tree("backend/app/core/config.py"))
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "chat_query_preparation_policy"
    )
    assert _evaluate(setting.value, {}) == "anchored_reference_v25"
    allowed = _evaluate(setting.annotation, {"Literal": Literal}).__args__
    assert all(f"anchored_reference_v{number}" in allowed for number in range(14, 29))
    assert (
        "CHAT_QUERY_PREPARATION_POLICY=anchored_reference_v25"
        in (ROOT / ".env.example").read_text()
    )


@pytest.mark.parametrize("number", [14, 21, 22, 23, 24, 25, 26, 27, 28])
def test_actual_submission_freezes_selected_version_and_matching_requirements(number):
    submit = _function(_tree("backend/app/modules/answering/service.py"), "submit_chat")
    request = next(
        node
        for node in ast.walk(submit)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "AnswerRequest"
    )
    command = next(keyword.value for keyword in request.keywords if keyword.arg == "command")
    values = {
        key.value: value
        for key, value in zip(command.keys, command.values)
        if isinstance(key, ast.Constant)
    }
    namespace = _namespace(f"conversation_preparer_v{number}", f"anchored_reference_v{number}")
    assert _evaluate(values["preparation_version"], namespace) == f"conversation_preparer_v{number}"
    expected = (
        "question_requirements_v8"
        if number >= 22
        else ("question_requirements_v7" if number == 21 else "question_requirements_v4")
    )
    assert _evaluate(values["requirements_version"], namespace) == expected


@pytest.mark.parametrize("number", [22, 23, 24, 25, 26, 27, 28])
def test_frozen_execution_selects_saved_preparer_and_requirement_consumer(number):
    process = _function(_tree("backend/app/modules/answering/service.py"), "execute_answer")
    namespace = _namespace(f"conversation_preparer_v{number}")
    assert (
        _evaluate(_assignment(process, "active_query_preparer"), namespace) == f"prepare-{number}"
    )
    understanding = _assignment(process, "understanding")
    consumers = [
        node
        for node in ast.walk(understanding)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.IfExp)
        and any(
            isinstance(child, ast.Name) and child.id == "query_v25" for child in ast.walk(node.func)
        )
    ]
    assert len(consumers) == 1
    assert _evaluate(consumers[0].func, namespace) == f"requirements-{number}"


def test_frozen_v25_rejects_another_requested_version():
    with pytest.raises(ValueError, match="Unsupported frozen query preparation version"):
        query_v25.prepare_query(QUESTION, version=query_v22.VERSION)
