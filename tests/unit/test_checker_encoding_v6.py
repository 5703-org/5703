"""Lossless transport proofs and token measurements, never semantic quality scores."""

from copy import deepcopy
import json

import pytest

from generation import checker_encoding as legacy
from generation.checker_encoding_v6 import VERSION, decode, encode, select_encoding
from generation.reliability_v6 import CompactJointCheckV6, compact_check_context
from generation.token_counting import TokenCounter
from generation.types import ModelConfig


def context():
    statement = (
        "At −2.5 °C and P ≥ 10 kPa, X does not increase; unless condition A holds, "
        "ΔG = −3.0 J mol−1 and n = 2 mol remain unchanged [ev_001]."
    )
    claims = [
        {"claim_id": "c1", "text": statement, "answer_field": "answer_text"},
        {"claim_id": "c2", "text": statement, "answer_field": "short_answer"},
    ]
    return compact_check_context(
        {
            "question": "Under condition A, compare X and ΔG. Preserve the pressure units.",
            "current_problem": "Under condition A, compare X and ΔG. Preserve the pressure units.",
            "CLAIMS": claims,
            "SOURCE_FRAGMENTS": [
                {
                    "fragment_id": f"F{number:03d}",
                    "evidence_id": "ev_001",
                    "exact_text": (statement + " ") * 14,
                    "complete_block": True,
                    "block_kind": "paragraph",
                }
                for number in range(1, 12)
            ],
            "ACTUAL_CITATION_BINDINGS": [
                {
                    "claim_id": row["claim_id"],
                    "citations": [
                        {
                            "evidence_id": "ev_001",
                            "allowed_fragment_ids": [f"F{number:03d}" for number in range(1, 12)],
                        }
                    ],
                }
                for row in claims
            ],
            "CONTEXT_COVERAGE": {"requirements": [{"id": "r1", "conditions": ["condition A"]}]},
            "PROPOSED_DELIVERY": {"answer_text": statement, "short_answer": statement},
            "PRIOR_EXPOSURE": {"disabled": True},
            "POLICY": {"teaching_mode": "direct", "control_evidence": True},
        }
    )


def test_exact_round_trip_retains_complete_signed_conditions_quotes_and_summary():
    data = context()
    before = deepcopy(data)
    encoded = encode(data)
    restored = decode(encoded)
    assert restored == before and data == before
    assert restored["CLAIMS"][0]["text"] == restored["CLAIMS"][1]["text"]
    assert restored["PROPOSED_DELIVERY"] == before["PROPOSED_DELIVERY"]
    assert restored["CONTEXT_COVERAGE"] == before["CONTEXT_COVERAGE"]
    assert restored["REQUEST_TARGET"] == before["REQUEST_TARGET"]
    assert all("−2.5 °C" in f["exact_text"] for f in restored["SOURCE_FRAGMENTS"])
    assert all("unless condition A" in f["exact_text"] for f in restored["SOURCE_FRAGMENTS"])
    assert all("text" not in unit for unit in encoded["COMPACT_CLAIM_UNITS"]["rows"])
    assert "text_hash" not in legacy.dumps(encoded["QUOTE_REFERENCES"])
    assert encoded["SOURCE_FRAGMENTS"] == legacy.encode(data)["SOURCE_FRAGMENTS"]
    assert encoded["CLAIMS"] == legacy.encode(data)["CLAIMS"]


@pytest.mark.parametrize("table", ["COMPACT_CLAIM_UNITS", "QUOTE_REFERENCES"])
@pytest.mark.parametrize(
    "change", ["missing", "duplicate", "foreign_id", "span", "boolean_offset", "column", "order"]
)
def test_reference_mutations_fail_closed(table, change):
    value = encode(context())
    rows = value[table]["rows"]
    if change == "missing":
        rows.pop()
    elif change == "duplicate":
        rows.append(deepcopy(rows[0]))
    elif change == "foreign_id":
        rows[0][0] = "foreign"
    elif change == "span":
        rows[0][-1] -= 1
    elif change == "boolean_offset":
        rows[0][-2] = False
    elif change == "column":
        value[table]["columns"][0] = "unknown"
    else:
        rows.reverse()
    with pytest.raises(ValueError, match="COMPACT_ENCODING_REFERENCE_TABLE_MISMATCH"):
        decode(value)


@pytest.mark.parametrize(
    "change",
    ["unit_text", "unit_hash", "quote_hash", "missing_quote", "other_policy", "already_encoded"],
)
def test_invalid_original_catalogue_is_not_silently_normalized(change):
    data = context()
    if change == "unit_text":
        data["COMPACT_CLAIM_UNITS"][0]["units"][0]["text"] = "A shortened summary."
    elif change == "unit_hash":
        data["COMPACT_CLAIM_UNITS"][0]["units"][0]["text_hash"] = "0" * 64
    elif change == "quote_hash":
        data["QUOTE_REFERENCES"][0]["text_hash"] = "0" * 64
    elif change == "missing_quote":
        data["QUOTE_REFERENCES"].pop()
    elif change == "other_policy":
        data["COMPACT_CONTRACT"] = "typed_joint_v5"
    else:
        data["CHECKER_INPUT_ENCODING"] = {"version": legacy.VERSION}
    with pytest.raises(ValueError):
        encode(data)


@pytest.mark.parametrize("change", ["source", "claim", "question", "version"])
def test_changed_originals_cannot_reuse_old_reference_tables(change):
    value = encode(context())
    if change in {"source", "claim"}:
        table = value["SOURCE_FRAGMENTS" if change == "source" else "CLAIMS"]
        column = table["columns"].index("exact_text" if change == "source" else "text")
        table["rows"][0][column] = "Changed condition and negation."
    elif change == "question":
        value["question"] = "Changed question."
    else:
        value["CHECKER_INPUT_ENCODING"]["version"] = "foreign"
    with pytest.raises(ValueError):
        decode(value)


@pytest.mark.parametrize("table", ["COMPACT_CLAIM_UNITS", "QUOTE_REFERENCES"])
@pytest.mark.parametrize("offset", [False, 0.0])
def test_original_boolean_or_float_offsets_do_not_pass_integer_equality(table, offset):
    data = context()
    row = data[table][0]["units"][0] if table == "COMPACT_CLAIM_UNITS" else data[table][0]
    assert row["start"] == 0
    row["start"] = offset
    with pytest.raises(ValueError, match="COMPACT_ENCODING_ORIGINAL_CATALOGUE_MISMATCH"):
        encode(data)


def test_complete_fragments_and_partial_target_metadata_remain_unchanged():
    data = context()
    data["SOURCE_FRAGMENTS"][0]["complete_block"] = False
    data["REQUEST_TARGET"].update(source_coverage="partial", proven_fragments=[])
    assert decode(encode(data)) == data
    assert decode(encode(data))["SOURCE_FRAGMENTS"][0]["complete_block"] is False
    assert decode(encode(data))["REQUEST_TARGET"]["source_coverage"] == "partial"


def test_encoding_does_not_change_model_output_schema_or_legacy_encoder():
    data = context()
    schema = CompactJointCheckV6.model_json_schema()
    schema_before = deepcopy(schema)
    legacy_before = legacy.encode(data)
    assert decode(encode(data)) == data
    assert schema == schema_before and legacy.encode(data) == legacy_before
    with pytest.raises(ValueError, match="UNKNOWN_COMPACT_CHECKER_INPUT_ENCODING"):
        decode(legacy_before)


def test_real_offline_tokenizer_measures_input_savings_without_quality_claim():
    data = context()
    counter = TokenCounter(
        ModelConfig(
            tokenizer_provider="tiktoken",
            tokenizer_name="cl100k_base",
            token_count_fallback="error",
        )
    )
    messages = [
        {"role": "system", "content": "Check all gates."},
        {"role": "user", "content": json.dumps(data)},
    ]
    schema = CompactJointCheckV6.model_json_schema()
    previous, previous_report = legacy.select_encoding(
        data, messages, counter, schema, "joint_check_v6"
    )
    selected, receipt = select_encoding(data, messages, counter, schema, "joint_check_v6")
    assert receipt["encoding"] == VERSION
    assert receipt["encoded_input_tokens"] < previous_report["encoded_input_tokens"]
    assert decode(json.loads(selected[-1]["content"])) == data
    assert receipt["original_data_sha256"] == receipt["decoded_data_sha256"]
    assert receipt["local_semantic_support_certified"] is False
    assert messages[-1]["content"] != selected[-1]["content"]
    assert previous[-1]["content"] != selected[-1]["content"]
