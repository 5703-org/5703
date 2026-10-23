"""One authored real GenerationService repair/codec integration case.

PREPARED ONLY; author has not executed these two cases. Scripted verdicts test transport and
protection, not independent model quality. Uses public unit-test helpers, no
workspace auth/fixtures, database, provider configuration or network adapters.

Future import: generation.claim_feedback_transport_v1 (frozen codec b937...).
Adapted from test_source_relation_protection27_release.py SHA12fdfd0d...409b.
"""

from copy import deepcopy
from dataclasses import replace
import json

from generation import GenerationService, ModelConfig, RequestBudget
from generation import checked as checked_module
from generation.claim_feedback_transport_v1 import (
    VERSION as CODEC_VERSION,
    HEADER,
    BODY as FEEDBACK_BODY,
    DRAFT,
    INSTRUCTIONS,
    canonical_bytes,
    canonical_hash,
    decode_claim_feedback,
)
from generation.local_repair import VERSION as CLAIM_PATCH_POLICY
from generation.reliability_v4 import normalize_judgment
from generation.reliability_v5 import protected_claims
from generation.source_relations_v2 import VERSION as RELATION_VERSION, assess_source_relations
from retrieval.source_spans import text_hash
from test_answer_core_v5 import req
from test_enhancement_generation import Script, answer
from test_source_relation_units_v2 import check_input, unit_checker


MARKER = "REPAIR_DATA_JSON:\n"
GATES = ("scope_ok", "suggestions_ok", "evidence_display_ok", "cumulative_ok")
# Runtime strings really contain U+0000/U+0001, Han, U+1F9EC, CR and LF.
# Explicit source blocks keep the repeated lines whole. Claims replace CRLF
# with a space to keep each cited claim a single exact response span.
CONTROL_SEQUENCE = "\x00\x01\u7532\U0001f9ec\r\n"
SOURCE_PADDING = (" neutral" + CONTROL_SEQUENCE) * 55
CLAIM_PADDING = SOURCE_PADDING.replace("\r\n", " ")
DEVICE_SOURCE = "The device transfers stored energy" + SOURCE_PADDING + "."
VESSEL_SOURCE = "The vessel stores material" + SOURCE_PADDING + "."
INLET_SOURCE = "The material enters the vessel through an inlet."
SOURCE_PARTS = (DEVICE_SOURCE, VESSEL_SOURCE, INLET_SOURCE)
SOURCE = " ".join(SOURCE_PARTS)
GOOD = "The device transfers stored energy" + CLAIM_PADDING + "[ev_001]."
TARGET = (
    "The vessel stores material" + CLAIM_PADDING + "and creates material without input [ev_001]."
)
REPLACEMENT = "The vessel stores material" + CLAIM_PADDING + "[ev_001]."
SHORT = "The device transfers stored energy [ev_001]."
INITIAL_BODY = TARGET + " " + GOOD


def _typed_signature(value):
    if type(value) is dict:
        return (dict, [(key, _typed_signature(value[key])) for key in sorted(value)])
    if type(value) is list:
        return (list, [_typed_signature(item) for item in value])
    if type(value) is float:
        return (float, value.hex())
    return (type(value), value)


def _request_fixture(source_parts=SOURCE_PARTS):
    source = " ".join(source_parts)
    value = req(
        question="Explain the device's energy transfer and the vessel's material storage.",
        answer_mode="textbook",
        teaching_context={"teaching_mode": "direct", "help_level": 0},
        joint_checker_policy="typed_joint_v5",
        source_relation_policy=RELATION_VERSION,
        repair_policy=CLAIM_PATCH_POLICY,
        config=ModelConfig(tokenizer_provider="estimate", window_tokens=131072),
    )
    evidence, mapping = deepcopy(value.evidence), deepcopy(value.source_map)
    evidence[0].update(text=source, text_hash=text_hash(source), section="Authored Unicode device")
    chunk = mapping["c1"]
    chunk.update(chunk_text=source, chunk_hash=text_hash(source))
    unit = chunk["units"][0]
    blocks, start = [], 0
    for part in source_parts:
        blocks.append({"start": start, "end": start + len(part), "kind": "prose"})
        start += len(part) + 1
    unit.update(cleaned_text=source, text_hash=text_hash(source), blocks=blocks)
    chunk["spans"][0].update(end=len(source), chunk_end=len(source))
    return replace(value, evidence=evidence, source_map=mapping)


def _relation_checker(state, *, adverse=False, target_text=TARGET, source_parts=SOURCE_PARTS):
    def callback(messages):
        data = check_input(messages)
        fragments = data["SOURCE_FRAGMENTS"]
        by_text = {row["exact_text"].strip(): row for row in fragments}
        assert len(fragments) == 3 and set(by_text) == set(source_parts)
        assert all(row["complete_block"] for row in fragments)
        claims = {row["claim_id"]: row for row in data["CLAIMS"]}
        bindings = {row["claim_id"]: row for row in data["ACTUAL_CITATION_BINDINGS"]}
        target_ids = [cid for cid, row in claims.items() if row["text"] == target_text]
        assert len(claims) == 3 and len(target_ids) == 1
        target_id = target_ids[0]
        judgment = unit_checker(messages)
        assert judgment["body_ok"] is True and all(judgment[gate] is True for gate in GATES)
        for row in judgment["claims"]:
            assert row["basis"] == "textbook" and row["status"] == "supported"
            cid = row["claim_id"]
            fragment = by_text[source_parts[1] if cid == target_id else source_parts[0]]
            citation = bindings[cid]["citations"]
            assert len(citation) == 1 and citation[0]["evidence_id"] == "ev_001"
            assert fragment["fragment_id"] in citation[0]["allowed_fragment_ids"]
            row["citations"] = [
                {
                    "evidence_id": "ev_001",
                    "relation": "supporting",
                    "fragment_ids": [fragment["fragment_id"]],
                }
            ]
            for unit in row["units"]:
                unit["fragment_ids"] = [fragment["fragment_id"]]
        normalized, binding_issues = normalize_judgment(
            deepcopy(judgment), data["ACTUAL_CITATION_BINDINGS"]
        )
        assert not binding_issues and all(row["factual"] for row in normalized["claims"])
        baseline = protected_claims(data["CLAIMS"], normalized, [])
        assert baseline == data["CLAIMS"]
        target = next(row for row in judgment["claims"] if row["claim_id"] == target_id)
        if adverse:
            assert len(target["units"]) == 2
            target["units"][-1].update(status="unsupported", relation_preserved=False)
        contract, defects, assessment = assess_source_relations(
            judgment, data["CLAIMS"], data["ACTUAL_CITATION_BINDINGS"], fragments
        )
        assert not contract
        if adverse:
            assert defects and not assessment["accepted"]
            assert {row["claim_id"] for row in defects} == {target_id}
            assert (
                sum(
                    unit["status"] != "supported"
                    for row in judgment["claims"]
                    for unit in row["units"]
                )
                == 1
            )
        else:
            assert not defects and assessment["accepted"]
        state.update(
            claims=deepcopy(data["CLAIMS"]),
            judgment=deepcopy(judgment),
            target_id=target_id,
            defects=deepcopy(defects),
            baseline_protected=deepcopy(baseline),
        )
        return judgment

    return callback


def test_real_service_large_unicode_claim_patch_chooses_lossless_wire_and_preserves_raw(
    monkeypatch,
):
    """Four scripted calls: draft, one adverse unit, local patch, complete recheck."""
    initial, final, captured = {}, {}, {}
    value = _request_fixture()
    untouched = deepcopy((value.evidence, value.source_map))
    original_projector = checked_module._compact_claim_patch_feedback
    original_encoder = checked_module.encode_claim_feedback

    def observe_projector(feedback):
        before = _typed_signature(feedback)
        projected = original_projector(feedback)
        assert _typed_signature(feedback) == before
        if "source_relation_assessment" in feedback:
            captured["raw_ref"] = feedback
            captured["raw_snapshot"] = deepcopy(feedback)
            captured["projected_snapshot"] = deepcopy(projected)
        return projected

    def observe_encoder(feedback, **options):
        before = _typed_signature(feedback)
        payload, proof = original_encoder(feedback, **options)
        assert _typed_signature(feedback) == before
        assert proof["encoding"] == CODEC_VERSION
        captured.update(
            projected=deepcopy(feedback),
            options=deepcopy(options),
            encoded=deepcopy(payload),
            codec_proof=deepcopy(proof),
        )
        return payload, proof

    monkeypatch.setattr(checked_module, "_compact_claim_patch_feedback", observe_projector)
    monkeypatch.setattr(checked_module, "encode_claim_feedback", observe_encoder)

    def patch(messages):
        content = messages[-1]["content"]
        prefix, encoded_json = content.rsplit(MARKER, 1)
        trusted = "\nServer transport instructions: " + INSTRUCTIONS + "\n"
        assert trusted in prefix and prefix.count(INSTRUCTIONS) == 1
        assert content.index(trusted) < content.rfind(MARKER)
        packet = json.loads(encoded_json)
        assert packet[HEADER]["version"] == CODEC_VERSION
        assert packet[HEADER]["instructions"] == INSTRUCTIONS
        assert canonical_hash(packet) == canonical_hash(captured["encoded"])
        assert "\\u0000" in encoded_json and "\\u0001" in encoded_json
        assert (
            "\u7532" in packet[DRAFT]["answer_text"]
            and "\U0001f9ec" in packet[DRAFT]["answer_text"]
        )
        decoded = decode_claim_feedback(packet, encoded=True, **captured["options"])
        expected = captured["projected"]
        assert _typed_signature(decoded) == _typed_signature(expected)
        assert (
            canonical_hash(decoded)
            == canonical_hash(expected)
            == captured["codec_proof"]["original_sha256"]
        )
        assert _typed_signature(captured["projected_snapshot"]) == _typed_signature(expected)
        assert _typed_signature(captured["raw_ref"]) == _typed_signature(captured["raw_snapshot"])
        assert decoded["original_claims"] == initial["claims"]
        target_id = initial["target_id"]
        expected_protected = [
            row for row in initial["baseline_protected"] if row["claim_id"] != target_id
        ]
        assert decoded["protected_exact_claims"] == expected_protected
        assert decoded["editable_claim_ids"] == [target_id]
        assert (
            decoded["draft"]["answer_text"] == INITIAL_BODY
            and decoded["draft"]["short_answer"] == SHORT
        )
        assert decoded["source_repair_candidates"] == expected["source_repair_candidates"]
        assert decoded.get("source_ref_version") == expected.get("source_ref_version")
        assert decoded["structural_issues"] and {
            row["claim_id"] for row in decoded["structural_issues"]
        } == {target_id}
        assert captured["codec_proof"]["claim_span_count"] == 3
        assert captured["codec_proof"]["protected_claim_ref_count"] == 2
        assert captured["codec_proof"]["source_quote_ref_count"] >= 3
        meta, transmitted = packet[HEADER], packet[FEEDBACK_BODY]
        multibyte_claim_offset = False
        for index in meta["claim_span_indices"]:
            row = decoded["original_claims"][index]
            field, start, end = transmitted["original_claims"][index]["text"]["draft_span"]
            text = packet[DRAFT][field]
            assert type(start) is int and type(end) is int
            assert text[start:end] == row["text"]
            assert (start, end) == (row["start"], row["end"])
            multibyte_claim_offset |= len(text[:start].encode("utf-8")) != start
        assert multibyte_claim_offset
        contexts = [
            json.loads(message["content"].split("\n", 1)[1])
            for message in captured["options"]["messages"]
            if message["role"] == "system" and message["content"].startswith("CONTEXT_DATA_JSON:\n")
        ]
        assert len(contexts) == 1
        current = {row["evidence_id"]: row["text"] for row in contexts[0]["CURRENT_EVIDENCE"]}
        assert CONTROL_SEQUENCE in current["ev_001"]
        multibyte_source_offset = False
        for ci, oi, qi in meta["source_quote_paths"]:
            wire_row = transmitted["source_relation_assessment"]["claims"][ci]["obligations"][oi][
                "source_quotes"
            ][qi]
            restored_row = decoded["source_relation_assessment"]["claims"][ci]["obligations"][oi][
                "source_quotes"
            ][qi]
            eid, start, end = wire_row["quote"]["source_span"]
            assert current[eid][start:end] == restored_row["quote"]
            assert wire_row["fragment_id"] == restored_row["fragment_id"]
            assert CONTROL_SEQUENCE in restored_row["quote"]
            multibyte_source_offset |= len(current[eid][:start].encode("utf-8")) != start
        assert multibyte_source_offset
        # Measure JSON escaping a second time at the outer message boundary.
        # Identical provider fields/common prompts cancel in this byte delta;
        # no provider adapter, payload submission or network is invoked here.
        if encoded_json == canonical_bytes(packet).decode("utf-8"):
            full_wire = canonical_bytes(expected).decode("utf-8")
        else:
            assert encoded_json == checked_module._json(packet)
            full_wire = checked_module._json(expected)
        baseline_content = prefix.replace(trusted, "", 1) + MARKER + full_wire
        baseline_messages = deepcopy(messages)
        baseline_messages[-1]["content"] = baseline_content
        compact_json = lambda item: json.dumps(
            item, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
        selected_outer_content, full_outer_content = (
            compact_json(content),
            compact_json(baseline_content),
        )
        selected_outer_messages, full_outer_messages = (
            compact_json(messages),
            compact_json(baseline_messages),
        )
        assert b"\\\\u0000" in selected_outer_content and b"\\\\u0001" in selected_outer_content
        assert len(selected_outer_content) < len(full_outer_content)
        assert len(selected_outer_messages) < len(full_outer_messages)
        assert len(full_outer_content) - len(selected_outer_content) == (
            len(full_outer_messages) - len(selected_outer_messages)
        )
        captured.update(
            decoded=deepcopy(decoded),
            encoded_json=encoded_json,
            trusted=trusted,
            selected_wire_bytes=len((trusted + encoded_json).encode("utf-8")),
            full_wire_bytes=len(full_wire.encode("utf-8")),
            serialized_selected_fragment_bytes=len(compact_json(trusted + encoded_json)),
            serialized_full_fragment_bytes=len(compact_json(full_wire)),
            serialized_selected_messages_bytes=len(selected_outer_messages),
            serialized_full_messages_bytes=len(full_outer_messages),
        )
        return {
            "edits": [{"claim_id": target_id, "replacement_text": REPLACEMENT}],
            "append_answer_text": "",
        }

    adapter = Script(
        [
            answer(INITIAL_BODY, short_answer=SHORT),
            _relation_checker(initial, adverse=True),
            patch,
            _relation_checker(final, target_text=REPLACEMENT),
        ]
    )
    out = GenerationService(adapter).generate(value, RequestBudget(max_calls=4))
    assert out.succeeded, out.error
    assert len(adapter.calls) == out.budget["consumed_calls"] == 4
    assert adapter.calls[2][1]["request_context"]["purpose"] == "semantic_repair"
    assert adapter.calls[2][1]["response_schema_name"] == "claim_patch_repair_v1"
    assert adapter.calls[3][1]["response_schema_name"] == "joint_check_source_relations_v2"
    assert len(out.checks) == 2 and out.checks[-1]["source_relation_assessment"]["accepted"]
    assert (
        out.response["answer_text"] == REPLACEMENT + " " + GOOD
        and out.response["short_answer"] == SHORT
    )
    assert (value.evidence, value.source_map) == untouched
    assert _typed_signature(captured["raw_ref"]) == _typed_signature(captured["raw_snapshot"])
    transport = out.checks[0]["claim_feedback_transport"]
    assert transport["selected_wire_encoding"] == CODEC_VERSION
    assert transport["authoritative_server_feedback_changed"] is False
    assert transport["trusted_instruction_included_in_wire_measurement"] is True
    assert transport["raw_server_feedback_sha256"] == canonical_hash(captured["raw_snapshot"])
    assert transport["projected_feedback_sha256"] == canonical_hash(captured["decoded"])
    assert transport["full_content_utf8_bytes"] == captured["full_wire_bytes"]
    assert transport["selected_content_utf8_bytes"] == captured["selected_wire_bytes"]
    assert (
        transport["full_serialized_content_utf8_bytes"]
        == captured["serialized_full_fragment_bytes"]
    )
    assert (
        transport["selected_serialized_content_utf8_bytes"]
        == captured["serialized_selected_fragment_bytes"]
    )
    assert transport["wire_delta_basis"] == "same_remaining_body_and_outer_JSON_string_serializer"
    assert transport["saved_provider_wire_utf8_bytes"] == (
        captured["serialized_full_fragment_bytes"] - captured["serialized_selected_fragment_bytes"]
    )
    assert transport["saved_provider_wire_utf8_bytes"] > 0
    assert (
        captured["serialized_full_messages_bytes"] > captured["serialized_selected_messages_bytes"]
    )
    initial_by_id = {row["claim_id"]: row for row in initial["claims"]}
    final_by_id = {row["claim_id"]: row for row in final["claims"]}
    unaffected = {
        row["claim_id"]
        for row in initial["baseline_protected"]
        if row["claim_id"] != initial["target_id"]
    }
    assert len(unaffected) == 2 and unaffected <= final_by_id.keys()
    for cid in unaffected:
        assert final_by_id[cid]["answer_field"] == initial_by_id[cid]["answer_field"]
        assert final_by_id[cid]["text"] == initial_by_id[cid]["text"]
    assert initial["target_id"] != final["target_id"] and initial["target_id"] not in final_by_id
    assert out.checks[0]["source_relation_protection_invalidation"][
        "protection_removed_claim_ids"
    ] == [initial["target_id"]]
    assert (
        out.checks[0]["source_relation_protection_invalidation"]["unattributed_protection_losses"]
        == []
    )


def test_real_service_small_claim_patch_keeps_full_feedback_without_codec_instructions(monkeypatch):
    """Small authored feedback follows the full branch through all four calls."""
    parts = (
        "The device transfers stored energy.",
        "The vessel stores material.",
        "The material enters the vessel through an inlet.",
    )
    good, target = SHORT, "The vessel stores material and creates material without input [ev_001]."
    replacement = "The vessel stores material [ev_001]."
    initial, final, captured = {}, {}, {}
    value = _request_fixture(source_parts=parts)
    untouched = deepcopy((value.evidence, value.source_map))
    original_encoder = checked_module.encode_claim_feedback

    def observe_encoder(feedback, **options):
        snapshot = deepcopy(feedback)
        payload, proof = original_encoder(feedback, **options)
        assert _typed_signature(feedback) == _typed_signature(snapshot)
        captured.update(projected=snapshot, payload=deepcopy(payload), proof=deepcopy(proof))
        return payload, proof

    monkeypatch.setattr(checked_module, "encode_claim_feedback", observe_encoder)

    def patch(messages):
        prefix, packet_json = messages[-1]["content"].rsplit(MARKER, 1)
        packet = json.loads(packet_json)
        assert "Server transport instructions: " not in prefix and INSTRUCTIONS not in prefix
        assert HEADER not in packet
        restored = decode_claim_feedback(packet, encoded=False)
        assert _typed_signature(restored) == _typed_signature(captured["projected"])
        assert canonical_hash(restored) == captured["proof"]["original_sha256"]
        expected_protected = [
            row for row in initial["baseline_protected"] if row["claim_id"] != initial["target_id"]
        ]
        assert restored["original_claims"] == initial["claims"]
        assert restored["protected_exact_claims"] == expected_protected
        assert restored["editable_claim_ids"] == [initial["target_id"]]
        assert restored["draft"]["answer_text"] == target + " " + good
        return {
            "edits": [{"claim_id": initial["target_id"], "replacement_text": replacement}],
            "append_answer_text": "",
        }

    adapter = Script(
        [
            answer(target + " " + good, short_answer=SHORT),
            _relation_checker(initial, adverse=True, target_text=target, source_parts=parts),
            patch,
            _relation_checker(final, target_text=replacement, source_parts=parts),
        ]
    )
    out = GenerationService(adapter).generate(value, RequestBudget(max_calls=4))
    assert out.succeeded, out.error
    assert len(adapter.calls) == out.budget["consumed_calls"] == 4
    assert adapter.calls[2][1]["response_schema_name"] == "claim_patch_repair_v1"
    assert (
        out.response["answer_text"] == replacement + " " + good
        and out.response["short_answer"] == SHORT
    )
    assert (value.evidence, value.source_map) == untouched
    transport = out.checks[0]["claim_feedback_transport"]
    assert transport["selected_wire_encoding"] == checked_module.FULL_CLAIM_FEEDBACK
    assert transport["authoritative_server_feedback_changed"] is False
    assert transport["saved_provider_wire_utf8_bytes"] == 0
    assert transport["selected_content_utf8_bytes"] == transport["full_content_utf8_bytes"]
    assert (
        transport["selected_serialized_content_utf8_bytes"]
        == transport["full_serialized_content_utf8_bytes"]
    )
    assert transport["projected_feedback_sha256"] == canonical_hash(captured["projected"])
    assert out.checks[-1]["source_relation_assessment"]["accepted"]
