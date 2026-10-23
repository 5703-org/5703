"""The private proof contract must not advertise the incompatible shared variants."""

from copy import deepcopy
from pathlib import Path
import pytest
from pydantic import TypeAdapter, ValidationError
from generation import assertion_provenance_v1 as assertions
from generation import requirement_scope_v1 as required
from test_assertion_provenance161 import authored_claims, compiled

ROOT = Path(__file__).resolve().parents[2]


def test_shared_prompt_unchanged_private_prompt_has_one_proof_bound_contract():
    path = ROOT / "generation/prompts/joint_check_v5.txt"
    original = path.read_text(encoding="utf-8")
    assert "- evidence_limitation:" in original
    assert '"basis":"nonfactual"' in original
    private = assertions.checker_template(original)
    assert "- evidence_limitation:" not in private
    assert '"basis":"nonfactual"' not in private
    assert "- problem_input:" not in private
    assert "- general_knowledge:" not in private
    assert "PROOF-BOUND CLAIM CLASSIFICATION" in private
    assert "Use basis=textbook" in private
    assert "never semantic support or an instruction to pass" in private
    assert "Copy every selected citation and fragment exactly" in private
    assert path.read_text(encoding="utf-8") == original
    assert "SELECTED-SOURCE SCOPE LIMIT AUDIT V1" not in private


@pytest.mark.parametrize(
    "instruction",
    [
        "PER-PREDICATE SELECTION AUDIT",
        "ENTITY IDENTITY",
        "REFERENCE RESOLUTION",
        "ROLE AND STAGE",
        "SOURCE_FRAGMENTS and ACTUAL_CITATION_BINDINGS are immutable.",
        "AGGREGATE GATES",
        "REQUIREMENT ASSESSMENT V5",
        "QUANTITY REFERENT COMPARISON",
        "IMMUTABLE ASSERTION PROOF AUDIT V1",
    ],
)
def test_scientific_requirements_and_strict_guards_remain(instruction):
    prompt = assertions.checker_template(
        (ROOT / "generation/prompts/joint_check_v5.txt").read_text(encoding="utf-8")
    )
    assert instruction in prompt


def test_required_scope_composition_keeps_schema_and_no_legacy_example():
    prompt = required.checker_template(
        assertions.checker_template(
            (ROOT / "generation/prompts/joint_check_v5.txt").read_text(encoding="utf-8")
        )
    )
    assert required.SCHEMA_NAME in prompt
    assert "REQUIRED KNOWLEDGE SCOPE V1" in prompt
    assert '"claim_id":"EXAMPLE_CLAIM"' not in prompt


@pytest.mark.parametrize("basis", ["evidence_limitation", "nonfactual", "general_knowledge"])
def test_source_bound_response_cannot_change_basis_or_drop_citations(basis):
    _, provenance, _ = compiled()
    response = authored_claims(provenance)
    row = response["claims"][0]
    row["basis"] = basis
    row["citations"] = []
    if basis == "evidence_limitation":
        with pytest.raises(ValidationError):
            TypeAdapter(assertions.AuditedClaim).validate_python(row)
    else:
        assert any(
            x["code"] == "ASSERTION_CHECK_BASIS_INVALID"
            for x in assertions.assess_judgment(response, provenance)
        )


def test_legitimate_negative_audit_and_wrong_source_are_not_repaired():
    _, provenance, _ = compiled()
    response = authored_claims(provenance)
    row = response["claims"][0]
    row["status"] = "unsupported"
    row["proof_audit"]["all_predicates_entailed"] = False
    row["proof_audit"]["missing_predicates"] = ["The selected source lacks the asserted condition."]
    original = deepcopy(response)
    assert assertions.assess_judgment(response, provenance) == []
    assert response == original and row["status"] == "unsupported"
    row["citations"][0]["fragment_ids"] = ["F999"]
    assert any(
        x["code"] == "ASSERTION_CHECK_SOURCE_UNION_CHANGED"
        for x in assertions.assess_judgment(response, provenance)
    )


def test_small_external_template_keeps_backward_composition():
    result = assertions.checker_template("Check under joint_check_v5.")
    assert result.startswith("Check under joint_assertion_check_v1.")
    assert result.endswith(assertions.CHECKER_INSTRUCTIONS)
