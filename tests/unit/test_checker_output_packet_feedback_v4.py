"""Real correction-message layout; original input and feedback stay unchanged."""

import importlib.util
import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from generation import checker_encoding, checker_encoding_v2
from generation.reliability_v4 import compact_schema
from generation.source_relations_v2 import ReliableUnitCheck, scoped_syntactic_units

HELPER = Path(__file__).with_name("test_checker_output_projection_v1.py")
SPEC = importlib.util.spec_from_file_location("feedback_public_fixture84", HELPER)
assert SPEC is not None and SPEC.loader is not None
fixture_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = fixture_module
SPEC.loader.exec_module(fixture_module)
codec = fixture_module.codec


def packet_message(packet):
    return {"role": "user", "content": json.dumps(packet, ensure_ascii=False)}


def ordinary_fixture():
    packet, full = fixture_module.fixture()
    packet.update(
        answer_mode="textbook",
        LEARNER_TURN={"turn_role": "user_question"},
        ATTEMPT_EVALUATION=None,
        TUTOR_QUESTION=None,
    )
    packet["SOURCE_SYNTACTIC_UNITS"] = scoped_syntactic_units(
        packet["CLAIMS"], packet["ACTUAL_CITATION_BINDINGS"], packet["SOURCE_FRAGMENTS"]
    )
    return packet, full


def test_unique_encoded_packet_before_correction_feedback_preserves_every_message():
    packet, full = ordinary_fixture()
    feedback = {
        "role": "user",
        "content": "Re-evaluate exactly the same unchanged draft and source display. "
        "Your previous check had contract contradictions. Preserve honest unsupported/partial "
        "decisions. CHECKER_CONTRACT_ISSUES_JSON:\n"
        '[{"code":"citation_fragment_scope","field":"CLAIMS"}]',
    }
    for encode in (checker_encoding.encode, checker_encoding_v2.encode):
        messages = [
            {"role": "system", "content": "Use the complete canonical checker contract."},
            packet_message(encode(packet)),
            {"role": "assistant", "content": "Previous withheld checker reply."},
            feedback,
            {"role": "user", "content": '{"field_errors":[],"instruction":"try again"}'},
        ]
        before = deepcopy(messages)
        prepared = codec.prepare(messages, compact_schema(ReliableUnitCheck))
        assert messages == before
        assert prepared.messages[1:] == before[1:]
        assert prepared.messages[0]["content"].startswith(before[0]["content"] + "\n\n")
        assert prepared.context.packet == packet
        assert codec.decode(codec.encode_full(full, prepared.context), prepared.context) == full


def test_duplicate_or_packet_like_second_input_rejects_without_selecting_first_or_last():
    packet, _ = ordinary_fixture()
    for second in (packet, {"CLAIMS": []}, {"CHECKER_INPUT_ENCODING": {"version": "fake"}}):
        messages = [
            {"role": "system", "content": "Original checker."},
            packet_message(packet),
            packet_message(second),
            {"role": "user", "content": "Correct only the judgment."},
        ]
        before = deepcopy(messages)
        with pytest.raises(ValueError, match="PACKET_AMBIGUOUS"):
            codec.prepare(messages, compact_schema(ReliableUnitCheck))
        assert messages == before


def test_missing_malformed_or_single_pseudo_packet_cannot_be_feedback_fallback():
    for content in (
        "Correct only the judgment using the supplied exact claims and aliases.",
        '{"SOURCE_RELATION_POLICY":"source_relation_contract_v2"}',
        '{"CHECKER_INPUT_ENCODING":',
        '{"CLAIMS":[]}',
    ):
        messages = [
            {"role": "system", "content": "Original checker."},
            {"role": "user", "content": content},
        ]
        before = deepcopy(messages)
        with pytest.raises(ValueError):
            codec.prepare(messages, compact_schema(ReliableUnitCheck))
        assert messages == before
    packet, _ = ordinary_fixture()
    for malformed in (
        '{"CLAIMS":[],"CLAIMS":[]}',
        '{"unrelated_feedback":NaN}',
        '{"CL\\u0041IMS":',
        '[{"CLAIMS":[]}]',
        '```json\n{"CLAIMS":[]}\n```',
        '\ufeff{"CLAIMS":[]}',
    ):
        messages = [
            {"role": "system", "content": "Original checker."},
            packet_message(packet),
            {"role": "user", "content": malformed},
        ]
        before = deepcopy(messages)
        with pytest.raises(ValueError, match="BAD_PACKET_USER_MESSAGE"):
            codec.prepare(messages, compact_schema(ReliableUnitCheck))
        assert messages == before
