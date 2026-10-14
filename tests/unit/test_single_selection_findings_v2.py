"""Free structural/gate controls; authored fixtures are not model quality evidence."""

from copy import deepcopy
import socket

import pytest

from generation import single_selection_findings_v2 as codec
from generation import lossless_unit_findings_v1 as old
from generation.reliability_v4 import compact_schema
from generation.source_relations_v2 import (
    ReliableUnitCheck, assess_source_relations, scoped_syntactic_units,
)
from test_full_checker_encoding_integration82 import full_judgment, packet
from test_lossless_output_integration84 import run


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("The authored codec control cannot open a socket")
    monkeypatch.setattr(socket, "socket", denied)
    monkeypatch.setattr(socket, "create_connection", denied)


@pytest.fixture
def fixture():
    outcome, adapter = run(None)
    assert outcome.succeeded, outcome.error
    messages, kwargs = adapter.calls[1]
    original = packet(messages)
    return original, adapter.records[1]["authored"], messages, kwargs


def test_complete_canonical_roundtrip_preserves_arbitrary_orders_and_parent_extras(fixture):
    original, full, _, _ = fixture
    # Explicit parent-only F002 appears before unit-selected F001. Reversed claims
    # preserve their ordered authored values rather than being silently sorted.
    full["claims"].reverse()
    full["claims"][0]["citations"][0]["fragment_ids"] = ["F002", "F001"]
    context = codec.build_context(original)
    projected = codec.encode_full(full, context)
    citation = projected["claims"][0]["citations"][0]
    assert citation == {
        "evidence_id": "ev_001", "relation": "supporting",
        "whole_parent_fragment_ids": ["F002"], "fragment_order": [1, 0],
    }
    assert "fragment_ids" not in citation
    assert codec.decode(projected, context) == full
    assert codec.canonical(codec.decode(projected, context)) == old.canonical(full)
    assert old.decode(old.encode_full(full, old.build_context(original)), old.build_context(original)) == full


def test_complete_supported_findings_still_need_and_pass_every_original_gate():
    captured = []
    def projected(messages):
        authored = full_judgment(messages)
        context = codec.build_context(packet(messages))
        decoded = codec.decode(codec.encode_full(authored, context), context)
        assert decoded == authored
        captured.append(decoded)
        return decoded
    baseline, _ = run(None)
    candidate, _ = run(None, projected)
    assert baseline.succeeded and candidate.succeeded
    assert baseline.response == candidate.response
    assert baseline.delivered_projection == candidate.delivered_projection
    for key in (
        "typed_judgment_raw_aliases", "actual_citation_bindings", "source_relation_assessment",
        "semantic_sufficiency", "checker_inconsistencies",
    ):
        assert baseline.checks[0][key] == candidate.checks[0][key]
    assert candidate.checks[0]["accepted"] is True
    assert captured


def test_multiple_unit_and_fragment_array_orders_are_exact_not_sorted(fixture):
    original, full, _, _ = fixture
    original["CLAIMS"][0]["text"] = "Photosynthesis uses light and carbon dioxide supplies carbon."
    original["SOURCE_FRAGMENTS"].append({
        "block_kind": "prose", "complete_block": True, "evidence_id": "ev_001",
        "exact_text": "Water supplies electrons.", "fragment_id": "F003",
    })
    original["ACTUAL_CITATION_BINDINGS"][0]["citations"][0]["allowed_fragment_ids"].append("F003")
    original["SOURCE_SYNTACTIC_UNITS"] = scoped_syntactic_units(
        original["CLAIMS"], original["ACTUAL_CITATION_BINDINGS"], original["SOURCE_FRAGMENTS"]
    )
    row = full["claims"][0]
    unit = deepcopy(row["units"][0])
    row["units"] = [
        {**unit, "unit_id": "U02", "fragment_ids": ["F001"]},
        {**unit, "unit_id": "U01", "fragment_ids": ["F002", "F001"]},
    ]
    row["citations"][0]["fragment_ids"] = ["F003", "F002", "F001"]
    context = codec.build_context(original)
    projected = codec.encode_full(full, context)
    citation = projected["claims"][0]["citations"][0]
    assert citation["fragment_order"] == [2, 1, 0]
    assert citation["whole_parent_fragment_ids"] == ["F003"]
    assert codec.decode(projected, context) == full


@pytest.mark.parametrize("status", ["partial", "unsupported"])
def test_negative_statuses_and_all_flags_survive_and_original_gates_reject(fixture, status):
    _, _, _, _ = fixture
    records = []
    def negative(messages):
        full = full_judgment(messages)
        full["claims"][0]["units"][0].update(
            status=status, fragment_ids=[], relation_preserved=False,
            conditions_preserved=False, reason="Missing quantified/negated condition; authored fixture.",
        )
        full["requirements"][0].update(
            sufficiency="partial", conditions_preserved=False,
            response_coverage="not_addressed", missing_information="Quantified condition absent.",
        )
        full.update(body_ok=False, complete_answer=False, coverage="none")
        return full
    def projected_negative(messages):
        authored = negative(messages)
        context = codec.build_context(packet(messages))
        decoded = codec.decode(codec.encode_full(authored, context), context)
        assert decoded == authored
        records.append(decoded)
        return decoded
    baseline, _ = run(None, negative)
    candidate, _ = run(None, projected_negative)
    assert baseline.error["code"] == candidate.error["code"] == "SEMANTIC_CHECK_FAILED"
    assert baseline.response is candidate.response is None
    assert baseline.checks[0]["source_relation_assessment"] == candidate.checks[0]["source_relation_assessment"]
    assert baseline.checks[0]["semantic_sufficiency"] == candidate.checks[0]["semantic_sufficiency"]
    assert records[0]["claims"][0]["units"][0]["conditions_preserved"] is False
    assert records[0]["claims"][0]["units"][0]["relation_preserved"] is False


@pytest.mark.parametrize("fault", [
    "missing_unit", "foreign_unit", "unknown_fragment", "unknown_field",
    "missing_flag", "parent_order_omission", "parent_order_duplicate", "boolean_order",
    "whole_parent_duplicate", "unknown_extra", "stale_context", "foreign_quote",
])
def test_malformed_wire_never_fills_or_drops_model_values(fixture, fault):
    original, full, _, _ = fixture
    context = codec.build_context(original)
    projected = codec.encode_full(full, context)
    unit = projected["claims"][0]["units"][0]
    citation = projected["claims"][0]["citations"][0]
    if fault == "missing_unit":
        projected["claims"][0]["units"] = []
    elif fault == "foreign_unit":
        unit["unit_id"] = "U999"
    elif fault == "unknown_fragment":
        unit["fragment_ids"] = ["F999"]
    elif fault == "unknown_field":
        unit["relpath"] = "forged"
    elif fault == "missing_flag":
        unit.pop("conditions_preserved")
    elif fault == "parent_order_omission":
        citation["fragment_order"] = []
    elif fault == "parent_order_duplicate":
        citation["fragment_order"] = [0, 0]
    elif fault == "boolean_order":
        citation["fragment_order"] = [False]
    elif fault == "whole_parent_duplicate":
        citation["whole_parent_fragment_ids"] = ["F001"]
    elif fault == "unknown_extra":
        citation.update(whole_parent_fragment_ids=["F999"], fragment_order=[0, 1])
    elif fault == "stale_context":
        projected["context_sha256"] = "0" * 64
    else:
        projected["requirements"][0]["evidence"][0]["quote_id"] = "F002"
    with pytest.raises(ValueError):
        codec.decode(projected, context)


@pytest.mark.parametrize("fault", ["foreign_same_evidence", "incomplete_fragment"])
def test_actual_current_own_scope_and_complete_blocks_are_required(fixture, fault):
    original, full, _, _ = fixture
    clean = codec.encode_full(full, codec.build_context(original))
    if fault == "foreign_same_evidence":
        original["ACTUAL_CITATION_BINDINGS"][0]["citations"][0]["allowed_fragment_ids"] = ["F002"]
    else:
        original["SOURCE_FRAGMENTS"][0]["complete_block"] = False
    original["SOURCE_SYNTACTIC_UNITS"] = scoped_syntactic_units(
        original["CLAIMS"], original["ACTUAL_CITATION_BINDINGS"], original["SOURCE_FRAGMENTS"]
    )
    context = codec.build_context(original)
    if fault == "foreign_same_evidence":
        clean["context_sha256"] = context.digest
        with pytest.raises(ValueError, match="Foreign parent citation fragment"):
            codec.decode(clean, context)
    else:
        with pytest.raises(ValueError, match="Unit selects an incomplete source fragment"):
            codec.encode_full(full, context)




def test_prepare_has_only_new_structural_instructions_and_canonical_gates(fixture):
    _, _, messages, kwargs = fixture
    prepared = codec.prepare(messages, kwargs["response_schema"])
    assert prepared.messages[-1] == messages[-1]
    assert "Return the lossless_unit_findings_v1 schema" not in prepared.messages[0]["content"]
    assert "Return the single_selection_findings_v2 schema" in prepared.messages[0]["content"]
    assert "attempt_evaluation_ok" in prepared.schema["required"]
    assert prepared.context.descriptor()["source_entailment_certified"] is False
    assert prepared.context.descriptor()["original_full_validators_required"] is True


