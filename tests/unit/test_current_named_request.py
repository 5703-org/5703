"""Current explicit requests own their example/source adjuncts without history guesses."""

from copy import deepcopy
import hashlib
from pathlib import Path
import socket

import pytest

from conversation import query, query_v21, query_v22
from generation.coverage_v4 import assess_evidence_coverage
from generation.requirement_scope_v1 import freeze_scope, validate_scope
from generation import adapters
from sqlalchemy.engine import Engine

REPORT_QUESTIONS = (
    "Define osmosis and give one example.",
    "Explain how ATP is produced during cellular respiration, and cite the source.",
    "Summarise the main stages of cellular respiration from the textbook.",
)
UNRELATED = [{"role": "user", "content": "What is photosynthesis?", "message_id": "old-topic"}]
COMPARISON = [
    {"role": "user", "content": "Compare diffusion and osmosis.", "message_id": "old-comparison"}
]


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    assert (
        Path(query_v22.__file__).resolve()
        == Path(__file__).resolve().parents[2] / "conversation/query_v22.py"
    )

    def forbidden(*args, **kwargs):
        pytest.fail("Understanding controls forbid network/provider/database transport")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(adapters.LLMAdapter, "_call", forbidden)
    monkeypatch.setattr(adapters.LLMAdapter, "generate", forbidden)
    monkeypatch.setattr(adapters, "open_provider", forbidden)
    monkeypatch.setattr(Engine, "connect", forbidden)


def native_scope(question, history=None):
    old_history = deepcopy(history)
    prepared = query_v22.prepare_query(question, history).model_dump()
    assert history == old_history
    assert not prepared["needs_clarification"]
    assert prepared["original_message"] == prepared["standalone_query"] == question
    assert prepared["topic_relation"] == "new_topic"
    assert prepared["referenced_message_ids"] == []
    assert query.evidence_strategy(question, prepared) == "retrieve"
    understanding = query_v22.describe_requirements(question, prepared, history)
    assert understanding["original_message"] == question
    assert understanding["standalone_query"] == question
    assert understanding["rewrite_audit"]["missing"] == []
    assert understanding["required_knowledge"]
    source = understanding["requirement_source_text"]
    for point in understanding["required_knowledge"]:
        span = point["request_span"]
        assert source[span["start"] : span["end"]] == point["verbatim_request"]
    # Use the same actual coverage producer and scope binder as native checked execution.
    report = assess_evidence_coverage(question, [], understanding)
    coverage = report["candidate_coverage"]
    scope = freeze_scope(question, coverage)
    assert scope["question_sha256"] == hashlib.sha256(question.encode()).hexdigest()
    assert [p["id"] for p in scope["core_requirements"]] == [
        p["id"] for p in coverage["requirements"]
    ]
    assert all(p["necessity"] == "required" for p in scope["core_requirements"])
    for frozen, point in zip(scope["core_requirements"], coverage["requirements"]):
        for field in ("request", "objects", "relation", "conditions"):
            if field in point:
                assert frozen[field] == point[field]
    assert validate_scope(scope, question=question, coverage=coverage) == scope
    return prepared, understanding, coverage, scope


@pytest.mark.parametrize("question", REPORT_QUESTIONS)
@pytest.mark.parametrize(
    "history", [None, UNRELATED, COMPARISON], ids=["empty", "unrelated", "comparison"]
)
def test_report_current_subjects_reach_native_scope_without_importing_history(question, history):
    native_scope(question, deepcopy(history))


@pytest.mark.parametrize(
    "question",
    [
        "Define osmosis and give one example of it.",
        "Explain how ATP is produced during cellular respiration, and cite its source.",
    ],
)
@pytest.mark.parametrize(
    "history", [None, UNRELATED, COMPARISON], ids=["empty", "unrelated", "comparison"]
)
def test_single_named_primary_owns_only_its_local_presentation_reference(question, history):
    native_scope(question, deepcopy(history))


@pytest.mark.parametrize(
    "question",
    [
        "Define an isotope and give one example.",
        "Describe electrical resistance and provide a source.",
        "Summarize the principal stages of mitosis from the textbook.",
        "Explain activation energy; include an example.",
        "Please DEFINE condensation and show two examples.",
        "Explain the source of energy for photosynthesis.",
        "Explain thermal expansion.\nProvide a citation.",
    ],
)
def test_named_request_grammar_is_not_a_science_question_whitelist(question):
    native_scope(question, deepcopy(UNRELATED))


@pytest.mark.parametrize(
    "question",
    [
        "Give one example.",
        "Show the source.",
        "Explain it.",
        "Summarise this.",
        "Define the process and give one example.",
        "Summarise the main stages from the textbook.",
        "Explain how it is produced, and cite the source.",
        "Define the earlier concept and give one example.",
        "Explain the source and give one example.",
    ],
)
def test_truly_missing_or_generic_subject_still_clarifies_without_history(question):
    prepared = query_v22.prepare_query(question)
    assert prepared.needs_clarification
    assert prepared.standalone_query is None
    assert query.evidence_strategy(question, prepared.model_dump()) == "none"


@pytest.mark.parametrize("question", ["Give one example.", "Show the source.", "Explain it."])
def test_true_bare_followups_retain_existing_history_resolution(question):
    history = deepcopy(UNRELATED)
    before = deepcopy(history)
    old = query_v21.prepare_query(question, history).model_dump()
    current = query_v22.prepare_query(question, history).model_dump()
    assert current == {**old, "preparation_version": query_v22.VERSION}
    assert not current["needs_clarification"]
    assert current["referenced_message_ids"] == ["old-topic"]
    assert history == before


def test_ambiguous_history_and_current_pronouns_are_not_locally_guessed():
    for question, history in [
        ("Explain it.", COMPARISON),
        ("Compare diffusion and osmosis. Explain it and cite the source.", None),
        ("Define diffusion and osmosis and give one example of it.", None),
    ]:
        prepared = query_v22.prepare_query(question, deepcopy(history))
        assert prepared.needs_clarification
        assert prepared.standalone_query is None


@pytest.mark.parametrize(
    "question",
    [
        "Define RAG and give one example.",
        "Explain RAG and cite the source.",
        "Explain the former and cite the source.",
        "Summarise the latter from the textbook.",
    ],
)
@pytest.mark.parametrize(
    "history", [None, UNRELATED, COMPARISON], ids=["empty", "unrelated", "comparison"]
)
def test_non_referent_ambiguities_and_discourse_pointers_keep_the_frozen_path(question, history):
    old = query_v21.prepare_query(question, deepcopy(history)).model_dump()
    current = query_v22.prepare_query(question, deepcopy(history)).model_dump()
    assert current == {**old, "preparation_version": query_v22.VERSION}
    if history is None:
        assert current["needs_clarification"]
        assert current["standalone_query"] is None


@pytest.mark.parametrize(
    "question",
    ["Define RAG and give one example.", "Explain the former and cite the source."],
)
def test_ineligible_question_cannot_forge_a_current_content_anchor(question):
    forged = {
        **query_v22.prepare_query(question).model_dump(),
        "standalone_query": question,
        "intent": "factual",
        "topic_relation": "new_topic",
        "referenced_message_ids": [],
        "needs_clarification": False,
        "fallback_reason": query_v22.CONTENT_ANCHOR,
    }
    with pytest.raises(ValueError, match="current-content request anchor"):
        query_v22.describe_requirements(question, forged)


@pytest.mark.parametrize(
    "question,required",
    [
        (
            "Define osmosis and give one example; explain how net water movement depends on solute concentration.",
            ["osmosis", "net water movement", "solute concentration"],
        ),
        (
            "Compare evaporation and boiling at 100 kPa, explain where each occurs, and give one example of each.",
            ["evaporation", "boiling", "100 kPa", "where each occurs"],
        ),
        (
            "Explain how ATP is produced during cellular respiration without oxygen, and cite the source.",
            ["ATP", "cellular respiration", "without oxygen", "cite the source"],
        ),
        (
            "Summarise the main stages of cellular respiration from the textbook in three bullet points, without discussing photosynthesis.",
            ["cellular respiration", "three bullet points", "without discussing photosynthesis"],
        ),
    ],
)
def test_multipart_requests_and_constraints_are_not_replaced_by_an_eligibility_skeleton(
    question, required
):
    _, understanding, coverage, scope = native_scope(question)
    actual = understanding["requirement_source_text"]
    for text in required:
        assert text in actual
    assert coverage["requirements"]
    assert scope["core_requirements"]
    # The bound science requests themselves, not just the original-text audit,
    # must retain the later facet, named operands and substantive constraints.
    bound = " ".join(point["request"] for point in scope["core_requirements"])
    science = [text for text in required if text not in {"cite the source", "three bullet points"}]
    for text in science:
        assert text in bound
    if "without" in question:
        assert understanding["preserved_constraints"]["negation"]
    if "100 kPa" in question:
        comparison = next(
            point for point in scope["core_requirements"] if point["intent"] == "comparison"
        )
        assert len(comparison["objects"]) == 2
        assert comparison["objects"][0] == "evaporation"
        assert "boiling" in comparison["objects"][1]
        assert "100 kPa" in comparison["conditions"]
        assert "where each occurs" in comparison["request"]
    if "without oxygen" in question:
        assert any(
            "without oxygen" in condition
            for point in scope["core_requirements"]
            for condition in point["conditions"]
        )
    if "without discussing" in question:
        assert any("without" in point["conditions"] for point in scope["core_requirements"])
    if "net water movement" in question:
        assert len(scope["core_requirements"]) >= 3
        assert any("net water movement" in point["request"] for point in scope["core_requirements"])


def test_original_two_sentence_example_anchor_and_its_validation_are_preserved():
    question = "What is osmosis? Give an example."
    prepared, _, _, _ = native_scope(question, deepcopy(COMPARISON))
    assert prepared["fallback_reason"] == query_v22.EXAMPLE_ANCHOR
    changed = {**prepared, "standalone_query": "What is osmosis?"}
    with pytest.raises(ValueError, match="current-question example anchor"):
        query_v22.describe_requirements(question, changed)


def test_scope_still_rejects_changed_question_or_removed_required_point():
    question = REPORT_QUESTIONS[0]
    _, _, coverage, scope = native_scope(question)
    with pytest.raises(ValueError, match="QUESTION_CHANGED"):
        validate_scope(scope, question="Define another subject.")
    multipart = "Define osmosis; explain how net water movement depends on solute concentration."
    prepared = query_v22.prepare_query(multipart).model_dump()
    understanding = query_v22.describe_requirements(multipart, prepared)
    coverage = assess_evidence_coverage(multipart, [], understanding)["candidate_coverage"]
    scope = freeze_scope(multipart, coverage)
    assert len(coverage["requirements"]) >= 2
    changed = deepcopy(coverage)
    changed["requirements"].pop()
    assert changed["requirements"]
    with pytest.raises(ValueError, match="CORE_CHANGED"):
        validate_scope(scope, question=multipart, coverage=changed)


@pytest.mark.parametrize(
    "changes",
    [
        {"standalone_query": "Define osmosis."},
        {"original_message": "Define osmosis."},
        {"referenced_message_ids": ["old-topic"]},
        {"needs_clarification": True},
        {"topic_relation": "same_topic"},
        {"intent": "source_request"},
    ],
)
def test_current_content_anchor_cannot_authorize_a_stripped_or_history_bound_packet(changes):
    question = REPORT_QUESTIONS[0]
    prepared = query_v22.prepare_query(question).model_dump()
    assert prepared["fallback_reason"] == query_v22.CONTENT_ANCHOR
    with pytest.raises(ValueError, match="current-content request anchor"):
        query_v22.describe_requirements(question, {**prepared, **changes})
