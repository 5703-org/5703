"""Offline generic coverage trace controls; not model quality results."""

from copy import deepcopy
import socket
import pytest
from generation.requirement_completeness_candidate_v1 import POLICY, freeze, apply, audit_witnesses


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*a, **k):
        raise AssertionError("No provider calls")

    monkeypatch.setattr(socket.socket, "connect", deny)


@pytest.mark.parametrize(
    "question",
    [
        "Report millilitres delivered per valve opening and operating pressure.",
        "For each rotation, give clockwise and counterclockwise displacement and energy used.",
        "Explain how yield changes without heat, except when the catalyst is absent.",
        'Quote the statement "per sample" and explain the sampling assumption.',
        "Give mass flux in grams per square metre per second, not total mass.",
        "Compare cost per passenger-kilometre at equal load and distance.",
    ],
)
def test_preserve_generic_conditions_and_denominators_verbatim(question):
    m = freeze(question)
    original = [
        {"role": "system", "content": "Original strict schema and citation rules."},
        {"role": "user", "content": question},
    ]
    baseline, receipt = apply(original, m)
    assert baseline == original and receipt["applied"] is False
    changed, receipt = apply(original, m, policy=POLICY)
    assert receipt["applied"] and receipt["semantic_completeness"] is None
    assert changed[0] == original[0] and changed[-1] == original[-1]
    assert m["requirements"][0]["verbatim_request"] == question
    assert original == baseline


def fixture():
    q = "Describe displacement. Include energy consumed per rotation."
    return freeze(
        q,
        [
            {"id": "requirement_01", "start": 0, "end": 22},
            {"id": "requirement_02", "start": 23, "end": len(q)},
        ],
    )


def witness(rid, text, status="covered"):
    return {"id": rid, "status": status, "start": 0, "end": len(text), "quote": text}


def test_missing_energy_axis_cannot_be_accounted_by_another_axis():
    m = fixture()
    text = "The component travels forward."
    result = audit_witnesses(m, text, [witness("requirement_01", text)])
    assert result["missing_requirement_ids"] == ["requirement_02"]
    assert not result["structurally_accounted"] and result["semantic_completeness"] is None


def test_exact_but_irrelevant_witness_never_certifies_semantics():
    # An optimistic model can repeat a movement quote for the energy request.
    # Structural coverage must therefore never be advertised as semantic PASS.
    text = "The component travels forward."
    result = audit_witnesses(
        fixture(), text, [witness("requirement_01", text), witness("requirement_02", text)]
    )
    assert result["all_claimed_covered"] and result["semantic_completeness"] is None
    assert not result["publication_override"] and not result["citation_gate_override"]


def test_explicit_source_limitation_is_not_correct_complete_answer():
    text = "The source does not give energy consumed per rotation."
    result = audit_witnesses(
        fixture(),
        text,
        [witness("requirement_01", text), witness("requirement_02", text, "limited")],
    )
    assert result["structurally_accounted"] and not result["all_claimed_covered"]
    assert result["explicit_limitation_ids"] == ["requirement_02"]


@pytest.mark.parametrize(
    "mutation", ["duplicate", "foreign", "invented", "range", "missing_with_span"]
)
def test_trace_contract_failures_preserved(mutation):
    text = "A synthetic exact statement."
    row = witness("requirement_01", text)
    rows = [row]
    if mutation == "duplicate":
        rows.append(deepcopy(row))
    if mutation == "foreign":
        row["id"] = "requirement_99"
    if mutation == "invented":
        row["quote"] = "An invented value."
    if mutation == "range":
        row["end"] += 1
    if mutation == "missing_with_span":
        row["status"] = "missing"
    with pytest.raises(ValueError):
        audit_witnesses(fixture(), text, rows)


@pytest.mark.parametrize("mutation", ["question", "manifest", "policy"])
def test_opt_in_and_manifest_guards(mutation):
    q = "Give energy per action."
    m = freeze(q)
    messages = [{"role": "user", "content": q}]
    policy = POLICY
    if mutation == "question":
        messages[0]["content"] = "A different request."
    if mutation == "manifest":
        m["requirements"][0]["verbatim_request"] = "Injected answer"
    if mutation == "policy":
        policy = "unknown"
    with pytest.raises(ValueError):
        apply(messages, m, policy=policy)


def test_old_matching_history_is_not_current_request():
    q = "Give energy per action."
    messages = [
        {"role": "user", "content": q},
        {"role": "assistant", "content": "Earlier answer."},
        {"role": "user", "content": "Now explain the material."},
    ]
    with pytest.raises(ValueError):
        apply(messages, freeze(q), policy=POLICY)


def test_tampered_manifest_does_not_enter_trace_audit():
    m = fixture()
    m["requirements"][0]["verbatim_request"] = "Changed request."
    with pytest.raises(ValueError):
        audit_witnesses(m, "A response.", [])
