"""Release-only lossless checker encoding and configured-window boundaries."""

from copy import deepcopy
from dataclasses import replace
import json

import pytest

from generation import GenerationService
from generation.checker_encoding import VERSION, encode, decode, dumps, select_encoding
from generation.reliability_v4 import ReliableCheckV4, compact_schema
from generation.token_counting import TokenCounter
from test_enhancement_generation import Script, answer
from test_teaching_contracts_v4 import req, check


def payload():
    return {
        "CLAIMS": [
            {"claim_id": "c1", "text": "Keep negation: not X; 3.00 kg.", "evidence_ids": ["e1"]},
            {"claim_id": "c2", "text": "Condition: at 20 °C.", "evidence_ids": ["e1", "e2"]},
            {"claim_id": "c3", "text": "Consider the next step.", "evidence_ids": []},
        ],
        "SOURCE_FRAGMENTS": [
            {
                "fragment_id": "F001",
                "evidence_id": "e1",
                "exact_text": "not X\n3.00 kg",
                "complete_block": True,
            },
            {
                "fragment_id": "F002",
                "evidence_id": "e2",
                "exact_text": "Only at 20 °C.",
                "complete_block": True,
            },
        ],
        "ACTUAL_CITATION_BINDINGS": [
            {
                "claim_id": "c1",
                "citations": [{"evidence_id": "e1", "allowed_fragment_ids": ["F001"]}],
            },
            {
                "claim_id": "c2",
                "citations": [
                    {"evidence_id": "e1", "allowed_fragment_ids": ["F001"]},
                    {"evidence_id": "e2", "allowed_fragment_ids": ["F002"]},
                ],
            },
            {"claim_id": "c3", "citations": []},
        ],
        "PROPOSED_DELIVERY": {"body": "not X\n3.00 kg [e1]"},
        "PRIOR_EXPOSURE": {"body": "Previous full text."},
    }


def test_round_trip_preserves_source_bytes_conditions_binding_and_untouched_input():
    original = payload()
    before = deepcopy(original)
    encoded = encode(original)
    assert decode(json.loads(dumps(encoded))) == before == original
    assert len(encoded["BINDING_BANK"]["rows"]) == 2
    assert encoded["ACTUAL_CITATION_BINDINGS"]["rows"][-1][0] == []


def test_different_visible_allowlists_for_same_source_remain_distinct():
    original = payload()
    original["ACTUAL_CITATION_BINDINGS"][1]["citations"][0]["allowed_fragment_ids"] = []
    encoded = encode(original)
    assert len(encoded["BINDING_BANK"]["rows"]) == 3
    assert decode(encoded) == original


def test_empty_and_heterogeneous_rows_retain_presence_and_null_distinction():
    original = payload()
    original["CLAIMS"][0]["optional"] = None
    original["SOURCE_FRAGMENTS"] = []
    assert decode(encode(original)) == original


def decoded_check(messages):
    restored = deepcopy(messages)
    for message in restored:
        if message["content"].startswith("{"):
            data = json.loads(message["content"])
            if "CHECKER_INPUT_ENCODING" in data:
                message["content"] = json.dumps(decode(data), ensure_ascii=False)
    return check(restored)


def test_new_policy_checks_exact_delivered_response_and_preserves_legacy_default():
    old = GenerationService(Script([answer(), check])).generate(req())
    new = GenerationService(Script([answer(), decoded_check])).generate(
        req(checker_payload_policy=VERSION)
    )
    assert old.succeeded and new.succeeded
    assert new.response == old.response
    assert new.checks[0]["actual_citation_bindings"] == old.checks[0]["actual_citation_bindings"]
    assert old.token_budget["checker_payload_encodings"][0]["encoding"] == "fragment_objects"
    choices = new.token_budget["checker_payload_encodings"][0]
    assert choices["encoded_input_tokens"] == min(choices["candidate_input_tokens"].values())
    assert new.token_budget["checker_payload_policy"] == VERSION
    assert req().checker_payload_policy == "legacy_fragment_table_v1"


def test_compaction_crosses_a_fixed_window_without_altering_sources_or_output_budget():
    original = payload()
    references = [f"F{number:03d}" for number in range(1, 61)]
    original["CLAIMS"] = [
        {"claim_id": f"c{i}", "text": f"Exact condition {i}.", "evidence_ids": ["e1"]}
        for i in range(20)
    ]
    original["ACTUAL_CITATION_BINDINGS"] = [
        {
            "claim_id": f"c{i}",
            "citations": [{"evidence_id": "e1", "allowed_fragment_ids": references}],
        }
        for i in range(20)
    ]
    counter = TokenCounter(req().config)
    schema = compact_schema(ReliableCheckV4)
    old = counter.request_input(
        [{"role": "user", "content": json.dumps(original)}], schema, "joint_check_v4"
    )
    new = counter.request_input(
        [{"role": "user", "content": dumps(encode(original))}], schema, "joint_check_v4"
    )
    output = 4096
    fixed_window = new + output
    assert old + output > fixed_window == new + output
    assert old - new > 1000
    assert decode(encode(original)) == original


def test_fixed_checker_limit_still_rejects_instead_of_dropping_source_fields():
    value = req(checker_payload_policy=VERSION)
    value = replace(value, checker_config=replace(value.config, window_tokens=100, max_tokens=50))
    out = GenerationService(Script([answer()])).generate(value)
    assert not out.succeeded and out.error["code"] == "CONTEXT_LIMIT"
    assert out.budget["consumed_calls"] <= 1


def test_small_complete_object_still_fits_when_table_instructions_would_overflow():
    original = {
        "CLAIMS": [],
        "SOURCE_FRAGMENTS": [],
        "ACTUAL_CITATION_BINDINGS": [],
        "answer_mode": "general_knowledge",
    }
    counter = TokenCounter(req().config)
    schema = compact_schema(ReliableCheckV4)
    messages = [{"role": "user", "content": json.dumps(original, sort_keys=True)}]
    selected, report = select_encoding(original, messages, counter, schema, "joint_check_v4")
    output_reserve = 4096
    cap = report["candidate_input_tokens"]["fragment_objects"] + output_reserve
    assert report["candidate_input_tokens"][VERSION] + output_reserve > cap
    assert report["encoded_input_tokens"] + output_reserve <= cap
    assert report["encoding"] == "fragment_objects"
    assert not report["exact_round_trip_verified"]
    assert selected == messages


@pytest.mark.parametrize("bad", ["unchecked", "", "future_encoding"])
def test_unknown_encoding_policy_cannot_publish(bad):
    out = GenerationService(Script([answer(), check])).generate(req(checker_payload_policy=bad))
    assert not out.succeeded and not out.attempts
