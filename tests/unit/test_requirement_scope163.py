"""Required availability/delivery axes stay distinct from optional notes and facts."""

from copy import deepcopy

import pytest
from pydantic import ValidationError

from generation import assertion_provenance_v1 as assertions
from generation import requirement_scope_v1 as scope_api
from generation.checker_encoding import decode, encode

from fixtures_generic163 import authored_parent, checker_labels


def fixture_scope():
    request, parent, fragments = authored_parent()
    coverage = {
        "requirements": [
            {
                "id": "requirement_01",
                "request": request.question,
                "intent": "explanation",
                "objects": ["piston T", "attached load"],
                "relation": "pressure causes movement",
                "conditions": ["valve A is open"],
            }
        ]
    }
    scope = scope_api.freeze_scope(request.question, coverage)
    raw = checker_labels(parent["drafts"][0]["assertion_provenance"], negative_target=False)
    for name in scope_api.DERIVED_SCOPE_FIELDS:
        raw.pop(name, None)
    raw["requirement_scope_version"] = scope_api.POLICY
    raw["requirement_scope_sha256"] = scope["scope_sha256"]
    raw["optional_extensions"] = []
    for row in raw["requirements"]:
        row["necessity"] = "required"
        row["response_missing_information"] = ""
    bank = assertions.source_bank(fragments, parent["evidence"])
    aliased = [{**row, "fragment_id": row["source_id"]} for row in bank]
    return request, coverage, scope, raw, aliased


def normalize(raw, scope):
    return scope_api.normalize_judgment(raw, scope, teaching_mode="direct", answer_mode="textbook")


def assess(typed, coverage, scope, fragments):
    return scope_api.assess_scope_requirements(
        typed, coverage, fragments, scope=scope, answer_mode="textbook", teaching_mode="direct"
    )


def optional_note(scope, *, extension_id="extension_01"):
    return {
        "extension_id": extension_id,
        "parent_requirement_id": scope["core_requirements"][0]["id"],
        "necessity": "optional",
        "extension": "A separate historical example beyond the request.",
        "missing_information": "No history of the example is supplied.",
        "response_missing_information": "The optional example is omitted.",
        "reason": "Authored advisory note only; it is not required knowledge or factual certification.",
    }


def test_optional_omission_does_not_gate_core_and_wire_preserves_server_authority():
    request, coverage, scope, raw, fragments = fixture_scope()
    raw["optional_extensions"] = [optional_note(scope)]
    original = deepcopy(raw)
    from generation.reliability_v5 import response_claims

    _, parent, _ = authored_parent()
    complete_transport = {
        "question": request.question,
        "CONTEXT_COVERAGE": coverage,
        "SENTINEL": "unchanged",
        "CLAIMS": response_claims(parent["drafts"][0]["response"]),
        "ACTUAL_CITATION_BINDINGS": parent["checks"][0]["actual_citation_bindings"],
        "SOURCE_FRAGMENTS": deepcopy(fragments),
        "ASSERTION_PROOFS": assertions.checker_packet(parent["drafts"][0]["assertion_provenance"]),
    }
    bound = scope_api.packet(complete_transport, scope)
    assert bound["SENTINEL"] == "unchanged" and bound["REQUIREMENT_SCOPE"] == scope
    roundtrip = decode(encode(bound))
    assert roundtrip == bound
    assert roundtrip["REQUIREMENT_SCOPE"] == scope
    assert scope["core_requirements"][0]["conditions"] == ["valve A is open"]
    model = scope_api.internal_model(assertions.AssertionCheck)
    wire = scope_api.wire_model(model, scope)
    assert all(name not in wire.model_fields for name in scope_api.DERIVED_SCOPE_FIELDS)
    assert wire.model_validate(raw).model_dump() == raw
    typed, receipt = normalize(raw, scope)
    assert model.model_validate(typed).model_dump() == typed
    assert typed["core_knowledge_complete"] is True
    assert typed["complete_answer"] is True and typed["coverage"] == "full"
    assert typed["missing_facets"] == []
    contract, defects, assessment = assess(typed, coverage, scope, fragments)
    assert contract == defects == []
    assert assessment["optional_extensions"] == raw["optional_extensions"]
    assert not receipt["optional_extensions_gate_core"] and not receipt["factual_gates_waived"]
    assert raw == original


def test_source_sufficient_with_named_response_omission_is_structurally_valid_but_incomplete():
    _, coverage, scope, raw, fragments = fixture_scope()
    row = raw["requirements"][0]
    row.update(
        response_coverage="partial",
        response_missing_information="The valve-open condition is omitted.",
    )
    original = deepcopy(raw)
    typed, receipt = normalize(raw, scope)
    contract, defects, assessment = assess(typed, coverage, scope, fragments)
    assert contract == []
    assert typed["core_knowledge_complete"] is True and typed["complete_answer"] is False
    assert typed["missing_facets"] == ["The valve-open condition is omitted."]
    assert row["missing_information"] == ""
    assert any(issue["code"] == "SUFFICIENT_CONTEXT_UNDERUSED" for issue in defects)
    assert assessment["technical_valid"] is True
    assert receipt["model_decision_fields_changed"] is False and raw == original


def test_real_required_source_gap_is_not_full_core_even_with_honest_limitation():
    _, coverage, scope, raw, fragments = fixture_scope()
    row = raw["requirements"][0]
    row.update(
        sufficiency="partial",
        missing_information="The chamber-pressure condition is not supplied.",
        response_coverage="limitation",
        response_missing_information="",
    )
    typed, _ = normalize(raw, scope)
    contract, _, _ = assess(typed, coverage, scope, fragments)
    assert contract == []
    assert typed["core_knowledge_complete"] is False and typed["coverage"] != "full"
    assert typed["missing_facets"] == ["The chamber-pressure condition is not supplied."]
    assert (
        typed["complete_answer"] is True
    )  # Honest available-content completion, not full knowledge.


def test_sufficient_source_plus_named_source_gap_remains_a_contract_failure():
    _, coverage, scope, raw, fragments = fixture_scope()
    row = raw["requirements"][0]
    row["missing_information"] = "A required causal premise is unavailable."
    typed, _ = normalize(raw, scope)
    contract, _, _ = assess(typed, coverage, scope, fragments)
    assert any(issue["code"] == "REQUIREMENT_SUFFICIENCY_CONTRADICTION" for issue in contract)
    assert typed["coverage"] == "unknown" and typed["core_knowledge_complete"] is None
    assert row["missing_information"] == "A required causal premise is unavailable."


@pytest.mark.parametrize(
    "field,value",
    [
        ("missing_information", None),
        ("missing_information", "  "),
        ("response_missing_information", None),
        ("response_missing_information", "\n "),
        ("necessity", "optional"),
        ("necessity", None),
    ],
)
def test_missing_null_whitespace_or_downgraded_core_is_not_filled_or_repaired(field, value):
    _, _, scope, raw, _ = fixture_scope()
    raw["requirements"][0][field] = value
    original = deepcopy(raw)
    with pytest.raises((ValueError, ValidationError)):
        normalize(raw, scope)
    assert raw == original


@pytest.mark.parametrize(
    "field", ["missing_information", "response_missing_information", "necessity"]
)
def test_missing_required_decision_field_is_not_legacy_migrated(field):
    _, _, scope, raw, _ = fixture_scope()
    del raw["requirements"][0][field]
    with pytest.raises((ValueError, ValidationError)):
        normalize(raw, scope)


@pytest.mark.parametrize(
    "defect",
    [
        "foreign_core",
        "duplicate_core",
        "missing_core",
        "optional_parent",
        "duplicate_optional",
        "explicit_clause_as_optional",
        "model_summary",
    ],
)
def test_identity_and_optional_boundaries_cannot_hide_an_explicit_obligation(defect):
    _, _, scope, raw, _ = fixture_scope()
    if defect == "foreign_core":
        raw["requirements"][0]["requirement_id"] = "foreign_requirement"
    elif defect == "duplicate_core":
        raw["requirements"].append(deepcopy(raw["requirements"][0]))
    elif defect == "missing_core":
        raw["requirements"] = []
    elif defect == "optional_parent":
        raw["optional_extensions"] = [optional_note(scope)]
        raw["optional_extensions"][0]["parent_requirement_id"] = "foreign_requirement"
    elif defect == "duplicate_optional":
        raw["optional_extensions"] = [optional_note(scope), optional_note(scope)]
    elif defect == "explicit_clause_as_optional":
        raw["optional_extensions"] = [optional_note(scope)]
        raw["optional_extensions"][0]["extension"] = scope["core_requirements"][0]["request"]
    elif defect == "model_summary":
        raw["complete_answer"] = True
    with pytest.raises((ValueError, ValidationError)):
        normalize(raw, scope)


@pytest.mark.parametrize(
    "defect",
    [
        "question_absent",
        "coverage_absent",
        "question_changed",
        "condition_changed",
        "request_changed",
        "core_optional",
    ],
)
def test_packet_fresh_binding_preserves_actual_question_request_and_conditions(defect):
    request, coverage, scope, _, _ = fixture_scope()
    data = {"question": request.question, "CONTEXT_COVERAGE": deepcopy(coverage)}
    if defect == "question_absent":
        del data["question"]
    elif defect == "coverage_absent":
        del data["CONTEXT_COVERAGE"]
    elif defect == "question_changed":
        data["question"] += " Remove the valve condition."
    elif defect == "condition_changed":
        data["CONTEXT_COVERAGE"]["requirements"][0]["conditions"] = ["valve A is closed"]
    elif defect == "request_changed":
        data["CONTEXT_COVERAGE"]["requirements"][0]["request"] = "A different question."
    elif defect == "core_optional":
        data["CONTEXT_COVERAGE"]["requirements"][0]["necessity"] = "optional"
    with pytest.raises(ValueError):
        scope_api.packet(data, scope)


def test_optional_delivered_unsupported_fact_cannot_be_promoted_by_core_summary():
    _, _, scope, raw, _ = fixture_scope()
    raw["optional_extensions"] = [optional_note(scope)]
    raw["body_ok"] = False
    raw["claims"][0]["status"] = "partial"
    raw["claims"][0]["proof_audit"].update(
        all_predicates_entailed=False,
        causal_bridges_entailed=False,
        missing_predicates=["Authored delivered statement has no causal proof."],
    )
    original = deepcopy(raw)
    typed, receipt = normalize(raw, scope)
    assert typed["complete_answer"] is True and typed["core_knowledge_complete"] is True
    assert typed["body_ok"] is False and typed["claims"][0]["status"] == "partial"
    assert not receipt["factual_gates_waived"] and raw == original


def test_absent_private_policy_preserves_legacy_admission_and_unknown_policy_stops():
    request, _, _, _, _ = fixture_scope()
    teaching = {"teaching_mode": "direct", "online_check": True}
    assert request.requirement_scope_policy is None
    assert scope_api.eligible(request, teaching) is False
    request.requirement_scope_policy = scope_api.POLICY
    assert scope_api.eligible(request, teaching) is True
    request.requirement_scope_policy = "unknown_scope"
    with pytest.raises(ValueError):
        scope_api.eligible(request, teaching)
