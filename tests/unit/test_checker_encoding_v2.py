"""Complete-input round trips and corrupted reference negative controls."""

import json
from copy import deepcopy

import pytest
from generation import checker_encoding as legacy
from generation.checker_encoding_v2 import VERSION, decode, encode, select_encoding
from generation.source_relations_v2 import scoped_syntactic_units
from generation.token_counting import estimate_tokens


def context():
    text = "At −2.5 °C, X does not rise; unless P ≤ 10 kPa, n = 2 mol stays fixed [ev_001]."
    claims = [
        {"claim_id": "c1", "text": text, "evidence_ids": ["ev_001"]},
        {"claim_id": "c2", "text": "Consider this next step.", "evidence_ids": []},
    ]
    fragments = [
        {
            "fragment_id": f"F{number:03d}",
            "evidence_id": "ev_001",
            "exact_text": text + "\n" + 'Escaped quote "and"; e\u0301 is not é.',
            "complete_block": True,
            "block_kind": "paragraph",
        }
        for number in range(1, 4)
    ]
    bindings = [
        {
            "claim_id": "c1",
            "citations": [{"evidence_id": "ev_001", "allowed_fragment_ids": ["F001", "F002"]}],
        },
        {"claim_id": "c2", "citations": []},
    ]
    return {
        "CLAIMS": claims,
        "SOURCE_FRAGMENTS": fragments,
        "ACTUAL_CITATION_BINDINGS": bindings,
        "SOURCE_SYNTACTIC_UNITS": scoped_syntactic_units(claims, bindings, fragments),
        "SOURCE_RELATION_POLICY": "source_relation_contract_v2",
        "question": "Compare the conditional response.",
        "PROPOSED_DELIVERY": {"answer_text": text},
        "PRIOR_EXPOSURE": {"disabled": True},
        "POLICY": {"teaching_mode": "direct", "control_evidence": True},
        "CONTEXT_COVERAGE": {"requirements": [{"id": "r1", "conditions": ["P ≤ 10 kPa"]}]},
    }


def test_exact_canonical_round_trip_retains_every_text_gate_and_occurrence():
    data = context()
    before = deepcopy(data)
    encoded = encode(data)
    assert legacy.dumps(decode(json.loads(legacy.dumps(encoded)))) == legacy.dumps(before)
    assert data == before
    assert encoded["SOURCE_FRAGMENTS"] == legacy.encode(data)["SOURCE_FRAGMENTS"]
    assert encoded["CLAIMS"] == legacy.encode(data)["CLAIMS"]
    assert encoded["POLICY"] == data["POLICY"]
    assert encoded["CONTEXT_COVERAGE"] == data["CONTEXT_COVERAGE"]
    for original, reference in zip(
        data["SOURCE_SYNTACTIC_UNITS"], encoded["SOURCE_SYNTACTIC_UNITS"], strict=True
    ):
        assert reference["source_context_candidates"] == original["source_context_candidates"]
        assert "full_claim" not in reference and "actual_citation_scope" not in reference
        assert all(set(unit) == {"unit_id", "start", "end"} for unit in reference["units"])
    assert decode(encoded)["SOURCE_SYNTACTIC_UNITS"][1]["actual_citation_scope"] == []


@pytest.mark.parametrize(
    "field",
    [
        "CLAIMS",
        "SOURCE_FRAGMENTS",
        "ACTUAL_CITATION_BINDINGS",
        "SOURCE_SYNTACTIC_UNITS",
    ],
)
@pytest.mark.parametrize("change", ["duplicate", "missing", "foreign_id", "empty_id"])
def test_bad_original_identity_catalogues_fail_closed(field, change):
    data = context()
    rows = data[field]
    id_field = "fragment_id" if field == "SOURCE_FRAGMENTS" else "claim_id"
    if change == "duplicate":
        rows.append(deepcopy(rows[0]))
    elif change == "missing":
        rows.pop(0)
    else:
        rows[0][id_field] = "unknown" if change == "foreign_id" else ""
    with pytest.raises(ValueError):
        encode(data)


@pytest.mark.parametrize(
    "change",
    [
        "text",
        "hash",
        "span",
        "boolean_offset",
        "float_offset",
        "duplicate_unit",
        "missing_unit",
        "foreign_unit",
        "scope",
        "candidate",
        "missing_candidate",
    ],
)
def test_original_units_and_candidates_are_never_silently_repaired(change):
    data = context()
    group = data["SOURCE_SYNTACTIC_UNITS"][0]
    unit = group["units"][0]
    if change == "text":
        unit["text"] = "A normalized summary."
    elif change == "hash":
        unit["text_hash"] = "0" * 64
    elif change == "span":
        unit["end"] -= 1
    elif change in {"boolean_offset", "float_offset"}:
        unit["start"] = False if change == "boolean_offset" else 0.0
    elif change == "duplicate_unit":
        group["units"].append(deepcopy(unit))
    elif change == "missing_unit":
        group["units"].pop()
    elif change == "foreign_unit":
        unit["unit_id"] = "U99"
    elif change == "scope":
        group["actual_citation_scope"] = []
    elif change == "candidate":
        group["source_context_candidates"]["source_entailment_certified"] = True
    else:
        group["source_context_candidates"]["rows"].pop()
    with pytest.raises(ValueError):
        encode(data)


@pytest.mark.parametrize(
    "change",
    [
        "claim",
        "fragment",
        "scope",
        "question",
        "gate",
        "candidate",
        "digest",
        "version",
        "instructions",
        "extra_bank",
        "duplicate_bank",
        "missing_bank",
        "unknown_bank",
        "duplicate_column",
        "duplicate_group",
        "missing_group",
        "unknown_group",
        "missing_unit",
        "duplicate_unit",
        "unknown_unit",
        "span",
        "negative_span",
        "boolean_offset",
        "float_offset",
        "extra_unit_text",
    ],
)
def test_encoded_packet_mutations_fail_closed(change):
    value = encode(context())
    group = value["SOURCE_SYNTACTIC_UNITS"][0]
    unit = group["units"][0]
    if change in {"claim", "fragment"}:
        table = value["CLAIMS" if change == "claim" else "SOURCE_FRAGMENTS"]
        table["rows"][0][table["columns"].index("text" if change == "claim" else "exact_text")] += (
            "changed"
        )
    elif change == "scope":
        value["BINDING_BANK"]["rows"][0][
            value["BINDING_BANK"]["columns"].index("allowed_fragment_ids")
        ] = ["F003"]
    elif change == "question":
        value["question"] += "changed"
    elif change == "gate":
        value["POLICY"]["control_evidence"] = False
    elif change == "candidate":
        group["source_context_candidates"]["rows"].pop()
    elif change in {"digest", "version", "instructions"}:
        value["CHECKER_INPUT_ENCODING"][
            "original_data_sha256" if change == "digest" else change
        ] = "changed"
    elif change in {"extra_bank", "duplicate_bank"}:
        row = deepcopy(value["BINDING_BANK"]["rows"][0])
        if change == "extra_bank":
            row[value["BINDING_BANK"]["columns"].index("binding_id")] = "B999"
        value["BINDING_BANK"]["rows"].append(row)
    elif change == "missing_bank":
        value["BINDING_BANK"]["rows"].clear()
    elif change == "unknown_bank":
        table = value["ACTUAL_CITATION_BINDINGS"]
        table["rows"][0][table["columns"].index("binding_ids")] = ["B999"]
    elif change == "duplicate_column":
        value["CLAIMS"]["columns"][0] = value["CLAIMS"]["columns"][1]
    elif change == "duplicate_group":
        value["SOURCE_SYNTACTIC_UNITS"].append(deepcopy(group))
    elif change == "missing_group":
        value["SOURCE_SYNTACTIC_UNITS"].pop()
    elif change == "unknown_group":
        group["claim_id"] = "foreign"
    elif change == "missing_unit":
        group["units"].pop()
    elif change == "duplicate_unit":
        group["units"].append(deepcopy(unit))
    elif change == "unknown_unit":
        unit["unit_id"] = "U99"
    elif change == "span":
        unit["end"] -= 1
    elif change == "negative_span":
        unit["start"] = -1
    elif change in {"boolean_offset", "float_offset"}:
        unit["start"] = False if change == "boolean_offset" else 0.0
    else:
        unit["text"] = "Injected text."
    with pytest.raises(ValueError):
        decode(value)


def test_incomplete_blocks_and_empty_sources_remain_complete_data_not_support():
    data = context()
    data["SOURCE_FRAGMENTS"][0]["complete_block"] = False
    data["SOURCE_SYNTACTIC_UNITS"] = scoped_syntactic_units(
        data["CLAIMS"], data["ACTUAL_CITATION_BINDINGS"], data["SOURCE_FRAGMENTS"]
    )
    assert decode(encode(data)) == data
    assert decode(encode(data))["SOURCE_FRAGMENTS"][0]["complete_block"] is False


def test_legacy_encoder_and_full_output_schema_remain_unchanged():
    data = context()
    old = legacy.encode(data)
    assert decode(encode(data)) == data
    assert legacy.encode(data) == old
    with pytest.raises(ValueError, match="UNKNOWN_FULL_CHECKER_INPUT_ENCODING"):
        decode(old)
    with pytest.raises(ValueError, match="FULL_ENCODING_ALREADY_ENCODED"):
        encode(old)


@pytest.mark.parametrize("change", ["foreign_policy", "compact_output", "missing_policy"])
def test_encoding_is_specific_to_complete_full_source_relation_inputs(change):
    data = context()
    if change == "foreign_policy":
        data["SOURCE_RELATION_POLICY"] = "source_relation_contract_v1"
    elif change == "compact_output":
        data["COMPACT_CONTRACT"] = "scoped_compact_v6"
    else:
        del data["SOURCE_RELATION_POLICY"]
    with pytest.raises(ValueError, match="FULL_ENCODING_POLICY_MISMATCH"):
        encode(data)


@pytest.mark.parametrize("value", [None, [], {}, {"CHECKER_INPUT_ENCODING": None}])
def test_missing_or_malformed_encoding_version_fails_closed(value):
    with pytest.raises(ValueError, match="UNKNOWN_FULL_CHECKER_INPUT_ENCODING"):
        decode(value)


class OfflineCounter:
    def request_input(self, messages, schema, schema_name):
        return estimate_tokens(
            json.dumps(
                {"messages": messages, "schema": schema, "name": schema_name},
                ensure_ascii=False,
            )
        )


def test_small_packet_may_keep_legacy_without_schema_or_message_mutation():
    data = context()
    messages = [
        {"role": "system", "content": "Check every full gate."},
        {"role": "user", "content": json.dumps(data)},
    ]
    schema = {"required": ["attempt_evaluation_ok", "claims", "requirements"]}
    before = deepcopy((messages, schema, data))
    selected, report = select_encoding(data, messages, OfflineCounter(), schema, "full_joint")
    assert (messages, schema, data) == before
    assert report["encoded_input_tokens"] == min(report["candidate_input_tokens"].values())
    assert report["saved_encoding_policy"] == VERSION
    assert report["original_data_sha256"] == report["decoded_data_sha256"]
    assert report["local_semantic_support_certified"] is False
    assert selected[-1]["content"]
