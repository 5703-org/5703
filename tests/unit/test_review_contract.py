"""Authored external-review controls and a separately labelled retained native replay."""

from copy import deepcopy
import hashlib
import json

import pytest

from evaluation.review_contract import (
    ReviewContractError,
    ReviewSession,
    assess_review,
    freeze_review_contract,
    strict_review_json,
)

FLAGS = ("task_fit", "no_disclosure", "no_invented_candidate")
SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "schema_version": {"type": "string", "const": "authored_review_v1"},
        "verdict": {"type": "string", "enum": ["PASS", "FAIL", "UNAVAILABLE"]},
        **{flag: {"type": "boolean"} for flag in FLAGS},
        "reason": {"type": "string", "minLength": 1, "maxLength": 1000},
    },
    "required": ["schema_version", "verdict", *FLAGS, "reason"],
}
CRITERIA = {"flags": list(FLAGS), "instruction": "Judge only this unchanged released surface."}
PROJECTION = {
    "answer_text": "Which stated feature matters to the next step, and why?",
    "citations": [],
}


def contract():
    return freeze_review_contract(SCHEMA, CRITERIA, PROJECTION)


def review(verdict="PASS", **changes):
    value = {
        "schema_version": "authored_review_v1",
        "verdict": verdict,
        **{flag: True for flag in FLAGS},
        "reason": "Authored mock judgment, not a historical provider response.",
    }
    value.update(changes)
    return json.dumps(value)


@pytest.mark.parametrize("verdict", ["PASS", "FAIL", "UNAVAILABLE"])
def test_availability_and_content_result_are_separate(verdict):
    session = ReviewSession(contract())
    result = session.consume(review(verdict))
    assert result.contract_valid is True
    assert result.content_result == verdict
    assert result.evaluator_availability == (
        "UNAVAILABLE" if verdict == "UNAVAILABLE" else "AVAILABLE"
    )
    assert result.teaching_quality_pass is (verdict == "PASS")
    assert result.review["verdict"] == verdict
    assert session.closed and not session.correction_available
    with pytest.raises(ReviewContractError, match="REVIEW_CORRECTION_NOT_AVAILABLE"):
        session.correction_messages()


@pytest.mark.parametrize(
    ("raw", "code"),
    [
        ('{"verdict":"PASS","verdict":"FAIL"}', "DUPLICATE_JSON_KEY"),
        ('{"verdict":"FAIL","verdict":"FAIL"}', "DUPLICATE_JSON_KEY"),
        ('{"nested":{"flag":true,"flag":false}}', "DUPLICATE_JSON_KEY"),
        (r'{"a":true,"\u0061":false}', "DUPLICATE_JSON_KEY"),
        ('{"value":NaN}', "NONFINITE_JSON"),
        ('{"value":Infinity}', "NONFINITE_JSON"),
        ('{"value":1e309}', "NONFINITE_JSON"),
        ('{"verdict":', "JSON_SYNTAX_INVALID"),
        ("{} {}", "JSON_SYNTAX_INVALID"),
        ("[]", "JSON_OBJECT_REQUIRED"),
        (b"\xff", "JSON_UTF8_INVALID"),
        (r'{"value":"\ud800"}', "JSON_UTF8_INVALID"),
    ],
)
def test_authored_malformed_json_is_rejected_without_recovering_a_verdict(raw, code):
    with pytest.raises(ReviewContractError) as caught:
        strict_review_json(raw)
    assert caught.value.code == code
    result = assess_review(raw, contract())
    assert result.content_result == "UNAVAILABLE"
    assert result.evaluator_availability == "UNAVAILABLE"
    assert result.contract_valid is False
    assert result.review is None
    assert result.teaching_quality_pass is False


@pytest.mark.parametrize(
    "change",
    [
        {"task_fit": 1},
        {"schema_version": "wrong"},
        {"reason": " "},
        {"reason": "x" * 1001},
        {"unexpected": "untrusted-provider-value"},
    ],
)
def test_schema_failures_have_only_known_structural_diagnostics(change):
    result = assess_review(review(**change), contract())
    assert result.diagnostic_code == "REVIEW_SCHEMA_INVALID"
    assert result.evaluator_availability == "UNAVAILABLE"
    assert result.review is None
    assert "untrusted-provider-value" not in str(result.to_dict())


def test_missing_flag_and_false_flag_cannot_be_dropped_to_get_pass():
    value = json.loads(review())
    del value["no_disclosure"]
    missing = assess_review(json.dumps(value), contract())
    assert missing.diagnostic_code == "REVIEW_SCHEMA_INVALID"
    assert "no_disclosure" in missing.field_errors
    inconsistent = assess_review(review(no_disclosure=False), contract())
    assert inconsistent.diagnostic_code == "REVIEW_VERDICT_FLAGS_INCONSISTENT"
    failed = assess_review(review("FAIL", no_disclosure=False), contract())
    assert failed.contract_valid and failed.evaluator_availability == "AVAILABLE"
    assert failed.content_result == "FAIL" and not failed.teaching_quality_pass


def test_one_authored_duplicate_correction_preserves_bound_context_and_valid_fail():
    frozen = contract()
    session = ReviewSession(frozen)
    raw = '{"verdict":"PASS","verdict":"FAIL"}'  # Authored, not DS11's lost raw.
    result = session.consume(raw)
    assert result.diagnostic_code == "DUPLICATE_JSON_KEY"
    assert session.correction_available and not session.closed
    feedback = json.loads(session.correction_messages()[1]["content"])
    assert feedback["invalid_review_text"] == raw
    assert feedback["diagnostic"] == {"code": "DUPLICATE_JSON_KEY", "field_errors": []}
    assert feedback["binding_sha256"] == frozen.binding_sha256
    assert feedback["criteria_sha256"] == frozen.criteria_sha256
    assert feedback["released_projection_sha256"] == frozen.released_projection_sha256
    assert feedback["response_schema_sha256"] == frozen.response_schema_sha256
    assert feedback["criteria"] == CRITERIA
    assert feedback["released_projection"] == PROJECTION
    assert feedback["response_schema"] == SCHEMA
    assert session.corrections_used == 1
    replacement = session.consume(review("FAIL", task_fit=False))
    assert replacement.contract_valid and replacement.evaluator_availability == "AVAILABLE"
    assert replacement.content_result == "FAIL" and not replacement.teaching_quality_pass
    assert session.closed and not session.correction_available
    with pytest.raises(ReviewContractError, match="REVIEW_CORRECTION_NOT_AVAILABLE"):
        session.correction_feedback()


def test_one_structure_replacement_must_include_every_original_flag():
    session = ReviewSession(contract())
    session.consume("{}")
    session.correction_messages()
    corrected = session.consume(review())
    assert corrected.contract_valid and corrected.teaching_quality_pass
    assert set(corrected.review) == set(SCHEMA["required"])
    assert session.closed and session.corrections_used == 1


def test_repeat_invalid_is_terminal_and_cannot_be_silently_retried():
    session = ReviewSession(contract())
    session.consume('{"a":1,"a":2}')
    session.correction_feedback()
    failed = session.consume('{"b":1,"b":2}')
    assert failed.diagnostic_code == "DUPLICATE_JSON_KEY"
    assert failed.content_result == "UNAVAILABLE" and not failed.teaching_quality_pass
    assert session.closed and not session.correction_available
    with pytest.raises(ReviewContractError, match="REVIEW_CORRECTION_NOT_AVAILABLE"):
        session.correction_messages()
    with pytest.raises(ReviewContractError, match="REVIEW_SESSION_STATE_INVALID"):
        session.consume(review())


def test_reconsume_without_reserving_correction_is_rejected():
    session = ReviewSession(contract())
    session.consume("{}")
    with pytest.raises(ReviewContractError, match="REVIEW_SESSION_STATE_INVALID"):
        session.consume(review())


def test_bound_input_snapshots_cannot_be_changed_between_attempts():
    criteria, projection, schema = deepcopy(CRITERIA), deepcopy(PROJECTION), deepcopy(SCHEMA)
    frozen = freeze_review_contract(schema, criteria, projection)
    criteria["instruction"] = "Changed criterion"
    projection["answer_text"] = "Changed learner answer"
    del schema["properties"]["no_disclosure"]
    session = ReviewSession(frozen)
    session.consume("{}")
    feedback = session.correction_feedback()
    assert feedback["criteria"] == CRITERIA
    assert feedback["released_projection"] == PROJECTION
    assert feedback["response_schema"] == SCHEMA
    assert (
        freeze_review_contract(SCHEMA, criteria, PROJECTION).binding_sha256 != frozen.binding_sha256
    )
    assert (
        freeze_review_contract(SCHEMA, CRITERIA, projection).binding_sha256 != frozen.binding_sha256
    )
    with pytest.raises(AttributeError):
        session.contract = contract()


def test_unknown_schema_constraints_are_rejected_instead_of_ignored():
    schema = deepcopy(SCHEMA)
    schema["properties"]["task_fit"]["const"] = True
    with pytest.raises(ReviewContractError, match="UNSUPPORTED_REVIEW_SCHEMA"):
        freeze_review_contract(schema, CRITERIA, PROJECTION)


def test_invalid_utf8_and_size_never_offer_a_correction():
    for raw in (b"\xff", "x" * 131073):
        session = ReviewSession(contract())
        result = session.consume(raw)
        assert not result.contract_valid and session.closed
        assert not session.correction_available


# DS11 native bad raw SHA256: 52dd81a2a2ec16a28646112041238660f7f5477f7ae92397053cf63cdc569ddd
_DS11_NATIVE_BAD_RAW = (
    '{"claims":[{"claim_id":"claim_365fff999efdec98951e3f4c_1","basis":"problem_i'
    'nput","status":"supported","problem_quote":"Look at the given equation 5x - '
    '4 = 21","reason":"The learner\'s problem explicitly states the equation 5x - '
    "4 = 21 and the goal of isolating x by equality-preserving inverse operations"
    "; the rest of the sentence is procedural framing. Exact substring present in"
    ' answer_text and matching the learner-provided problem."},{"claim_id":"claim'
    '_b927ee4dd0fcbe2ee65f07a3_1","basis":"nonfactual","status":"supported","reas'
    'on":"This is a procedural, structural question asking the learner to identif'
    "y a condition and test a candidate step's fit; it makes no scientific assert"
    'ion."}],"body_ok":true,"specific_help":true,"scope_ok":true,"suggestions_ok"'
    ':true,"evidence_display_ok":true,"cumulative_ok":true,"complete_answer":fals'
    'e,"coverage":"supported_partial","missing_facets":["The final selected inver'
    'se operation and the reason it must be applied first"],"limitations_explicit'
    '":false,"reason":"The question remains purely structural at H1: it asks whic'
    "h condition any valid first treatment must account for and asks the learner "
    "to judge fit, leaving the inverse operation unanswered. No scientific assert"
    "ion is certified by the single generic source fragment, and no disclosure of"
    " the answer occurs. The question is actionable, but because the requested cu"
    "rrent step is intentionally withheld at hint level 1, coverage is supported_"
    'partial and complete_answer is false.","repair_fragment_ids":[],"attempt_eva'
    'luation_ok":true,"tutor_question_ok":true,"requirements":[{"requirement_id":'
    '"requirement_01","relevance":"related","sufficiency":"partial","evidence":[{'
    '"evidence_id":"ev_001","fragment_id":"F001","quote":"An equality remains val'
    'id when the same permissible operation is applied to both sides."}],"conditi'
    'ons_preserved":true,"response_coverage":"partial","missing_information":"No '
    "source states that the first operation must undo subtraction of 4 from 5x in"
    " 5x - 4 = 21, nor the specific structural relation needed to select the firs"
    't inverse operation.","reason":"The source address equality preservation gen'
    'erally but do not establish the task-specific first-step selection."}],"non_'
    'repetitive_next_action":true}'
)

# DS11 native corrected raw SHA256: 76542996bb8409cc9f7c0bb7edea97014fba4cb47b15233a0450500e3f56abaf
_DS11_NATIVE_CORRECTED_RAW = (
    '{"claims":[{"claim_id":"claim_365fff999efdec98951e3f4c_1","basis":"nonfactua'
    'l","reason":"Procedural guidance directing the learner to attend to the give'
    "n equation and the equality-preserving constraint; it makes no scientific as"
    'sertion and needs no citation."},{"claim_id":"claim_b927ee4dd0fcbe2ee65f07a3'
    '_1","basis":"nonfactual","reason":"A request asking the learner to identify '
    "a structural feature and judge whether a candidate step fits; purely procedu"
    'ral, contains no scientific assertion."}],"body_ok":true,"specific_help":tru'
    'e,"scope_ok":true,"suggestions_ok":true,"evidence_display_ok":true,"cumulati'
    've_ok":true,"complete_answer":false,"coverage":"supported_partial","missing_'
    'facets":["The learner\'s own selection of the first inverse operation and the'
    ' reason it starts isolating x"],"limitations_explicit":true,"reason":"The dr'
    "aft is a hint-stage (H1) prompt. No substantive candidate option is actually"
    " supplied: the recorded step goal names only the category 'first inverse ope"
    "ration,' and no task-linked candidate appears in EVIDENCE_DOCUMENTS or PRACT"
    "ICE_CONTEXT. The plan's neutral-structure branch therefore applies, and the "
    "visible question asks which part of the whole structure a first treatment mu"
    "st account for and why fit matters, leaving the selection unanswered. Both c"
    "laims are nonfactual procedural guidance, so no textbook citation applies; n"
    "o factual assertion is uncited. The withheld selection and its basis are the"
    " deliberately deferred task in hint mode, not an evidence gap. No prior expo"
    'sure exists, and no suggested content or evidence markers appear.","repair_f'
    'ragment_ids":[],"attempt_evaluation_ok":true,"tutor_question_ok":true,"requi'
    'rements":[{"requirement_id":"requirement_01","relevance":"related","sufficie'
    'ncy":"partial","evidence":[{"evidence_id":"ev_001","fragment_id":"F001","quo'
    'te":"An equality remains valid when the same permissible operation is applie'
    'd to both sides."}],"conditions_preserved":true,"response_coverage":"deferre'
    'd_for_hint","missing_information":"The sources state the equality-preservati'
    "on principle but do not identify the specific first inverse operation or its"
    " relation to the structure of 5x - 4 = 21; that selection is deliberately wi"
    'thheld at this hint stage.","reason":"The source supports the equality-prese'
    "rving constraint referenced by the current step, but the actual first-invers"
    "e-step selection and its structural justification are reserved for the learn"
    'er\'s reply."}],"non_repetitive_next_action":true}'
)


def test_replay_retained_native_schema_error_and_correction_not_lost_external_json():
    from generation.checker_contract import LEGACY_POLICY, correction_limit, schema_issue
    from generation.reliability_v5 import ReliableCheckV5
    from pydantic import ValidationError

    assert hashlib.sha256(_DS11_NATIVE_BAD_RAW.encode()).hexdigest() == (
        "52dd81a2a2ec16a28646112041238660f7f5477f7ae92397053cf63cdc569ddd"
    )
    assert hashlib.sha256(_DS11_NATIVE_CORRECTED_RAW.encode()).hexdigest() == (
        "76542996bb8409cc9f7c0bb7edea97014fba4cb47b15233a0450500e3f56abaf"
    )
    bad = strict_review_json(_DS11_NATIVE_BAD_RAW)
    with pytest.raises(ValidationError) as caught:
        ReliableCheckV5.model_validate(bad)
    issues = schema_issue(caught.value)
    assert issues[0]["code"] == "CHECKER_SCHEMA_INVALID"
    assert any(row["error_type"] == "extra_forbidden" for row in issues[0]["field_errors"])
    assert correction_limit(LEGACY_POLICY, [issues]) == 1
    corrected = ReliableCheckV5.model_validate(strict_review_json(_DS11_NATIVE_CORRECTED_RAW))
    assert corrected.specific_help is True
    assert corrected.complete_answer is False
    # This proves only a retained native schema transition, not teaching acceptance
    # or recovery of external request05's missing duplicate-key review content.
