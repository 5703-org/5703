"""Actual response replay: protocol clarity never certifies factual support."""

import hashlib
import json
from pathlib import Path

import pytest

from generation.parser import ResponseValidationError, parse_response, strict_json
from generation.reliability_v4 import actual_bindings, normalize_judgment
from generation.reliability_v5 import TeachingDraftV5, response_claims
from generation.response_field_contract_v2 import instructions

FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures/actual_google_citation_protocol_20261006.json"
)


def recorded():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def public_draft(raw):
    draft = TeachingDraftV5.model_validate(strict_json(raw)).model_dump()
    assert draft.pop("tutor_question") is None
    assert draft.pop("learner_attempt_evaluation") is None
    return draft


def parse(draft, *, answer_mode="textbook", ids=None):
    return parse_response(
        json.dumps(draft),
        mode="interactive_chat",
        condition="E1",
        evidence_ids=recorded()["atomic"]["selected_evidence_ids"] if ids is None else ids,
        answer_mode=answer_mode,
    )


def singleton_control():
    draft = public_draft(recorded()["atomic"]["generation"]["raw_text"])
    for field in ("answer_text", "short_answer"):
        draft[field] = draft[field].replace("[ev_003, ev_007]", "[ev_003] [ev_007]")
    return draft


@pytest.mark.parametrize(
    "stage",
    ["generation", "generation_format_repair"],
    ids=["actual-initial", "actual-format-repair"],
)
def test_actual_atomic_grouped_marker_response_remains_rejected(stage):
    case = recorded()["atomic"]
    saved = case[stage]
    assert hashlib.sha256(saved["raw_text"].encode()).hexdigest() == saved["raw_text_sha256"]
    assert case["terminal_error"]["code"] == "CITATION_MARKER_MISMATCH"
    with pytest.raises(ResponseValidationError) as caught:
        parse(public_draft(saved["raw_text"]))
    assert caught.value.code == "CITATION_MARKER_MISMATCH"


def test_singleton_control_is_only_protocol_valid_and_has_local_short_answer_bindings():
    parsed = parse(singleton_control())
    assert parsed["citations"] == ["ev_003", "ev_007"]
    short = [row for row in response_claims(parsed) if row["answer_field"] == "short_answer"]
    assert len(short) == 1
    assert short[0]["evidence_ids"] == ["ev_003", "ev_007"]
    # No semantic checker was run; this assertion does not establish source support.


@pytest.mark.parametrize(
    "mutation,code",
    [
        ("unknown-id", "INVALID_CITATIONS"),
        ("missing-array-id", "CITATION_MARKER_MISMATCH"),
        ("duplicate-array-id", "SCHEMA_VALIDATION"),
        ("malformed-group", "CITATION_MARKER_MISMATCH"),
        ("general-knowledge-citation", "GENERAL_KNOWLEDGE_CITATIONS"),
    ],
    ids=[
        "unknown-id",
        "missing-array-id",
        "duplicate-array-id",
        "malformed-group",
        "general-knowledge",
    ],
)
def test_clarification_does_not_accept_wrong_citations(mutation, code):
    draft = singleton_control()
    mode, ids = "textbook", None
    if mutation == "unknown-id":
        draft["citations"] = ["ev_003", "ev_999"]
        for field in ("answer_text", "short_answer"):
            draft[field] = draft[field].replace("ev_007", "ev_999")
    elif mutation == "missing-array-id":
        draft["citations"] = ["ev_003"]
    elif mutation == "duplicate-array-id":
        draft["citations"].append("ev_003")
    elif mutation == "malformed-group":
        draft["answer_text"] = draft["answer_text"].replace("[ev_003] [ev_007]", "[ev_003 ev_007]")
    else:
        mode, ids = "general_knowledge", []
    with pytest.raises(ResponseValidationError) as caught:
        parse(draft, answer_mode=mode, ids=ids)
    assert caught.value.code == code


def test_actual_chloroplast_short_answer_never_inherits_body_citations():
    case = recorded()["chloroplast"]
    saved = case["generation_format_repair"]
    assert hashlib.sha256(saved["raw_text"].encode()).hexdigest() == saved["raw_text_sha256"]
    claims = response_claims(public_draft(saved["raw_text"]))
    short = next(row for row in claims if row["answer_field"] == "short_answer")
    assert short["evidence_ids"] == []
    bindings = actual_bindings([short], [], {}, False)
    assert bindings == [{"claim_id": short["claim_id"], "citations": []}]
    checker = strict_json(case["joint_check"]["raw_text"])
    reported = next(row for row in checker["claims"] if row["claim_id"] == short["claim_id"])
    assert reported["basis"] == "textbook" and reported["status"] == "supported"
    assert reported["citations"] == []
    normalized, _ = normalize_judgment({"claims": [reported]}, bindings)
    assert normalized["claims"][0]["factual"] is True
    assert normalized["claims"][0]["fragment_ids"] == []
    assert (
        "CHECK_SUPPORT_WITHOUT_SOURCE"
        in case["terminal_error"]["details"]["publication_block"]["structural_issue_codes"]
    )
