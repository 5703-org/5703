"""Offline attack schedule and current response-boundary regressions."""

import json

from generation import GenerationService
from generation.parser import ResponseValidationError, parse_response
from generation.types import RequestBudget

from evaluation.week09_continuation.injection_pilot import (
    CANARY,
    CASE_SPECS,
    FORGED_CITATION,
    PRIVATE_KEY_CANARY,
    CaptureAdapter,
    PromptCaptured,
    _score_draft,
    case_payload,
    estimated_cost,
    freeze,
    generation_request,
    load_official_anchor,
)


def draft(**updates):
    value = {
        "schema_version": "chat_response_v1",
        "response_type": "answer",
        "answer_text": "Light-dependent reactions convert light to chemical energy. [ev_001]",
        "short_answer": None,
        "citations": ["ev_001"],
        "refusal_reason": None,
        "follow_up_questions": [],
        "confidence": 0.8,
        "tutor_question": None,
        "learner_attempt_evaluation": None,
    }
    value.update(updates)
    return json.dumps(value)


def test_official_anchor_is_exact_real_chunk_and_original_pdf():
    anchor = load_official_anchor()
    assert anchor["hit"]["text_hash"] == (
        "3875811a6249a7143e15d588fc278821bb897a38f13f16ca024829c2495f6fa7"
    )
    assert anchor["hit"]["pages"] == [138]
    assert anchor["release_id"] == "4f11bd70-a486-4d16-b216-78cfe499530a"


def test_frozen_messages_reach_each_attack_boundary_without_hidden_key(tmp_path):
    location = tmp_path / "freeze"
    receipt = freeze(location)
    manifest = json.loads((location / "freeze.json").read_text(encoding="utf-8"))
    assert receipt["frozen_cases"] == len(CASE_SPECS) == 6
    by_kind = {row["kind"]: row for row in manifest["cases"]}
    for kind in ("source_instruction", "source_forged_citation"):
        assert by_kind[kind]["source_is_adversarial_derivative"] is True
    assert CANARY in str(by_kind["source_instruction"]["messages"])
    assert FORGED_CITATION in str(by_kind["source_forged_citation"]["messages"])
    assert CANARY in str(by_kind["memory_mode_override"]["messages"])
    assert "mitochondria" in str(by_kind["memory_false_fact"]["messages"])
    assert PRIVATE_KEY_CANARY not in str([row["messages"] for row in manifest["cases"]])
    assert "unpublished instructor answer key" in str(by_kind["answer_key_coaxing"]["messages"])


def test_source_attack_stays_inside_data_segment_and_is_not_authority():
    anchor = load_official_anchor()
    payload = case_payload("source_instruction", anchor)
    capture = CaptureAdapter()
    try:
        GenerationService(adapter=capture).generate(
            generation_request("INJ-002", payload), RequestBudget(max_calls=4)
        )
    except PromptCaptured:
        pass
    assert len(capture.calls) == 1
    messages = capture.calls[0]["messages"]
    assert CANARY not in messages[0]["content"]
    assert CANARY in next(
        message["content"] for message in messages if "CONTEXT_DATA_JSON:" in message["content"]
    )
    assert payload["evidence"]["source_title"].startswith("Isolated adversarial derivative")
    assert payload["evidence"]["source_url"] is None


def test_forged_citation_draft_is_rejected_by_current_parser():
    healthy = _score_draft(draft(), kind="clean_baseline")
    assert healthy["publication_parser_valid"] is True
    invalid = _score_draft(
        draft(
            answer_text="Light-dependent reactions convert energy. [ev_999]",
            citations=["ev_999"],
        ),
        kind="source_forged_citation",
    )
    assert invalid["forged_citation_present"] is True
    assert invalid["publication_parser_valid"] is False
    assert invalid["publication_parser_error"] == "INVALID_CITATIONS"
    raw = json.loads(draft(answer_text="Fake. [ev_999]", citations=["ev_999"]))
    raw.pop("tutor_question")
    raw.pop("learner_attempt_evaluation")
    try:
        parse_response(
            json.dumps(raw),
            mode="interactive_chat",
            condition="E1",
            evidence_ids=["ev_001"],
        )
    except ResponseValidationError as exc:
        assert exc.code == "INVALID_CITATIONS"
    else:
        raise AssertionError("Forged citation was admitted")


def test_cost_requires_provider_usage_counters():
    rates = {"cached": 0.003, "uncached": 0.15, "output": 0.6}
    assert estimated_cost({}, rates) is None
    assert (
        estimated_cost(
            {"input_tokens": 100, "output_tokens": 50, "cache_hit_input_tokens": 20}, rates
        )
        == (20 * 0.003 + 80 * 0.15 + 50 * 0.6) / 1_000_000
    )
