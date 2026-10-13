"""Finite offline protocol controls; no science QA or provider invocation."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import sys
import time
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

MAIN = Path(r"E:\5703\learning-assistant")
HERE = Path(__file__).resolve().parent
W = HERE.parents[1]
RUNTIME = W / "5703-dev89-runtime"
BASE_CASES = ("case01", "case03", "case04", "case05", "case06", "case07", "case08", "case09")
PREIMAGE_SHA = "81045fec9ddc851eda6f445bdd99b20c056de07c36a8acb7264fdbc5c2f5d459"
CANDIDATE_SHA = "8c830694093b41e9f6250939de2cf9f72b24726bddbc1cba0141a6b8cb9efa56"
RESULT = HERE / "control-selection-index89-frozen.json"


def audit(event, args):
    if event.startswith("socket.") or event in {"subprocess.Popen", "os.system", "sqlite3.connect"}:
        raise RuntimeError("OFFLINE_CONTROL_EXTERNAL_ACTION_FORBIDDEN")
    if event == "open":
        target, mode, flags = args
        if not isinstance(target, (str, bytes)):
            return
        path = Path(target).resolve()
        if path.name.casefold().startswith(".env"):
            raise RuntimeError("OFFLINE_CONTROL_AUTH_READ_FORBIDDEN")
        writing = isinstance(mode, str) and any(char in mode for char in "wax+")
        writing = writing or isinstance(flags, int) and bool(flags & (1 | 2 | 64 | 512 | 1024))
        if writing and path != RESULT:
            raise RuntimeError("OFFLINE_CONTROL_WRITE_OUTSIDE_SINGLE_RESULT_FORBIDDEN")


sys.addaudithook(audit)
sys.path.insert(0, str(MAIN))
from generation import lossless_unit_findings_v1 as original
from generation.reliability_v4 import compact_schema
from generation.source_relations_v2 import (
    ReliableUnitCheck,
    scoped_syntactic_units,
)

candidate_path = HERE / "lossless_unit_findings_v1.py"
spec = importlib.util.spec_from_file_location("generation.selection_index_candidate89", candidate_path)
candidate = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = candidate
spec.loader.exec_module(candidate)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def codebook(prepared):
    system = next(row["content"] for row in prepared.messages if row["role"] == "system")
    return json.JSONDecoder().raw_decode(system.split("Codebook: ", 1)[1])[0]


def named_members(tree):
    return {
        node.name: ast.dump(node, include_attributes=False)
        for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))
    }


def unnamed_members(tree):
    return [
        ast.dump(node, include_attributes=False)
        for node in tree.body if not isinstance(node, (ast.FunctionDef, ast.ClassDef))
    ]


def wire_bytes(body):
    return json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def wire_options(body):
    return {key: value for key, value in body.items() if key != "messages"}


def exception_signature(module, projected, context):
    try:
        module.hydrate_findings(projected, context)
    except ValueError as exc:
        return type(exc).__name__, str(exc)
    raise AssertionError("Known malformed actual output unexpectedly accepted")


def main():
    started = time.perf_counter()
    source = MAIN / "generation" / "lossless_unit_findings_v1.py"
    assert sha(source.read_bytes()) == PREIMAGE_SHA
    assert sha(candidate_path.read_bytes()) == CANDIDATE_SHA
    old_tree = ast.parse(source.read_text(encoding="utf-8"))
    new_tree = ast.parse(candidate_path.read_text(encoding="utf-8"))
    # Function positions move by one after the helper; compare named functions/classes
    # independently, and all remaining module statements in original order.
    old_named, new_named = named_members(old_tree), named_members(new_tree)
    assert set(new_named) == set(old_named) | {"_selection_index"}
    assert [key for key in old_named if old_named[key] != new_named[key]] == ["reference_instructions"]
    assert unnamed_members(old_tree) == unnamed_members(new_tree)
    groups = ["single_input_helper_and_reference_instructions_only"]

    expected_claim_keys = {
        "textbook": ["c", "r", "b", "s", "ci", "us"],
        "problem_input": ["c", "r", "b", "s", "pq"],
        "derived_calculation": ["c", "r", "b", "s", "ci", "d"],
        "nonfactual": ["c", "r", "b"],
        "evidence_limitation": ["c", "r", "b"],
        "general_knowledge": ["c", "r", "b", "s"],
    }
    expected_records = {
        "CitationAssessment": ["e", "fs", "rl"],
        "UnitAssessment": ["u", "s", "fs", "rp", "cp", "r"],
        "RequirementCheck": ["k", "rv", "sf", "ev", "cp", "rc", "mi", "r"],
        "RequirementEvidence": ["e", "f", "p"],
    }
    contexts, wire_rows, unchanged_teacher_wires, preserved_pins = {}, [], [], []
    canonical_schema = compact_schema(ReliableUnitCheck)
    public_artifact_count = 0
    for case in BASE_CASES:
        folder = RUNTIME / case / "native-provider70"
        for path in sorted(folder.glob("slot-*-public-inputs.json")):
            public_artifact_count += 1
            record = read_json(path)
            preserved_pins.append((path, sha(path.read_bytes())))
            if record["role"] != "checker":
                teacher_bytes = len(json.dumps(record["normal_compiled_wire"], ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
                unchanged_teacher_wires.append({
                    "case_id": case, "slot": path.name.split("-")[1],
                    "public_input_sha256": sha(path.read_bytes()),
                    "before_complete_wire_bytes": teacher_bytes,
                    "after_complete_wire_bytes": teacher_bytes, "added_wire_bytes": 0,
                    "basis": "No teacher source/compiler changes; saved complete teacher wire retained.",
                })
                continue
            slot = path.name.split("-")[1]
            messages = deepcopy(record["messages"])
            old = original.prepare(messages, canonical_schema)
            new = candidate.prepare(messages, canonical_schema)
            assert messages == record["messages"]
            assert old.context.packet_json == new.context.packet_json
            assert old.context.descriptor() == new.context.descriptor()
            assert old.schema == new.schema
            assert old.context.canonical_schema_sha256 == new.context.canonical_schema_sha256
            assert old.context.wire_codec_fingerprint == new.context.wire_codec_fingerprint
            old_book, new_book = codebook(old), codebook(new)
            index = new_book.pop("selection_index")
            assert old_book == new_book
            assert index["input_only"] is True
            assert set(index) == {
                "input_only", "root_required_short_keys", "claim_required_short_keys_by_basis",
                "record_required_short_keys", "parent_scopes_by_C", "valid_quote_ids_by_fragment",
            }
            assert index["root_required_short_keys"] == old.schema["required"]
            assert index["claim_required_short_keys_by_basis"] == expected_claim_keys
            assert index["record_required_short_keys"] == {
                name: definition["required"]
                for name, definition in old.schema["$defs"].items()
                if definition.get("type") == "object"
            }
            for name, keys in expected_records.items():
                assert index["record_required_short_keys"][name] == keys
            packet = old.context.packet
            units = {row["claim_id"]: row["units"] for row in packet["SOURCE_SYNTACTIC_UNITS"]}
            bindings = {row["claim_id"]: row["citations"] for row in packet["ACTUAL_CITATION_BINDINGS"]}
            assert set(index["parent_scopes_by_C"]) == set(old_book["claim_aliases"])
            for alias, claim_id in old_book["claim_aliases"].items():
                assert index["parent_scopes_by_C"][alias] == {
                    "actual_unit_ids": [unit["unit_id"] for unit in units[claim_id]],
                    "own_source_domains": {row["evidence_id"]: row["allowed_fragment_ids"] for row in bindings[claim_id]},
                }
            catalogue, _ = original._quote_catalogue(packet)
            independently_grouped = {row["fragment_id"]: [] for row in packet["SOURCE_FRAGMENTS"]}
            for pointer, row in catalogue.items():
                independently_grouped[row["fragment_id"]].append(pointer)
            assert index["valid_quote_ids_by_fragment"] == independently_grouped
            new_system = next(row["content"] for row in new.messages if row["role"] == "system")
            assert new_system.count('"selection_index":') == 1
            # Reconstruct the complete saved normal request with identical routing,
            # schema suffix, response_format, reasoning/output limits and numbers.
            before = deepcopy(record["normal_compiled_wire"])
            after = deepcopy(before)
            assert len(before["messages"]) == len(old.messages) == len(new.messages)
            for number, (stored, prior, current) in enumerate(zip(before["messages"], old.messages, new.messages, strict=True)):
                if prior["role"] != "system":
                    assert stored == prior == current
                    continue
                assert stored["role"] == prior["role"] == current["role"]
                assert stored["content"].startswith(prior["content"])
                suffix = stored["content"][len(prior["content"]):]
                assert suffix.startswith("\nOUTPUT FORMAT: ")
                assert suffix.endswith(original._json(old.schema))
                after["messages"][number]["content"] = current["content"] + suffix
            before_bytes, after_bytes = len(wire_bytes(before)), len(wire_bytes(after))
            assert after_bytes < 160000 and after_bytes < 200000
            assert after["max_tokens"] == before["max_tokens"] == 8192
            bound = Decimal(after_bytes) * Decimal("0.3") / Decimal(1000000) + Decimal(8192) * Decimal("2.5") / Decimal(1000000)
            assert bound <= Decimal("0.0714688")
            assert wire_options(before) == wire_options(after)
            assert [row for row in old.messages if row["role"] != "system"] == [row for row in new.messages if row["role"] != "system"]
            wire_rows.append({
                "case_id": case, "slot": slot, "public_input_sha256": sha(path.read_bytes()),
                "before_complete_wire_bytes": before_bytes, "after_complete_wire_bytes": after_bytes,
                "added_wire_bytes": after_bytes - before_bytes,
                "after_wire_sha256_reconstructed_order": sha(wire_bytes(after)),
                "conditional_byte_proxy_cost_bound_usd": str(bound),
                "complete_packet_sha256": sha(old.context.packet_json.encode("utf-8")),
                "claims": old.context.descriptor()["claim_count"],
                "units": old.context.descriptor()["unit_count"],
                "requirements": old.context.descriptor()["requirement_count"],
                "fragments": old.context.descriptor()["fragment_count"],
            })
            contexts[(case, slot)] = (old, new)
    assert public_artifact_count == 24 and len(wire_rows) == 14 and len(unchanged_teacher_wires) == 10
    assert {row["case_id"] for row in wire_rows} == set(BASE_CASES)
    groups.extend([
        "all14_actual_checker_packets_schemas_contexts_and_original_codebooks_unchanged",
        "per_basis_exact_short_keys_nonfactual_no_status_and_citation_rl",
        "all14_exact_C_unit_and_own_evidence_allowlist_coverage_without_selected_evidence",
        "all14_exact_quote_domains_including_valid_whole_F",
        "all14_complete_wire_reconstruction_index_once_schema_suffix_options_and_user_messages_preserved",
        "all8_cases_all14_checker_wires_within_160000_bytes_200000_bytes_and_conditional_hold",
    ])

    actual_negatives = [("case01", "02"), ("case01", "03"), ("case04", "02"), ("case08", "02"), ("case08", "03")]
    negative_rows = []
    for case, slot in actual_negatives:
        path = RUNTIME / case / "native-provider70" / f"slot-{slot}-normal-outcome.json"
        outcome = read_json(path)
        projected = json.loads(outcome["transport_raw_text"])
        old, new = contexts[(case, slot)]
        old_error = exception_signature(original, projected, old.context)
        new_error = exception_signature(candidate, projected, new.context)
        assert old_error == new_error
        negative_rows.append({"case_id": case, "slot": slot, "outcome_sha256": sha(path.read_bytes()), "same_strict_rejection": True})
        preserved_pins.append((path, sha(path.read_bytes())))
    groups.append("five_actual_common_protocol_failures_remain_strictly_rejected_without_defaults_or_alias_repair")

    positive_path = RUNTIME / "case03" / "native-provider70" / "slot-02-normal-outcome.json"
    positive_outcome = read_json(positive_path)
    positive_output = json.loads(positive_outcome["transport_raw_text"])
    old, new = contexts[("case03", "02")]
    old_full = original.hydrate_findings(positive_output, old.context)
    new_full = candidate.hydrate_findings(positive_output, new.context)
    assert old_full == new_full
    assert old_full == json.loads(positive_outcome["raw_text"])
    preserved_pins.append((positive_path, sha(positive_path.read_bytes())))
    assert candidate.encode_findings(new_full, new.context) == original.encode_findings(old_full, old.context) == positive_output
    groups.append("actual_case03_structural_decoder_countercontrol_roundtrip_identical_not_scientific_QA")

    # V2 deliberately replaces the complete V1 suffix, so this V1 reminder must
    # not silently affect the separate V2 wire or activate a default policy.
    from generation import single_selection_findings_v2 as separate_v2
    positive_messages = read_json(RUNTIME / "case03" / "native-provider70" / "slot-02-public-inputs.json")["messages"]
    old_v2 = separate_v2.prepare(positive_messages, canonical_schema)
    saved_legacy = separate_v2.legacy
    try:
        separate_v2.legacy = candidate
        new_v2 = separate_v2.prepare(positive_messages, canonical_schema)
    finally:
        separate_v2.legacy = saved_legacy
    assert old_v2.messages == new_v2.messages and old_v2.schema == new_v2.schema
    assert old_v2.context.descriptor() == new_v2.context.descriptor()
    assert candidate.validate_request(SimpleNamespace(checker_output_policy=None)) is None
    groups.append("separate_v2_wire_unchanged_and_default_policy_remains_unactivated")

    # Authored malformed variants exercise distinct fail-closed boundaries.
    mutations = []
    missing_status = deepcopy(positive_output)
    next(row for row in missing_status["cs"] if row["b"] == "textbook").pop("s")
    mutations.append(("missing_parent_status", missing_status))
    wrong_key = deepcopy(positive_output)
    citation = next(citation for claim in wrong_key["cs"] for citation in claim.get("ci", []))
    citation["relation"] = citation.pop("rl")
    mutations.append(("canonical_relation_in_wire", wrong_key))
    missing_unit = deepcopy(positive_output)
    next(row for row in missing_unit["cs"] if row.get("us")).get("us").pop()
    mutations.append(("missing_actual_parent_unit", missing_unit))
    stale_digest = deepcopy(positive_output)
    stale_digest["h"] = "0" * 64
    mutations.append(("stale_context_digest", stale_digest))
    for label, value in mutations:
        assert exception_signature(original, value, old.context) == exception_signature(candidate, value, new.context)
    groups.append("four_authored_missing_status_wrong_key_missing_unit_stale_digest_negative_controls")

    uncited = candidate._selection_index(contexts[("case01", "02")][1].context)
    assert uncited["parent_scopes_by_C"]["C001"]["own_source_domains"] == {}
    assert uncited["parent_scopes_by_C"]["C002"]["own_source_domains"] == {}
    groups.append("actual_uncited_claim_domains_remain_empty_no_automatic_science_reclassification")

    # Long full sentences have fixed Q ranges; an overlong single sentence has no
    # selected pointer. Both complete original texts remain in the immutable packet.
    packet = deepcopy(new.context.packet)
    first, second = packet["SOURCE_FRAGMENTS"][:2]
    first["exact_text"] = ("A complete authored protocol sentence. " * 45).strip()
    second["exact_text"] = "Z" * 1201
    first["complete_block"] = second["complete_block"] = True
    packet["SOURCE_SYNTACTIC_UNITS"] = scoped_syntactic_units(packet["CLAIMS"], packet["ACTUAL_CITATION_BINDINGS"], packet["SOURCE_FRAGMENTS"])
    long_context = candidate.build_context(packet)
    long_index = candidate._selection_index(long_context)
    quote_rows, unavailable = original._quote_catalogue(packet)
    long_ids = long_index["valid_quote_ids_by_fragment"][first["fragment_id"]]
    assert long_ids and all(key.startswith("Q") for key in long_ids)
    assert long_index["valid_quote_ids_by_fragment"][second["fragment_id"]] == []
    assert long_context.packet["SOURCE_FRAGMENTS"][:2] == packet["SOURCE_FRAGMENTS"][:2]
    assert any(row[0] == second["fragment_id"] for row in unavailable)
    for pointer in long_ids:
        row = quote_rows[pointer]
        assert row["fragment_id"] == first["fragment_id"]
        assert 0 < row["end"] - row["start"] <= 1200
        assert first["exact_text"][row["start"]:row["end"]].strip().endswith(".")
    groups.append("long_Q_and_unselectable_empty_domains_retain_full_original_text_without_fallback")

    assert sha(source.read_bytes()) == PREIMAGE_SHA
    assert sha(candidate_path.read_bytes()) == CANDIDATE_SHA
    assert all(sha(path.read_bytes()) == pin for path, pin in preserved_pins)
    groups.append("source_and_selected_actual_public_artifacts_unchanged_after_controls")
    elapsed = round(time.perf_counter() - started, 6)
    result = {
        "schema": "5703_selection_index89_finite_offline_controls_v1", "status": "PASS",
        "control_groups_passed": len(groups), "control_groups": groups, "elapsed_seconds": elapsed,
        "source_preimage_sha256": PREIMAGE_SHA, "candidate_sha256": CANDIDATE_SHA,
        "actual_public_input_artifacts_read": public_artifact_count, "actual_checker_requests_reconstructed": len(wire_rows),
        "checker_wire_rows": wire_rows, "actual_negative_controls": negative_rows,
        "unchanged_teacher_wire_rows": unchanged_teacher_wires,
        "auth_reads": 0, "database_calls": 0, "model_calls": 0, "network_calls": 0,
        "main_writes": 0, "runtime_writes": 0, "default_activation_changed": False,
        "semantic_and_publication_gates_changed": False, "scientific_QA_claimed": False,
        "byte_measurement": "Saved complete normal_compiled_wire options and exact existing schema suffix; original JSON object key order may differ from historical send, byte length is unchanged by key order.",
        "cost_bound_limitation": "Conditional one-byte-per-input-token proxy and configured max_price(.3/2.5), not tokenizer proof or current provider price confirmation; 8192 output preserved.",
        "actual_retest_blocker": {
            "source": "Root final baseline accounting and frozen nonpage admission policy",
            "baseline_physical_POSTs": 24, "baseline_cost_usd": "0.3557883", "UNKNOWN": 0,
            "nonpage_POST_cap": 24, "admission_case_reservation": 4,
            "condition": "24 + 4 <= 24 is false", "reason": "Frozen nonpage policy; no authorization or fee shortage claimed.",
        },
        "candidate_status": "W-only software controls; not adopted; no actual affected/control model retest or science/page promotion",
    }
    with RESULT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "groups": len(groups), "elapsed_seconds": elapsed, "wires": len(wire_rows), "max_after_bytes": max(row["after_complete_wire_bytes"] for row in wire_rows), "result_sha256": sha(RESULT.read_bytes())}))


if __name__ == "__main__":
    main()
