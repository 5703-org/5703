"""Lossless generator source transport; no semantic labels or external calls."""

from copy import deepcopy
import hashlib
import json

import pytest

from generation import assertion_provenance_v1 as assertions
from generation.reliability_v5 import response_claims


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sources():
    texts = [
        "When valve V is open, pressure in chamber P moves its piston upward.",
        "The same piston lifts a load against gravity; it does not create energy.",
    ]
    fragments = []
    offset = 0
    for index, text in enumerate(texts):
        fragments.append(
            {
                "fragment_id": f"original-{index}",
                "evidence_id": "ev_001",
                "exact_text": text,
                "text_hash": hashlib.sha256(text.encode()).hexdigest(),
                "complete_block": True,
                "asset_id": "authored-asset",
                "chunk_id": "authored-chunk",
                "source_unit_id": "authored-unit",
                "start": offset,
                "end": offset + len(text),
                "chunk_start": offset,
                "chunk_end": offset + len(text),
                "page": 7,
                "offset_basis": "cleaned_source_unit_unicode",
            }
        )
        offset += len(text) + 1
    text = "\n".join(texts)
    evidence = [
        {
            "evidence_id": "ev_001",
            "text": text,
            "text_hash": hashlib.sha256(text.encode()).hexdigest(),
        }
    ]
    return fragments, evidence


def bank():
    fragments, evidence = sources()
    return assertions.source_bank(fragments, evidence)


def packet():
    return assertions.encode_generation_source_bank(bank())


def cell(table, field, row=0):
    return table["rows"][row], table["columns"].index(field)


def test_generation_context_round_trip_retains_every_source_and_untouched_evidence():
    fragments, evidence = sources()
    original = {
        "CURRENT_EVIDENCE": evidence,
        "ASSERTION_SOURCE_BANK": bank(),
        "learner_turn": {"current_step": None},
        "current_problem": "Explain the mechanism.",
    }
    before = deepcopy(original)
    encoded = {
        **deepcopy(original),
        **assertions.encode_generation_source_bank(original["ASSERTION_SOURCE_BANK"]),
    }
    restored = deepcopy(encoded)
    decoded = assertions.decode_generation_source_bank(
        {
            key: restored.pop(key)
            for key in (
                "ASSERTION_SOURCE_BANK",
                "ASSERTION_SOURCE_LOCATORS",
                "GENERATION_INPUT_ENCODING",
            )
        },
        expected_bank=original["ASSERTION_SOURCE_BANK"],
    )
    restored["ASSERTION_SOURCE_BANK"] = decoded
    assert canonical(restored) == canonical(original)
    assert original == before and encoded["CURRENT_EVIDENCE"] == evidence
    assert decoded == assertions.source_bank(fragments, evidence)
    decoded[0]["source_locator"]["page"] = 99
    assert original == before


@pytest.mark.parametrize("shape", ["empty", "heterogeneous"])
def test_empty_and_absent_versus_null_locator_fields_remain_distinct(shape):
    rows = bank() if shape == "heterogeneous" else []
    if rows:
        rows[0]["source_locator"]["page"] = None
        del rows[1]["source_locator"]["page"]
    encoded = assertions.encode_generation_source_bank(rows)
    assert canonical(assertions.decode_generation_source_bank(encoded)) == canonical(rows)


def test_encoding_preserves_the_actual_compiler_claim_bindings_and_checker_packet():
    fragments, evidence = sources()
    draft = {
        "schema_version": "chat_response_v1",
        "response_type": "answer",
        "answer_text": [
            {
                "assertion_id": "A001",
                "text": "When valve V is open, pressure moves the piston and lifts its load against gravity.",
                "source_ids": ["F001", "F002"],
            }
        ],
        "short_answer": None,
        "citations": ["ev_001"],
        "refusal_reason": None,
        "follow_up_questions": [],
        "confidence": None,
        "tutor_question": None,
        "learner_attempt_evaluation": None,
    }
    public, provenance = assertions.compile_draft(draft, fragments)
    rows = assertions.decode_generation_source_bank(packet(), expected_bank=bank())
    restored = [
        {
            **row["source_locator"],
            "fragment_id": row["fragment_id"],
            "evidence_id": row["evidence_id"],
            "exact_text": row["exact_text"],
            "text_hash": row["text_sha256"],
            "complete_block": row["complete_block"],
        }
        for row in rows
    ]
    public_after, provenance_after = assertions.compile_draft(draft, restored)
    assert canonical((public_after, provenance_after)) == canonical((public, provenance))
    assert assertions.checker_bindings(
        response_claims(public), provenance, fragments
    ) == assertions.checker_bindings(response_claims(public_after), provenance_after, restored)
    assert assertions.checker_packet(provenance_after) == assertions.checker_packet(provenance)
    assert assertions.source_bank(restored, evidence) == bank()


@pytest.mark.parametrize(
    "defect",
    [
        "missing_locators",
        "duplicate_bank_column",
        "duplicate_locator_column",
        "short_row",
        "unknown_column",
        "extra_locator",
    ],
)
def test_missing_extra_or_ambiguous_table_structure_fails_closed(defect):
    value = packet()
    if defect == "missing_locators":
        del value["ASSERTION_SOURCE_LOCATORS"]
    elif defect == "duplicate_bank_column":
        value["ASSERTION_SOURCE_BANK"]["columns"].append("source_id")
    elif defect == "duplicate_locator_column":
        value["ASSERTION_SOURCE_LOCATORS"]["columns"].append("page")
    elif defect == "short_row":
        value["ASSERTION_SOURCE_BANK"]["rows"][0].pop()
    elif defect == "unknown_column":
        value["ASSERTION_SOURCE_BANK"]["columns"][0] = "unknown"
    else:
        value["ASSERTION_SOURCE_LOCATORS"]["rows"].append(
            deepcopy(value["ASSERTION_SOURCE_LOCATORS"]["rows"][0])
        )
    with pytest.raises(ValueError):
        assertions.decode_generation_source_bank(value)


@pytest.mark.parametrize("reference", [-1, 2, True, 0.0, "0", None, 1])
def test_missing_duplicate_wrong_type_and_foreign_locator_references_are_rejected(reference):
    value = packet()
    row, index = cell(value["ASSERTION_SOURCE_BANK"], "source_locator")
    row[index] = reference
    with pytest.raises(ValueError, match="LOCATOR_REFERENCE"):
        assertions.decode_generation_source_bank(value)


@pytest.mark.parametrize(
    "field,replacement",
    [
        ("source_id", "F099"),
        ("fragment_id", "changed"),
        ("evidence_id", "ev_999"),
        ("exact_text", "Different unsupported premise."),
        ("text_sha256", "0" * 64),
        ("complete_block", 1),
    ],
)
def test_changed_source_identity_text_hash_or_type_is_not_normalized(field, replacement):
    value = packet()
    row, index = cell(value["ASSERTION_SOURCE_BANK"], field)
    row[index] = replacement
    with pytest.raises(ValueError):
        assertions.decode_generation_source_bank(value, expected_bank=bank())


def test_changed_locator_fails_checksum_and_a_new_valid_packet_cannot_change_expected_bank():
    value = packet()
    row, index = cell(value["ASSERTION_SOURCE_LOCATORS"], "page")
    row[index] = 8
    with pytest.raises(ValueError, match="BANK_CHANGED"):
        assertions.decode_generation_source_bank(value)
    changed = bank()
    changed[0]["source_locator"]["page"] = 8
    with pytest.raises(ValueError, match="BANK_CHANGED"):
        assertions.decode_generation_source_bank(
            assertions.encode_generation_source_bank(changed), expected_bank=bank()
        )
