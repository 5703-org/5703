"""Actual E5 candidate replay and conservative mock-only lexical refusal regressions."""

import hashlib
import json
from pathlib import Path

import pytest

from generation import GenerationRequest, GenerationService
from scripts.verify.replay_openstax_mock_generation import request_evidence

FIXTURE = Path(__file__).parents[1] / "fixtures/openstax_mock_candidates.json"
CASES = json.loads(FIXTURE.read_text(encoding="utf-8"))["questions"]


def generate(question, hits, **updates):
    for hit in hits:
        assert hashlib.sha256(hit["text"].encode()).hexdigest() == hit["text_hash"]
    return GenerationService().generate(
        GenerationRequest(
            request_id="mock-evidence-regression",
            mode="interactive_chat",
            condition="E1",
            question=question,
            evidence=request_evidence(hits),
            **updates,
        )
    )


@pytest.mark.parametrize(
    "case",
    [case for case in CASES if case["category"] == "unrelated"],
    ids=lambda case: case["question"],
)
def test_actual_unrelated_candidates_never_become_factual_answers(case):
    result = generate(case["question"], case["hits"])
    assert result.succeeded and result.model_mode == "mock"
    assert result.evidence  # Refusal is decided from supplied text, not an empty retrieval stub.
    assert result.response["response_type"] == "refusal"
    assert result.response["refusal_reason"] == "INSUFFICIENT_EVIDENCE"
    assert result.response["citations"] == []
    assert "mock answerer" in result.response["answer_text"]


@pytest.mark.parametrize(
    "case",
    [
        case
        for case in CASES
        if case["category"] != "unrelated" and "plants use light" not in case["question"]
    ],
    ids=lambda case: case["question"],
)
def test_actual_textbook_candidates_retain_supported_extractive_answers(case):
    result = generate(case["question"], case["hits"])
    assert result.succeeded and result.model_mode == "mock"
    assert result.response["response_type"] == "answer"
    assert result.response["citations"]
    cited = result.response["citations"][0]
    source = next(item for item in result.evidence if item["evidence_id"] == cited)
    excerpt = result.response["answer_text"].removesuffix(f" [{cited}]")
    assert " ".join(excerpt.split()) in " ".join(source["text"].split())


def test_actual_learning_objective_question_is_not_mistaken_for_an_answer():
    # Model-token accounting now admits an additional substantive source chunk.
    # The full candidate set can yield a lexical extract; it is no longer a
    # question-only fixture. This check does not certify semantic entailment.
    case = next(case for case in CASES if "plants use light" in case["question"])
    result = generate(case["question"], case["hits"])
    assert result.succeeded and result.model_mode == "mock"
    if result.response["response_type"] == "answer":
        cited = result.response["citations"][0]
        source = next(item for item in result.evidence if item["evidence_id"] == cited)
        excerpt = result.response["answer_text"].removesuffix(f" [{cited}]")
        assert " ".join(excerpt.split()) in " ".join(source["text"].split())
        assert "?" not in excerpt and "LEARNING OBJECTIVES" not in excerpt
    else:
        assert result.response["citations"] == []
    objective = "LEARNING OBJECTIVES: How do plants use light energy in photosynthesis?"
    only_objective = generate(case["question"], [authored_hit(objective)])
    assert only_objective.response["response_type"] == "refusal"
    assert only_objective.response["citations"] == []


@pytest.mark.parametrize(
    "question", ["Why does it need light?", "Make it simpler", "Give an example"]
)
def test_actual_photosynthesis_candidates_remain_usable_after_prepared_follow_up(question):
    case = next(case for case in CASES if "photosynthesis" in case["question"])
    result = generate(
        question,
        case["hits"],
        history=[{"id": "original-user", "role": "user", "content": "What is photosynthesis?"}],
    )
    assert result.succeeded and result.response["response_type"] == "answer"
    assert "photosynthesis" in result.response["answer_text"].casefold()
    assert result.response["citations"]


def authored_hit(text):
    return {
        "chunk_id": "authored-coverage-case",
        "asset_id": "authored-coverage-case",
        "processing_id": "authored-coverage-case",
        "source_title": "Explicit authored lexical-guard fixture",
        "section": "Coverage",
        "pages": [1],
        "locator": "Authored fixture, page 1",
        "text": text,
        "text_hash": hashlib.sha256(text.encode()).hexdigest(),
    }


@pytest.mark.parametrize(
    "question", ["Explain nuclear fusion in 2031", "Explain nuclear fusion without heat"]
)
def test_numbers_and_negation_are_required_content(question):
    result = generate(question, [authored_hit("Nuclear fusion releases heat.")])
    assert result.response["response_type"] == "refusal"


def test_terms_scattered_over_unrelated_paragraphs_do_not_qualify_an_excerpt():
    passage = (
        "Photosynthesis captures light. The library closes in summer. "
        "Students attend lectures. Campus visitors need identification. "
        "The restaurant converts sugar into syrup."
    )
    result = generate("How does photosynthesis convert light into sugar?", [authored_hit(passage)])
    assert result.response["response_type"] == "refusal"


def test_provider_scores_are_not_used_to_qualify_mock_evidence():
    case = next(
        case for case in CASES if case["category"] == "unrelated" and "2026" in case["question"]
    )
    first = generate(case["question"], [{**hit, "score": 1.0} for hit in case["hits"]])
    second = generate(case["question"], [{**hit, "score": -1.0} for hit in case["hits"]])
    assert first.response == second.response


def test_standard_inflections_do_not_require_unrelated_keyword_exceptions():
    result = generate(
        "How do plants convert light into sugars?",
        [authored_hit("A plant converts light into sugar.")],
    )
    assert result.response["response_type"] == "answer"


def test_grounded_teaching_base_retains_energy_form_answer():
    requirements = json.loads(
        (Path(__file__).parents[2] / "evaluation/conversations/source_requirements.json").read_text(
            encoding="utf-8"
        )
    )
    passage = next(item for item in requirements["passages"] if item["topic"] == "photosynthesis")
    result = generate(
        "What form of energy is stored in sugars made by photosynthesis?",
        [authored_hit(passage["text"])],
    )
    assert result.response["response_type"] == "answer"
    assert "chemical energy" in result.response["answer_text"]
    assert result.response["citations"] == ["ev_001"]


def test_source_exercise_question_does_not_become_an_asserted_answer():
    exercise = "What impact will this have on photosynthesis?"
    only_question = generate("What is photosynthesis?", [authored_hit(exercise)])
    assert only_question.response["response_type"] == "refusal"
    supported = generate(
        "What is photosynthesis?",
        [
            authored_hit(
                exercise
                + " Photosynthesis stores captured light energy as chemical energy in sugars."
            )
        ],
    )
    assert supported.response["response_type"] == "answer"
    assert exercise not in supported.response["answer_text"]
    assert "chemical energy" in supported.response["answer_text"]


def test_learner_correction_completes_an_ambiguous_turn_with_the_named_topic():
    result = generate(
        "I mean photosynthesis.",
        [
            authored_hit(
                "Photosynthesis captures light energy and stores it as chemical energy in sugars."
            )
        ],
        history=[{"id": "ambiguous-user", "role": "user", "content": "Why does it do that?"}],
    )
    assert result.response["response_type"] == "answer"
    assert "Photosynthesis" in result.response["answer_text"]
    assert result.response["citations"] == ["ev_001"]
