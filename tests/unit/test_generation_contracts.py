"""Cross-mode fixtures for the foundation contracts and generation handover."""

import pytest
from pydantic import ValidationError

from contracts.models import ChatMessageCreate, ChatResponseV1, MCQCommand, MCQResponseV1


def chat_payload(**updates):
    return {
        "schema_version": "chat_response_v1",
        "response_type": "answer",
        "answer_text": "Plants convert light energy into chemical energy. [ev_001]",
        "short_answer": "Conversion of light energy to chemical energy",
        "citations": ["ev_001"],
        "refusal_reason": None,
        "follow_up_questions": [],
        "confidence": None,
        **updates,
    }


def mcq_command(options):
    return MCQCommand(
        mode="benchmark_mcq",
        run_id="run",
        item_id="item",
        question_id="q1",
        question_text="Which substance?",
        options=options,
    )


def test_chat_message_never_requires_choices():
    message = ChatMessageCreate(content="Why does it need light?")
    assert message.use_profile is True
    assert "options" not in message.model_dump()


@pytest.mark.parametrize(
    "forbidden", ["gold_answer", "history", "summary", "model", "owner", "options"]
)
def test_learner_cannot_supply_trusted_or_evaluator_fields(forbidden):
    with pytest.raises(ValidationError):
        ChatMessageCreate.model_validate(
            {"content": "Explain photosynthesis.", forbidden: "untrusted"}
        )


def test_chat_preserves_complete_prose_and_all_required_fields():
    result = ChatResponseV1.model_validate(chat_payload())
    assert result.answer_text.startswith("Plants convert")
    assert len(result.answer_text) > 1
    for name in chat_payload():
        value = chat_payload()
        value.pop(name)
        with pytest.raises(ValidationError):
            ChatResponseV1.model_validate(value)


@pytest.mark.parametrize("confidence", [True, False, float("nan"), float("inf"), -0.1, 1.1])
def test_chat_rejects_invalid_confidence(confidence):
    with pytest.raises(ValidationError):
        ChatResponseV1.model_validate(chat_payload(confidence=confidence))


def test_refusal_has_distinct_empty_and_null_invariants():
    payload = chat_payload(
        response_type="refusal",
        answer_text="No supporting passage is available.",
        short_answer=None,
        citations=[],
        refusal_reason="NO_EVIDENCE",
    )
    ChatResponseV1.model_validate(payload)
    for key, value in (
        ("confidence", 0.0),
        ("short_answer", "A"),
        ("citations", ["ev_001"]),
        ("follow_up_questions", ["Anything else?"]),
        ("refusal_reason", None),
    ):
        with pytest.raises(ValidationError):
            ChatResponseV1.model_validate({**payload, key: value})


@pytest.mark.parametrize("response_type", ["social", "clarification"])
def test_social_and_clarification_have_no_compact_factual_answer(response_type):
    with pytest.raises(ValidationError):
        ChatResponseV1.model_validate(chat_payload(response_type=response_type))
    ChatResponseV1.model_validate(
        chat_payload(response_type=response_type, short_answer=None, citations=[])
    )


def test_mcq_requires_exact_four_labels_and_normalized_distinct_options():
    for options in (
        {"A": "Water", "B": "Oxygen"},
        {"A": "Water", "B": " water ", "C": "Nitrogen", "D": "Hydrogen"},
        {"A": "Ａ", "B": "a", "C": "Nitrogen", "D": "Hydrogen"},
        {"A": "Carbon  dioxide", "B": "carbon dioxide", "C": "Nitrogen", "D": "Hydrogen"},
    ):
        with pytest.raises(ValidationError):
            mcq_command(options)


def test_mcq_preserves_original_option_text_for_exact_output_comparison():
    options = {"A": "  Carbon dioxide  ", "B": "Oxygen", "C": "Nitrogen", "D": "Hydrogen"}
    command = mcq_command(options)
    assert command.options["A"] == options["A"]
    result = MCQResponseV1.model_validate(
        {
            "question_id": "q1",
            "answer": "A",
            "answer_text": options["A"],
            "citations": [],
            "confidence": None,
            "refused": False,
            "refusal_reason": None,
            "short_explanation": "A selected original option.",
        }
    )
    assert result.answer_text == options["A"]


def test_legacy_mcq_refusal_enum_is_separate_from_chat():
    result = MCQResponseV1.model_validate(
        {
            "question_id": "q1",
            "answer": None,
            "answer_text": None,
            "citations": [],
            "confidence": None,
            "refused": True,
            "refusal_reason": "IRRELEVANT_EVIDENCE",
            "short_explanation": None,
        }
    )
    assert result.refused
    with pytest.raises(ValidationError):
        ChatResponseV1.model_validate(
            chat_payload(
                response_type="refusal",
                short_answer=None,
                citations=[],
                refusal_reason="IRRELEVANT_EVIDENCE",
            )
        )
