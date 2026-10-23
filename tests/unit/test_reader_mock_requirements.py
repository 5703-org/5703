"""Reproduce current reader mock failures with authored, offline source evidence."""

import hashlib

import pytest

from conversation.requirements_v4 import describe_requirements as v4
from conversation.requirements_v5 import describe_requirements as v5
from conversation.requirements_v6 import separate_help_depth
from conversation.requirements_v7 import separate_embedded_help_depth
from generation import GenerationRequest, GenerationService
from scripts.verify.replay_openstax_mock_generation import request_evidence


def requirements(version, question, prepared):
    if version == 4:
        return v4(question, prepared)
    result = v5(question, prepared)
    if version >= 6:
        result = separate_help_depth(result)
    if version >= 7:
        result = separate_embedded_help_depth(result)
    return result


def generate(version, question, passage, *, reading=True):
    prepared = {
        "original_message": question,
        "standalone_query": question
        + "\nTextbook section: Chapter 8 Photosynthesis / 8.1 Overview",
        "intent": "factual",
        "topic_relation": "new_topic",
        "referenced_message_ids": [],
        "needs_clarification": False,
        "preparation_version": "conversation_preparer_v21",
        "fallback_reason": "verified_reading_selection" if reading else None,
    }
    understanding = requirements(version, question, prepared)
    hit = {
        "chunk_id": "authored-reader",
        "asset_id": "authored-reader",
        "processing_id": "authored-reader",
        "source_title": "Authored reader fixture",
        "section": "Photosynthesis",
        "pages": [1],
        "locator": "Authored fixture, page 1",
        "text": passage,
        "text_hash": hashlib.sha256(passage.encode()).hexdigest(),
    }
    return GenerationService().generate(
        GenerationRequest(
            request_id="reader-mock-successor",
            mode="interactive_chat",
            condition="E1",
            question=question,
            prepared_query=prepared,
            understanding=understanding,
            evidence=request_evidence([hit]),
            enhancement_version="learning_enhancement_v1",
            reliability_policy="evidence_reliability_v5",
            source_map={
                "authored-reader": {
                    "document_version_id": "authored-version",
                    "processing_id": "authored-reader",
                    "asset_id": "authored-reader",
                    "chunk_text": passage,
                    "chunk_hash": hit["text_hash"],
                    "units": [
                        {
                            "id": "u1",
                            "page": 1,
                            "cleaned_text": passage,
                            "text_hash": hit["text_hash"],
                        }
                    ],
                    "spans": [
                        {
                            "unit_id": "u1",
                            "page": 1,
                            "start": 0,
                            "end": len(passage),
                            "chunk_start": 0,
                            "chunk_end": len(passage),
                        }
                    ],
                }
            },
        )
    )


@pytest.mark.parametrize("version", [4, 5, 6, 7])
@pytest.mark.parametrize(
    "question", ["What is photosynthesis?", "What is photosynthesis in this selected passage?"]
)
def test_reader_locator_does_not_block_supported_mock_answer(version, question):
    passage = "Photosynthesis converts sunlight into chemical energy."
    result = generate(version, question, passage)
    assert result.succeeded and result.model_mode == "mock"
    assert result.response["response_type"] == "answer"
    assert result.response["answer_text"] == passage + " [ev_001]"
    assert result.response["citations"] == ["ev_001"]


@pytest.mark.parametrize("version", [4, 5, 6, 7])
@pytest.mark.parametrize(
    "question",
    ["What is photosynthesis without sunlight?", "What is photosynthesis at 2031 kelvin?"],
)
def test_reader_resolution_preserves_unsupported_scientific_conditions(version, question):
    result = generate(version, question, "Photosynthesis converts sunlight into chemical energy.")
    assert result.succeeded
    assert result.response["response_type"] == "refusal"
    assert result.response["citations"] == []


@pytest.mark.parametrize("version", [4, 5, 6, 7])
def test_unverified_reading_metadata_keeps_original_query(version):
    result = generate(
        version,
        "What is photosynthesis?",
        "Photosynthesis converts sunlight into chemical energy.",
        reading=False,
    )
    assert result.response["response_type"] == "refusal"
