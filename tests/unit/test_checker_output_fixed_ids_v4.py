"""Fixed original-text references; no model, service, database or network."""

import hashlib
import importlib.util
import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from generation.reliability_v4 import compact_schema
from generation.source_relations_v2 import ReliableUnitCheck, scoped_syntactic_units

HELPER = Path(__file__).with_name("test_checker_output_projection_v1.py")
SPEC = importlib.util.spec_from_file_location("fixed_id_public_fixture84", HELPER)
assert SPEC is not None and SPEC.loader is not None
fixture_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = fixture_module
SPEC.loader.exec_module(fixture_module)
codec = fixture_module.codec


def prepared_fixture():
    packet, full = fixture_module.fixture()
    context = codec.build_context(packet)
    return packet, full, context, codec.encode_full(full, context)


def long_fixture():
    packet, full = fixture_module.fixture()
    text = "Unless the safety guard is open, the device does not emit sparks. "
    text += " ".join(
        f"Background sentence {i} retains the original source wording." for i in range(35)
    )
    text += " Only under the stated count basis can the final operation release two sparks."
    packet["SOURCE_FRAGMENTS"][0]["exact_text"] = text
    packet["SOURCE_SYNTACTIC_UNITS"] = scoped_syntactic_units(
        packet["CLAIMS"], packet["ACTUAL_CITATION_BINDINGS"], packet["SOURCE_FRAGMENTS"]
    )
    context = codec.build_context(packet)
    catalogue, _ = codec._quote_catalogue(packet)
    rows = [(qid, row) for qid, row in catalogue.items() if row["fragment_id"] == "F001"]
    qid, row = rows[0]
    full["requirements"][0]["evidence"][0]["quote"] = text[row["start"] : row["end"]]
    return packet, full, context, rows


def test_whole_original_id_exactly_restores_unicode_all_variants_and_negative_fields():
    packet, full, context, wire = prepared_fixture()
    assert wire["rs"][0]["ev"][0] == {"e": "ev1", "f": "F001", "p": "F001"}
    restored = codec.decode(wire, context)
    assert restored == full
    assert (
        restored["requirements"][0]["evidence"][0]["quote"]
        == packet["SOURCE_FRAGMENTS"][0]["exact_text"]
    )
    assert restored["claims"][0]["units"][0]["status"] == "unsupported"
    assert restored["claims"][0]["units"][0]["conditions_preserved"] is False
    assert restored["claims"][1]["problem_quote"] == full["claims"][1]["problem_quote"]
    assert restored["claims"][2]["derivation"] == full["claims"][2]["derivation"]


def test_long_blocks_are_finite_overlapping_exact_sentence_ranges_visible_without_text_copy():
    packet, full, context, rows = long_fixture()
    text = packet["SOURCE_FRAGMENTS"][0]["exact_text"]
    assert len(rows) > 1
    assert rows[1][1]["start"] < rows[0][1]["end"]
    assert all(0 < row["end"] - row["start"] <= 1200 for _, row in rows)
    wire = codec.encode_full(full, context)
    assert wire["rs"][0]["ev"][0]["p"] == rows[0][0]
    assert codec.decode(wire, context) == full
    instructions = codec.reference_instructions(context)
    assert "first_sentence" in instructions and "last_sentence" in instructions
    assert all(qid in instructions for qid, _ in rows)
    assert text not in instructions
    schema = codec.wire_schema(context)
    assert schema["$defs"]["RequirementEvidence"]["properties"]["p"]["type"] == "string"
    assert set(schema["$defs"]["RequirementEvidence"]["properties"]["p"]["enum"]) >= {
        qid for qid, _ in rows
    }


def test_unknown_fixed_id_rejects_without_nearby_or_whole_fragment_fallback():
    _, _, context, wire = prepared_fixture()
    wire["rs"][0]["ev"][0]["p"] = "F001-unknown"
    with pytest.raises(ValueError, match="fixed quote ID"):
        codec.decode(wire, context)


def test_legacy_coordinates_or_boolean_are_not_fixed_ids():
    _, _, context, wire = prepared_fixture()
    for value in ([0, 4], True, 0):
        wire["rs"][0]["ev"][0]["p"] = value
        with pytest.raises(ValueError, match="fixed quote ID"):
            codec.decode(wire, context)


def test_foreign_fragment_fixed_id_rejects_even_when_original_text_is_available():
    _, _, context, wire = prepared_fixture()
    wire["rs"][0]["ev"][0]["p"] = "F002"
    with pytest.raises(ValueError, match="another fragment"):
        codec.decode(wire, context)


def test_foreign_evidence_owner_rejects():
    _, _, context, wire = prepared_fixture()
    wire["rs"][0]["ev"][0]["e"] = "ev2"
    with pytest.raises(ValueError, match="Foreign"):
        codec.decode(wire, context)


def test_missing_fixed_id_never_defaults_to_whole_fragment():
    _, _, context, wire = prepared_fixture()
    wire["rs"][0]["ev"][0].pop("p")
    with pytest.raises(ValueError, match="Missing"):
        codec.decode(wire, context)


def test_duplicate_selected_reference_rejects_without_deduplicating_model_output():
    _, _, context, wire = prepared_fixture()
    wire["rs"][0]["ev"].append(deepcopy(wire["rs"][0]["ev"][0]))
    with pytest.raises(ValueError, match="Duplicate"):
        codec.decode(wire, context)


def test_incomplete_original_is_not_promoted_by_fixed_id():
    packet, _, _, wire = prepared_fixture()
    packet["SOURCE_FRAGMENTS"][0]["complete_block"] = False
    packet["SOURCE_SYNTACTIC_UNITS"] = scoped_syntactic_units(
        packet["CLAIMS"], packet["ACTUAL_CITATION_BINDINGS"], packet["SOURCE_FRAGMENTS"]
    )
    context = codec.build_context(packet)
    wire["h"] = context.digest
    with pytest.raises(ValueError, match="fixed quote ID"):
        codec.decode(wire, context)


def test_old_coordinate_context_digest_is_stale_even_with_a_new_fixed_id_field():
    packet, _, context, wire = prepared_fixture()
    old_bound = codec.canonical(
        {"packet": packet, "canonical_schema_sha256": context.canonical_schema_sha256}
    )
    wire["h"] = hashlib.sha256(old_bound.encode("utf-8")).hexdigest()
    assert wire["h"] != context.digest
    assert context.descriptor()["wire_codec_fingerprint"] == context.wire_codec_fingerprint
    with pytest.raises(ValueError, match="stale"):
        codec.decode(wire, context)


def test_uncatalogued_narrow_quote_is_rejected_without_widening_or_verdict_changes():
    packet, full, context, _ = prepared_fixture()
    full["requirements"][0]["evidence"][0]["quote"] = "does not emit two sparks"
    before = deepcopy(full)
    with pytest.raises(ValueError, match="no widening"):
        codec.encode_full(full, context)
    assert full == before
    assert packet == context.packet


def test_over_cap_single_sentence_has_no_id_and_is_not_cut_or_summarized():
    packet, full = fixture_module.fixture()
    text = "Unless " + "longword " * 150 + "the device must not emit sparks."
    packet["SOURCE_FRAGMENTS"][0]["exact_text"] = text
    packet["SOURCE_SYNTACTIC_UNITS"] = scoped_syntactic_units(
        packet["CLAIMS"], packet["ACTUAL_CITATION_BINDINGS"], packet["SOURCE_FRAGMENTS"]
    )
    context = codec.build_context(packet)
    catalogue, unavailable = codec._quote_catalogue(packet)
    assert not any(row["fragment_id"] == "F001" for row in catalogue.values())
    assert unavailable == [["F001", 1, 0, len(text)]]
    assert context.packet["SOURCE_FRAGMENTS"][0]["exact_text"] == text
    full["requirements"][0]["evidence"][0]["quote"] = text[:1200]
    with pytest.raises(ValueError, match="no widening"):
        codec.encode_full(full, context)


def test_partial_long_block_does_not_certify_omitted_condition_negation_or_sufficiency():
    packet, full, context, rows = long_fixture()
    text = packet["SOURCE_FRAGMENTS"][0]["exact_text"]
    qid, row = rows[1]
    quote = text[row["start"] : row["end"]]
    assert "does not emit sparks" not in quote
    full["requirements"][0]["evidence"][0]["quote"] = quote
    full["requirements"][0]["sufficiency"] = "partial"
    full["requirements"][0]["conditions_preserved"] = False
    full["requirements"][0]["reason"] = (
        "The selected passage omits the necessary condition and negation."
    )
    wire = codec.encode_full(full, context)
    assert wire["rs"][0]["ev"][0]["p"] == qid
    restored = codec.decode(wire, context)
    assert restored == full
    assert restored["requirements"][0]["sufficiency"] == "partial"
    assert restored["requirements"][0]["conditions_preserved"] is False
    assert restored["body_ok"] is False
    assert context.descriptor()["source_entailment_certified"] is False


def test_complementary_original_ids_remain_separate_quotes_and_keep_original_caps():
    packet, full, context, wire = prepared_fixture()
    assert wire["rs"][0]["ev"] == [
        {"e": "ev1", "f": "F001", "p": "F001"},
        {"e": "ev1", "f": "F002", "p": "F002"},
    ]
    restored = codec.decode(wire, context)
    assert [row["quote"] for row in restored["requirements"][0]["evidence"]] == [
        packet["SOURCE_FRAGMENTS"][0]["exact_text"],
        packet["SOURCE_FRAGMENTS"][1]["exact_text"],
    ]
    original = compact_schema(ReliableUnitCheck)
    shape = codec.wire_schema(context)
    assert (
        shape["$defs"]["RequirementCheck"]["properties"]["ev"]["maxItems"]
        == original["$defs"]["RequirementCheck"]["properties"]["evidence"]["maxItems"]
        == 8
    )
    assert shape["$defs"]["TextbookUnitClaim"]["properties"]["r"]["maxLength"] == 800
    assert shape["$defs"]["UnitAssessment"]["properties"]["r"]["maxLength"] == 200
    assert original["$defs"]["RequirementEvidence"]["properties"]["quote"]["maxLength"] == 1200
