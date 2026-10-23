"""Source gaps, delivery omissions and context defects remain independent."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket

import pytest
from pydantic import ValidationError

from generation import GenerationService, RequestBudget
from generation.qualification_v1 import ReliableQualificationCheck, decision_derivative
from generation.requirement_axes_v1 import (
    QualificationRequirementCheck,
    assess_qualification_requirements,
    requirement_transport_notes,
    derive_requirement_summary,
)
from test_context_qualification_v1 import request, verdict
from test_enhancement_generation import Script, answer


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Requirement-axis controls cannot use network or DNS")

    for name in ("socket", "create_connection", "getaddrinfo"):
        monkeypatch.setattr(socket, name, denied)


def gate_fixture():
    fragment = dict(
        fragment_id="F001",
        evidence_id="ev_001",
        exact_text="Under condition A, particles move left.",
        complete_block=True,
    )
    requirement = dict(
        requirement_id="requirement_01",
        relevance="related",
        sufficiency="sufficient",
        evidence=[dict(evidence_id="ev_001", fragment_id="F001", quote=fragment["exact_text"])],
        conditions_preserved=True,
        response_coverage="covered",
        missing_information="",
        reason="The supplied passage establishes the requested direction under A; delivered.",
    )
    judgment = dict(
        requirements=[requirement],
        coverage="full",
        missing_facets=[],
        complete_answer=True,
        limitations_explicit=False,
        non_repetitive_next_action=True,
    )
    coverage = dict(requirements=[dict(id="requirement_01", request="Direction under A")])
    return judgment, coverage, [fragment]


def assess(judgment, coverage, fragments, **changes):
    modes = dict(answer_mode="textbook", teaching_mode="direct")
    modes.update(changes)
    return assess_qualification_requirements(
        judgment,
        coverage,
        fragments,
        **modes,
    )


def test_complete_answer_has_empty_source_gap_and_no_coverage_defect():
    fixture = gate_fixture()
    before = deepcopy(fixture)
    contract, defects, result = assess(*fixture)
    assert not contract and not defects
    assert result["status"] == "sufficient"
    assert result["source_scope"] == "complete_submitted_source_fragments"
    assert fixture == before


def test_genuine_missing_required_knowledge_is_named_and_cannot_be_full_coverage():
    judgment, coverage, fragments = gate_fixture()
    coverage["requirements"][0]["request"] = "Direction under A and the transport rate"
    row = judgment["requirements"][0]
    row.update(
        sufficiency="partial",
        missing_information="The required transport rate under A is unavailable.",
        response_coverage="limitation",
        response_missing_information="",
        reason="The passage supplies direction but no requested rate; the answer names this limit.",
    )
    judgment.update(
        coverage="supported_partial",
        missing_facets=["Transport rate under A"],
        limitations_explicit=True,
    )
    summary = derive_requirement_summary(
        judgment["requirements"], limitations_explicit=True, teaching_mode="direct"
    )
    judgment.update(
        {name: summary[name] for name in ("coverage", "missing_facets", "complete_answer")}
    )
    assert assess(judgment, coverage, fragments)[:2] == ([], [])
    row["response_coverage"] = "covered"
    summary = derive_requirement_summary(
        judgment["requirements"], limitations_explicit=True, teaching_mode="direct"
    )
    judgment.update(
        {name: summary[name] for name in ("coverage", "missing_facets", "complete_answer")}
    )
    assert "INSUFFICIENT_CONTEXT_FULL_COVERAGE" in {
        item["code"] for item in assess(judgment, coverage, fragments)[1]
    }
    row["missing_information"] = ""
    assert "REQUIREMENT_GAP_UNSPECIFIED" in {
        item["code"] for item in assess(judgment, coverage, fragments)[0]
    }


def test_answer_omission_is_not_normalized_into_missing_source_information():
    judgment, coverage, fragments = gate_fixture()
    judgment["requirements"][0].update(
        response_coverage="partial", reason="The answer omits the requested direction under A."
    )
    judgment.update(coverage="supported_partial", missing_facets=["Direction under A"])
    before = deepcopy(judgment)
    contract, defects, _ = assess(judgment, coverage, fragments)
    assert {item["code"] for item in contract} == {"LEGACY_RESPONSE_GAP_UNASSESSED"}
    assert {item["code"] for item in defects} == {"SUFFICIENT_CONTEXT_UNDERUSED"}
    assert judgment == before and judgment["requirements"][0]["missing_information"] == ""


@pytest.mark.parametrize("state", ["absent", "null", "whitespace", "invalid_type"])
def test_missing_source_gap_field_never_becomes_explicit_empty(state):
    judgment, _, _ = gate_fixture()
    row = judgment["requirements"][0]
    if state == "absent":
        row.pop("missing_information")
    else:
        row["missing_information"] = dict(null=None, whitespace=" \n\t", invalid_type=False)[state]
    before = deepcopy(row)
    assert requirement_transport_notes([row])[0]["source_gap_state"] == state
    with pytest.raises(ValidationError):
        QualificationRequirementCheck.model_validate(row)
    assert row == before


@pytest.mark.parametrize("state", ["empty", "named"])
def test_valid_explicit_source_gap_strings_remain_exact(state):
    row = gate_fixture()[0]["requirements"][0]
    row["missing_information"] = "" if state == "empty" else "A required rate is not supplied."
    before = deepcopy(row)
    assert requirement_transport_notes([row])[0]["source_gap_state"] == state
    assert QualificationRequirementCheck.model_validate(row).model_dump() == before


@pytest.mark.parametrize("container", [None, {}, [None]])
def test_malformed_requirement_containers_fail_finitely_without_default_filling(container):
    raw = {"requirements": container}
    before = deepcopy(raw)
    with pytest.raises(ValueError, match="QUALIFICATION_REQUIREMENT_CONTAINER_INVALID"):
        decision_derivative(raw)
    assert raw == before


@pytest.mark.parametrize("case", ["absent_proof", "inapplicable_gap", "unrelated_proof", "facet"])
def test_nearby_cross_field_contradictions_fail_without_rewriting(case):
    judgment, coverage, fragments = gate_fixture()
    row = judgment["requirements"][0]
    code = {
        "absent_proof": "REQUIREMENT_ABSENT_WITH_EVIDENCE",
        "inapplicable_gap": "REQUIREMENT_INAPPLICABLE_WITH_GAP",
        "unrelated_proof": "REQUIREMENT_UNRELATED_WITH_PROOF",
        "facet": "MISSING_FACETS_WITH_NO_REQUIREMENT_GAP",
    }[case]
    if case == "absent_proof":
        row.update(sufficiency="absent", missing_information="Required direction absent.")
    elif case == "inapplicable_gap":
        row.update(sufficiency="not_applicable", evidence=[], missing_information="Invented gap.")
    elif case == "unrelated_proof":
        row["relevance"] = "unrelated"
    else:
        judgment["missing_facets"] = ["Direction already delivered"]
    before = deepcopy(judgment)
    assert code in {item["code"] for item in assess(judgment, coverage, fragments)[0]}
    assert judgment == before


def test_actual_absent_source_has_no_proof_and_requires_named_information():
    judgment, coverage, _ = gate_fixture()
    judgment["requirements"][0].update(
        relevance="unrelated",
        sufficiency="absent",
        evidence=[],
        missing_information="No submitted passage establishes the requested direction.",
        response_coverage="limitation",
        response_missing_information="",
    )
    judgment.update(
        coverage="supported_partial", missing_facets=["Direction"], limitations_explicit=True
    )
    summary = derive_requirement_summary(
        judgment["requirements"], limitations_explicit=True, teaching_mode="direct"
    )
    judgment.update(
        {name: summary[name] for name in ("coverage", "missing_facets", "complete_answer")}
    )
    assert assess(judgment, coverage, [])[:2] == ([], [])


@pytest.mark.parametrize(
    "case,expected_code",
    [
        ("condition", "REQUIREMENT_CONDITION_LOST"),
        ("limit", "REQUIREMENT_LIMITATION_MISSING"),
        ("quote", "REQUIREMENT_SOURCE_QUOTE_INVALID"),
        ("proof", "REQUIREMENT_EVIDENCE_MISSING"),
        ("sufficient_gap", "REQUIREMENT_SUFFICIENCY_CONTRADICTION"),
        ("full_gap", "FULL_COVERAGE_WITH_REQUIREMENT_GAP"),
        ("hint_in_direct", "REQUIRED_CONTENT_OMITTED"),
    ],
)
def test_existing_nearby_gates_remain_effective(case, expected_code):
    judgment, coverage, fragments = gate_fixture()
    row = judgment["requirements"][0]
    if case == "condition":
        row["conditions_preserved"] = False
    elif case == "limit":
        row.update(
            sufficiency="partial",
            missing_information="The requested rate is missing.",
            response_coverage="limitation",
        )
        judgment["coverage"] = "supported_partial"
    elif case == "quote":
        row["evidence"][0]["quote"] = "Invented direction."
    elif case == "proof":
        row["evidence"] = []
    elif case == "sufficient_gap":
        row["missing_information"] = "A purported missing direction."
    elif case == "full_gap":
        row.update(sufficiency="partial", missing_information="Requested rate absent.")
    else:
        row["response_coverage"] = "deferred_for_hint"
    before = deepcopy(judgment)
    contract, defects, _ = assess(judgment, coverage, fragments)
    assert expected_code in {item["code"] for item in contract + defects}
    assert judgment == before


def test_hint_deferral_and_general_inapplicability_do_not_invent_gaps():
    judgment, coverage, fragments = gate_fixture()
    judgment["requirements"][0]["response_coverage"] = "deferred_for_hint"
    assert assess(judgment, coverage, fragments, teaching_mode="hint")[:2] == ([], [])
    row = judgment["requirements"][0]
    row.update(sufficiency="not_applicable", evidence=[], response_coverage="covered")
    assert assess(judgment, coverage, [], answer_mode="general_knowledge")[:2] == ([], [])


def test_permitted_hint_deferral_is_not_a_missing_facet_at_current_help_level():
    judgment, coverage, fragments = gate_fixture()
    judgment["requirements"][0].update(
        response_coverage="deferred_for_hint", reason="Later reasoning is deliberately deferred."
    )
    assert assess(judgment, coverage, fragments, teaching_mode="hint")[:2] == ([], [])
    judgment["missing_facets"] = ["Deliberately deferred later reasoning"]
    before = deepcopy(judgment)
    contract, _, _ = assess(judgment, coverage, fragments, teaching_mode="hint")
    assert {row["code"] for row in contract} == {"MISSING_FACETS_WITH_NO_REQUIREMENT_GAP"}
    assert judgment == before


def test_historical116_remains_invalid_raw_and_semantic_decisions_unchanged():
    path = Path(__file__).parents[1] / "fixtures/qualification116_requirement_response.json"
    fixture = json.loads(path.read_bytes())
    raw_text = fixture["raw_text"]
    assert hashlib.sha256(raw_text.encode()).hexdigest() == fixture["raw_text_sha256"]
    raw = json.loads(raw_text)
    before = deepcopy(raw)
    derivative, notes = decision_derivative(raw)
    typed = ReliableQualificationCheck.model_validate(derivative).model_dump()
    contract, defects, result = assess(typed, fixture["coverage"], fixture["requirement_fragments"])
    assert {item["code"] for item in contract} == {"REQUIREMENT_GAP_UNSPECIFIED"}
    assert "INSUFFICIENT_CONTEXT_FULL_COVERAGE" in {item["code"] for item in defects}
    assert result["status"] == "partial"
    assert typed["requirements"] == raw["requirements"]
    assert typed["claims"] == raw["claims"]
    assert typed["qualification_assessments"] == raw["qualification_assessments"]
    assert notes["requirement_axes"][0]["source_gap_state"] == "empty"
    assert raw == before
    # The original full answer includes these reported "missing" delivered facets.
    assert "net water movement is out of the cell" in fixture["answer_text"]
    assert "net water movement is into the cell" in fixture["answer_text"]
    assert "retains its normal volume" in fixture["answer_text"]
    sources = {row["fragment_id"]: row["exact_text"] for row in fixture["requirement_fragments"]}
    assert "maintain normal volume and shape in an isotonic solution" in sources["F015"]
    assert "water to rush into the RBC" in sources["F021"]
    assert "water to rush out of the cell" in sources["F023"]


@pytest.mark.parametrize("defect", ["complete", "context", "citation", "source_gap", "omission"])
def test_normal_pipeline_keeps_each_gate_and_raw_reply_independent(defect):
    saved = {}

    def judge(messages):
        value = verdict(messages)
        if defect == "context":
            row = value["qualification_assessments"][0]
            row.update(
                context_status="conflict", limiting_quotes=deepcopy(row["supporting_quotes"])
            )
        elif defect == "citation":
            value["body_ok"] = False
            row = value["claims"][0]
            row["status"] = "partial"
            for unit in row["units"]:
                unit["status"] = "partial"
        elif defect == "source_gap":
            value["requirements"][0].update(sufficiency="partial", missing_information="")
        elif defect == "omission":
            value["requirements"][0].update(
                response_coverage="partial",
                reason="An authored required requested part is omitted.",
            )
            value.update(
                coverage="supported_partial",
                missing_facets=["Required requested part"],
                complete_answer=False,
            )
        saved["raw"] = deepcopy(value)
        return value

    adapter = Script([answer(), judge])
    out = GenerationService(adapter).generate(request(), RequestBudget(max_calls=2))
    check = out.checks[0]
    assert json.loads(check["raw_text"]) == saved["raw"]
    assert len(adapter.calls) == 2
    assert [attempt["stage"] for attempt in out.attempts] == ["generation", "joint_check"]
    assert out.succeeded is (defect == "complete")
    if defect in {"source_gap", "omission"}:
        assert out.error["code"] == "QUALIFICATION_CONTRACT_INVALID"
        expected = (
            "REQUIREMENT_GAP_UNSPECIFIED"
            if defect == "source_gap"
            else "LEGACY_RESPONSE_GAP_UNASSESSED"
        )
        assert expected in str(check["checker_inconsistencies"])
    else:
        assert check["validation_state"] == "validated"
        assert check["semantic_sufficiency"]["status"] == "sufficient"
        assert check["checker_inconsistencies"] == []
