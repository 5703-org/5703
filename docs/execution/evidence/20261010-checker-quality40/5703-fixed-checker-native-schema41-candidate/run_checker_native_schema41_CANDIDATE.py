"""One finite native-schema diagnostic of the unchanged candidate40 draft.

The closed json_object baseline and candidate are reconstructed offline only.
One request changes the output mode to full native json_schema.  This is not
a matched pair.  Root alone may execute the one call.  The original
approved credential consumer performs one read-only isolated credential leg;
the experiment itself does not open a database, teacher, browser or model cache.
"""

from __future__ import annotations

import argparse
import ast
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import importlib.util
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
import time
import types
from urllib import error as urlerror

W = Path(r"C:\Users\PC\Documents\Codex\2026-10-04\task-2")
MAIN = Path(r"E:\5703\learning-assistant")
B = W / "5703-week10-native-pair-20261009-01"
D = B / "diagnostic-preparation"
HERE = Path(__file__).absolute().parent
RUNTIME36 = B / "scientific-native-closure36/runtime"
DATA36 = RUNTIME36 / "retained-provider-diagnostics"
URL = "https://openrouter.ai/api/v1/chat/completions"
SOLE_DB = "cs30_week10_pair_b_20261009_01"
SCHEMA_NAME = "joint_check_source_relations_v2"
SCHEMA_SHA = "864212a5e636d2cadbc34328f431712a954c30130848a31e64e66e4bdedbc926"
ORIGINAL_DATA_SHA = "b0149e818ec57662235cc671da8be22afaf107c45211287453eef446dac7924a"
ORIGINAL_MESSAGES_SHA = "5ad251be2eff1a4c3d3e7115b81bc4a23f75528338237cbd27b604800e59288a"
ORIGINAL_BODY_SHA = "6082c9c9351f3076556a9773a0984754b734330e068936e1a2b5693a2ea59b2b"
ORIGINAL_CANONICAL_BODY_SHA = "9c43c122dcb6bbdc4599dcb0be0ee848e34d168807c6da89a9bff3eb20c5adf5"
ORIGINAL_CONTROLS_SHA = "9106c8c5dfd60ef22fdae09f3bb25db67e4bd6fb6cfbdf7eccea249b89960eff"
PER = Decimal("0.04500000")
TOTAL = Decimal("0.04500000")
PRIOR_COST = Decimal("0.17182790")
GROUP_LIMIT = Decimal("0.24000000")
MAX_WIRE = 98304
OUTPUT = 4096
ARMS = ("native_schema41",)
PINS = {
    "initial": (DATA36 / "slot-02-model-output01.json", 56525,
                "f3ed73ca40b0258998ef25d9d4d1fa74ace5e060cd1140b0ccca07bf831e1e67"),
    "final": (DATA36 / "slot-04-model-output01.json", 51850,
              "af450f2b56bb949f10bfcaf4f6fc64a7174ae4dbc2e663658afb2c4dcbfbaca4"),
    "outcome": (DATA36 / "native-generation-outcome01.json", 833871,
                "bb4a50a877a49a9103ea15e26ccb35b6000451c337989e3f46fad376e5abe517"),
    "acceptance": (W / "5703-native36-fixed-pair-acceptance/ACTUAL36_FIXED_PACKET_PAIRED_SOURCE_ACCEPTANCE_CONTRACT.json", 33356,
                   "272c62478698ff5bc213c44e8ad0724508451b1b45fc48f4193d87b208e7b7bc"),
    "adoption": (W / "ACTUAL_SOURCE_SYSTEM40_MAIN_ADOPTION.json", 2877,
                 "a27d4ee8cad68eb3e928560d447a4899105e2045f31d28a83be6e31ccc8309f3"),
    "anchor_adoption": (W / "ACTUAL_SOURCE_ANCHOR39_MAIN_ADOPTION.json", 1637,
                        "0b5b5f733b6bb2be2ccbaf9cf42b32eefbde46393791deeda6e10d0f175264d2"),
    "review": (W / "5703-source-anchor39-candidate/SOURCE_ANCHOR39_FROZEN_REVIEW.json", 6692,
               "977e6ebee9b425e21b38318b34a946dacf122e6595c15ecfb32796c85e1ef50b"),
    "controls": (W / "5703-source-anchor39-candidate/SOURCE_ANCHOR39_SMALL_FREE_CONTROLS.json", 8314,
                 "76a4902ecb136f5580c3b126c3a5cacee125eadb28dc7f75a21439b3fb265a04"),
    "instruction_review": (W / "5703-source-selection38-candidate/SOURCE_SELECTION38_FROZEN_REVIEW.json", 6341,
                           "97ef5d8962255531048f470c5e5f174fc433759d495947a878941b35dc8d0875"),
    "system_review": (W / "5703-source-system40-candidate/SOURCE_SYSTEM40_FROZEN_REVIEW.json", 5817,
                      "216b119c6740169d06963354fbf8f575c30d137225aaab5005134c1c2f549015"),
    "system_controls": (W / "5703-source-system40-candidate/SOURCE_SYSTEM40_SMALL_FREE_CONTROLS.json", 5981,
                        "d5d04370f185d102af654dc66b75eb9c3a1e33e98818d6939215e440dd8772b0"),
    "checked": (MAIN / "generation/checked.py", 155924,
                "838b641549631ee365f0f2e9b534c9f08aa0c230dfe59745f5de3ca901145a4c"),
    "source": (MAIN / "generation/source_relations_v2.py", 17079,
               "4e3ef844eff23b77d83e850c32fdfa47c9504b7cec9a8edd7db3328851ba5a55"),
    "prior_preparation40": (W / "5703-fixed-checker-pair40-candidate/OFFLINE_FIXED_CHECKER_PAIR40_PREPARATION01.json", 24434,
                            "3aa7b71fc0a8c5ab84eb9a1ad70d2bda348798ecb5d17461f4a8394b81e2eab0"),
    "native_schema_proof": (W / "5703-strict-schema41-candidate/STRICT_SCHEMA41_PURE_TRANSPORT_PROOF.json", 6181,
                            "d2f0005e499b980a73d8ec437d038609812a492a94481a958d1020dfabf4d1ca"),
    "native_schema_helper": (W / "5703-strict-schema41-candidate/strict_schema41_transport_contract.py", 4637,
                             "e014043e07d60a5711756b1090a4e1e02b4788e21e6b2a71fe06cc5a7588522d"),
    "full_native_schema": (W / "5703-strict-schema41-candidate/FULL_V2_CANONICAL_SCHEMA41.json", 7125,
                           "864212a5e636d2cadbc34328f431712a954c30130848a31e64e66e4bdedbc926"),
    "credential_helper": (D / "haiku_json_object_full_checker_probe_PREPARED08.py", 36687,
                          "b19fdfd53bfccb64e617a8203ed7947bc73ae2c2897a22908de7380dd5e29b6c"),
    "diagnostics": (D / "scientific-native-closure-preparation36/diagnostics01.py", 17258,
                    "e2f06c40dd0b703fd63bbd3248b436a79864290149ca515a4ac81d2822c3942b"),
}


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value, *, ascii=True):
    return json.dumps(value, ensure_ascii=ascii, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("ascii" if ascii else "utf-8")


def digest(value, *, ascii=True):
    return sha(canonical(value, ascii=ascii))


def require(condition, code):
    if not condition:
        raise ValueError(code)


def ordinary(value, root=W):
    path = Path(os.path.abspath(value))
    require(path.is_relative_to(root), "EXACT_PUBLIC_ROOT_REQUIRED")
    require(not any(p.casefold() in {".codex", ".agents", ".aws", ".secrets", "eval-private", "week09-private-db"}
                    for p in path.parts), "PROTECTED_INPUT_REFUSED")
    for item in (path, *path.parents):
        if item.exists():
            require(not getattr(item.stat(follow_symlinks=False), "st_file_attributes", 0) & 0x400,
                    "REPARSE_POINT_REFUSED")
        if item == root:
            break
    return path


def metadata(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": sha(raw)}


def read_tuple(pin):
    path, length, expected = pin
    path = ordinary(path, MAIN if Path(path).is_relative_to(MAIN) else W)
    info = path.stat(follow_symlinks=False)
    require(stat.S_ISREG(info.st_mode) and info.st_size <= 2_000_000, "BOUNDED_ORDINARY_INPUT_REQUIRED")
    raw = path.read_bytes()
    require(len(raw) == length and sha(raw) == expected, "FROZEN_INPUT_PIN_CHANGED")
    return raw


def read_json(pin):
    return json.loads(read_tuple(pin))


def load_source(name, pin):
    path = pin[0]
    module = types.ModuleType(name)
    module.__file__ = str(path)
    sys.modules[name] = module
    exec(compile(read_tuple(pin), str(path), "exec"), module.__dict__)
    return module


def install_public_implementation():
    # Omit only the package facade. Import real unchanged implementation modules.
    sys.dont_write_bytecode = True
    site = MAIN / ".venv/Lib/site-packages"
    require(site.is_dir(), "EXISTING_LOCAL_DEPENDENCIES_REQUIRED")
    if str(site) not in sys.path:
        sys.path.append(str(site))
    if str(MAIN) not in sys.path:
        sys.path.append(str(MAIN))
    package = types.ModuleType("generation")
    package.__path__ = [str(MAIN / "generation")]
    package.__package__ = "generation"
    sys.modules["generation"] = package


def sealed_source_relation_checker_system(trusted_instructions):
    # Execute only the pinned production pure function, avoiding service imports.
    path = PINS["checked"][0]
    tree = ast.parse(read_tuple(PINS["checked"]), filename=str(path))
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and
                 node.name == "source_relation_checker_system"]
    require(len(functions) == 1, "EXACT_PRODUCTION_SYSTEM_HELPER_REQUIRED")
    namespace = {"SOURCE_SELECTION_INSTRUCTIONS": trusted_instructions}
    pure = ast.Module(body=functions, type_ignores=[])
    exec(compile(pure, str(path), "exec"), namespace)
    return namespace["source_relation_checker_system"], digest(ast.dump(functions[0], include_attributes=False))


def validate_grouped_context_hints(entry, hints, by_cid, fragments, word_family):
    require(hints["candidate_only"] is True and hints["source_entailment_certified"] is False and
            hints["columns"] == ["kind", "anchor_text", "claim_occurrences", "source_hits"],
            "GROUPED_HINT_MUST_NOT_CERTIFY_SUPPORT")
    allowed = {r["evidence_id"]: set(r["allowed_fragment_ids"])
               for r in by_cid[entry["claim_id"]]["citations"]}
    units = {r["unit_id"]: r for r in entry["units"]}
    full_claim = entry["full_claim"]
    groups = set()
    occurrences = hits = source_spans = empty_groups = 0
    for kind, anchor, claim_occurrences, source_hits in hints["rows"]:
        require(isinstance(kind, str) and isinstance(anchor, str) and bool(anchor) and
                (kind, anchor) not in groups and bool(claim_occurrences), "EXACT_ANCHOR_GROUP_REQUIRED")
        groups.add((kind, anchor))
        empty_groups += not source_hits
        seen_occurrences = set()
        for uid, start, end in claim_occurrences:
            unit = units.get(uid)
            require(unit is not None and type(start) is int and type(end) is int and
                    unit["start"] <= start < end <= unit["end"] and
                    full_claim[start:end] == anchor and (uid, start, end) not in seen_occurrences,
                    "ANCHOR_UNIT_ORIGINAL_OFFSET_CHANGED")
            seen_occurrences.add((uid, start, end))
            occurrences += 1
        seen_hits = set()
        for eid, fid, spans in source_hits:
            fragment = fragments.get(fid)
            require(fragment is not None and fragment["evidence_id"] == eid and
                    fid in allowed.get(eid, set()) and fragment["complete_block"] and
                    fid not in seen_hits and bool(spans), "ANCHOR_SOURCE_OWNERSHIP_CHANGED")
            seen_hits.add(fid)
            source = fragment["exact_text"]
            seen_spans = set()
            for start, end, matching_rule in spans:
                require(type(start) is int and type(end) is int and 0 <= start < end <= len(source) and
                        (start, end, matching_rule) not in seen_spans,
                        "ANCHOR_SOURCE_ORIGINAL_OFFSET_CHANGED")
                selected = source[start:end]
                boundary = (start == 0 or not re.match(r"\w", source[start - 1])) and (
                    end == len(source) or not re.match(r"\w", source[end]))
                literal = matching_rule == "literal" and selected.casefold() == anchor.casefold()
                family = (matching_rule == "word_family_candidate" and kind == "predicate_term" and
                          selected.casefold() != anchor.casefold() and bool(word_family(anchor)) and
                          word_family(selected) == word_family(anchor))
                require(boundary and (literal or family), "DECLARED_ANCHOR_MATCH_RULE_CHANGED")
                seen_spans.add((start, end, matching_rule))
                source_spans += 1
            hits += 1
    return len(groups), occurrences, hits, source_spans, empty_groups


def prepare():
    install_public_implementation()
    from generation.types import ModelConfig
    from generation.providers import payload
    from generation.openrouter_routes import prepare_schema_wire
    from generation.checker_encoding import decode, encode, dumps
    from generation.source_relations_v2 import ReliableUnitCheck, scoped_syntactic_units, SOURCE_SELECTION_INSTRUCTIONS, _context_word_family
    from generation.reliability_v4 import compact_schema

    initial = read_json(PINS["initial"])["check_data"]
    final = read_json(PINS["final"])["check_data"]
    acceptance = read_json(PINS["acceptance"])
    adoption = read_json(PINS["adoption"])
    anchor_adoption = read_json(PINS["anchor_adoption"])
    review = read_json(PINS["review"])
    controls = read_json(PINS["controls"])
    instruction_review = read_json(PINS["instruction_review"])
    system_review = read_json(PINS["system_review"])
    system_controls = read_json(PINS["system_controls"])
    read_tuple(PINS["checked"])
    read_tuple(PINS["source"])
    require(adoption["output_schema_parser_assessor_gates_default_policy_changed"] is False and
            adoption["whole_other_business_ast_unchanged"] is True and
            anchor_adoption["discovery_rules_changed"] is False, "UNCHANGED_GATES_AND_DISCOVERY_RULES_REQUIRED")
    require(review["small_controls_passed"] == controls["small_controls_passed"] == 22 and
            len(controls["controls"]) == 22 and all(row["passed"] is True for row in controls["controls"]) and
            review["output_schema_parser_assessor_gates_default_policy_changed"] is False and
            review["schema_compact_sha256"] == SCHEMA_SHA and
            review["every_anchor_claim_and_source_offset_owned_and_exact"] is True and
            review["duplicate_anchor_across_units_grouped"] is True and
            review["original_discovery_rules_all_other_AST_nodes_unchanged"] is True and
            bool(review["specific_group_alignment_proof"]),
            "REVIEWED_BUSINESS_DELTA_REQUIRED")
    require(instruction_review["all_noninstruction_AST_nodes_unchanged"] is True and
            instruction_review["fresh_affected_controls_passed"] == 6 and
            len(instruction_review["fresh_affected_controls"]) == 6 and
            all(row["passed"] is True for row in instruction_review["fresh_affected_controls"]) and
            instruction_review["schema_compact_sha256"] == SCHEMA_SHA and
            instruction_review["schema_parser_assessor_gates_defaults_changed"] is False,
            "RETAINED_GENERIC_INSTRUCTION38_PROOF_REQUIRED")
    require(system_review["small_controls_passed"] == 15 and
            len(system_controls["controls"]) == 15 and all(row["passed"] is True for row in system_controls["controls"]) and
            system_review["compact_schema_sha256"] == SCHEMA_SHA and
            system_review["output_schema_parser_assessor_gates_default_policy_changed"] is False and
            system_review["whole_other_business_ast_unchanged"] is True and
            system_review["question_claim_fragment_hardcoding"] is False,
            "REVIEWED_PRODUCTION_SYSTEM40_DELTA_REQUIRED")
    for receipt in (adoption, anchor_adoption):
        for row in receipt["files"]:
            after = row["after"]
            read_tuple((Path(row["path"]), after["bytes"], after["sha256"]))
    require(digest(initial) == ORIGINAL_DATA_SHA == acceptance["fixed_initial_packet"]["whole_check_data_canonical_sha256"],
            "ORIGINAL_INITIAL_PACKET_CHANGED")
    for field, expected in acceptance["fixed_initial_packet"]["frozen_field_hashes"].items():
        require(digest(initial[field]) == expected, "INITIAL_FIELD_HASH_CHANGED")
    original = decode(initial)
    require(encode(original) == initial, "ORIGINAL_LOSSLESS_ROUND_TRIP_FAILED")
    require(len(original["CLAIMS"]) == 10 and len(original["SOURCE_FRAGMENTS"]) == 71 and
            sum(len(row["units"]) for row in original["SOURCE_SYNTACTIC_UNITS"]) == 19,
            "FIXED_10_19_71_REQUIRED")
    candidate = deepcopy(initial)
    candidate["SOURCE_SYNTACTIC_UNITS"] = scoped_syntactic_units(
        original["CLAIMS"], original["ACTUAL_CITATION_BINDINGS"], original["SOURCE_FRAGMENTS"])
    candidate.pop("SOURCE_RELATION_SELECTION_INSTRUCTIONS")
    projected = deepcopy(candidate)
    hint_rows = hint_occurrences = hint_source_hits = hint_source_spans = hint_empty_groups = 0
    by_cid = {r["claim_id"]: r for r in original["ACTUAL_CITATION_BINDINGS"]}
    fragments = {r["fragment_id"]: r for r in original["SOURCE_FRAGMENTS"]}
    for entry in projected["SOURCE_SYNTACTIC_UNITS"]:
        hints = entry.pop("source_context_candidates")
        groups, occurrences, hits, spans, empty_groups = validate_grouped_context_hints(
            entry, hints, by_cid, fragments, _context_word_family)
        hint_rows += groups
        hint_occurrences += occurrences
        hint_source_hits += hits
        hint_source_spans += spans
        hint_empty_groups += empty_groups
    projected["SOURCE_RELATION_SELECTION_INSTRUCTIONS"] = initial["SOURCE_RELATION_SELECTION_INSTRUCTIONS"]
    require(projected == initial and digest(projected) == ORIGINAL_DATA_SHA, "EXACT_HINT_REMOVAL_PROJECTION_FAILED")
    measured = review["payload_measurement"]
    require((hint_rows, hint_occurrences, hint_source_hits, hint_source_spans, hint_empty_groups) ==
            tuple(measured[key] for key in ("anchor_group_rows", "claim_occurrences", "source_hits", "source_spans", "empty_lookup_groups")),
            "REVIEWED_GROUPED_ANCHOR_COUNTS_CHANGED")
    require(decode(candidate)["CLAIMS"] == original["CLAIMS"] and
            candidate["SOURCE_FRAGMENTS"] == initial["SOURCE_FRAGMENTS"], "ORIGINAL_CLAIMS_OR_SOURCES_CHANGED")
    schema = compact_schema(ReliableUnitCheck)
    require(digest(schema, ascii=False) == SCHEMA_SHA, "EXACT_V2_SCHEMA_CHANGED")
    prompt_names = ("joint_check_v5.txt", "checker_contract_v3.txt", "claim_patch_checker_v1.txt", "source_relation_check_v2.txt")
    prompt_root = MAIN / "generation/prompts"
    system = "\n".join((prompt_root / n).read_text(encoding="utf-8") for n in prompt_names)
    old_check = read_json(PINS["outcome"])["checks"][0]
    require(sha(system.encode()) == old_check["rubric_hash"], "ACTUAL_INITIAL_RUBRIC_CHANGED")
    renderer, helper_ast_sha = sealed_source_relation_checker_system(SOURCE_SELECTION_INSTRUCTIONS)
    candidate_system = renderer(system)
    require(candidate_system == system + "\n" + SOURCE_SELECTION_INSTRUCTIONS +
            system_review["production_renderer"]["final_schema_audit"], "EXACT_TRUSTED_SYSTEM_DELIVERY_CHANGED")
    cfg = ModelConfig(provider="openai_compatible", model="google/gemini-3.5-flash-lite",
                      base_url="https://openrouter.ai/api/v1", window_tokens=131072, max_tokens=4096,
                      timeout_seconds=60.0, temperature=None, structured_output_mode="json_object",
                      reasoning_effort=None, configuration_id="model-settings:74c8201e-aca0-400d-bcc5-5785e24c1c11",
                      openrouter_route_profile="gemini35_google_vertex_v1")
    cfg.validate()
    reference_plans = []
    for arm, data, check_system in zip(("baseline40", "candidate40"), (initial, candidate), (system, candidate_system), strict=True):
        messages = [{"role": "system", "content": check_system}, {"role": "user", "content": dumps(data)}]
        body, transport = prepare_schema_wire(cfg, payload(cfg, messages, schema, SCHEMA_NAME), schema)
        require(transport == {} and body["response_format"] == {"type": "json_object"}, "ORIGINAL_SCHEMA_HINT_WIRE_REQUIRED")
        wire = json.dumps(body, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
        controls = {k: v for k, v in body.items() if k != "messages"}
        bound = (Decimal(len(wire) + 512) * Decimal("0.3") + Decimal(OUTPUT) * Decimal("2.5")) / Decimal(1000000)
        require(len(wire) <= MAX_WIRE and len(wire) + 512 < 100000 and len(wire) + 512 + OUTPUT <= cfg.window_tokens
                and bound < PER - Decimal("0.0005"), "UNIFORM_WIRE_FINANCIAL_TIER_WINDOW_LIMIT")
        reference_plans.append({"arm": arm, "messages": messages, "data": data, "body": body,
                      "wire_bytes": len(wire), "wire_sha256": sha(wire),
                      "canonical_complete_payload_sha256": digest(body, ascii=False),
                      "messages_sha256": digest(body["messages"], ascii=False),
                      "wire_controls_sha256": digest(controls, ascii=False),
                      "schema_sha256": SCHEMA_SHA, "strict_cost_bound_USD": str(bound)})
    baseline = reference_plans[0]
    require(baseline["wire_bytes"] == 68490 and baseline["wire_sha256"] == ORIGINAL_BODY_SHA and
            baseline["canonical_complete_payload_sha256"] == ORIGINAL_CANONICAL_BODY_SHA and
            baseline["messages_sha256"] == ORIGINAL_MESSAGES_SHA and
            baseline["wire_controls_sha256"] == ORIGINAL_CONTROLS_SHA, "ACTUAL36_INITIAL_WIRE_RECONSTRUCTION_FAILED")
    require(reference_plans[0]["wire_controls_sha256"] == reference_plans[1]["wire_controls_sha256"], "OFFLINE_REFERENCE_CONTROLS_DIFFERED")
    prior_preparation = read_json(PINS["prior_preparation40"])
    reference_keys = ("wire_bytes", "wire_sha256", "canonical_complete_payload_sha256", "messages_sha256", "wire_controls_sha256", "schema_sha256")
    require(all(actual[key] == expected[key] for actual, expected in
                zip(reference_plans, prior_preparation["plans"], strict=True) for key in reference_keys),
            "CLOSED40_REFERENCE_RECONSTRUCTION_CHANGED")
    native_proof = read_json(PINS["native_schema_proof"])
    require(native_proof["canonical_original_full_schema_sha256"] == SCHEMA_SHA and
            native_proof["provider_schema_exactly_canonical"] is True and
            native_proof["wire_projection_policy"] is None and
            native_proof["observed_live_endpoint_schema_support"] is False and
            read_json(PINS["full_native_schema"]) == schema, "FULL_UNPROJECTED_NATIVE_SCHEMA_REQUIRED")
    native_helper = load_source("root_pure_native_schema41_transport", PINS["native_schema_helper"])
    cfg41, body41, native_certificate = native_helper.prepare_full_native_schema41(
        cfg, reference_plans[1]["messages"], schema)
    old_config, new_config = cfg.to_dict(), cfg41.to_dict()
    config_delta = {key: [old_config[key], new_config[key]] for key in old_config
                    if old_config[key] != new_config[key]}
    require(config_delta == {"structured_output_mode": ["json_object", "json_schema"]}, "MODE_ONLY_CONFIG_DELTA_REQUIRED")
    require(body41["response_format"] == {"type": "json_schema", "json_schema": {
        "name": SCHEMA_NAME, "strict": True, "schema": schema}}, "EXACT_FULL_NATIVE_RESPONSE_FORMAT_REQUIRED")
    wire41 = json.dumps(body41, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
    bound41 = (Decimal(len(wire41) + 512) * Decimal("0.3") + Decimal(OUTPUT) * Decimal("2.5")) / Decimal(1000000)
    require(len(wire41) <= MAX_WIRE and len(wire41) + 512 < 100000 and
            len(wire41) + 512 + OUTPUT <= cfg41.window_tokens and bound41 < PER - Decimal("0.0005"),
            "NATIVE41_WIRE_FINANCIAL_TIER_WINDOW_LIMIT")
    controls41 = {key: value for key, value in body41.items() if key != "messages"}
    plans = [{"arm": ARMS[0], "messages": reference_plans[1]["messages"], "data": candidate, "body": body41,
              "wire_bytes": len(wire41), "wire_sha256": sha(wire41),
              "canonical_complete_payload_sha256": digest(body41, ascii=False),
              "messages_sha256": digest(body41["messages"], ascii=False),
              "wire_controls_sha256": digest(controls41, ascii=False),
              "schema_sha256": SCHEMA_SHA, "strict_cost_bound_USD": str(bound41)}]
    require(len(plans) == len(ARMS) == 1 and PRIOR_COST + TOTAL <= GROUP_LIMIT, "EXACT_ONE_POST_DIAGNOSTIC_REQUIRED")
    cfg = cfg41
    retained_observation = validate_output(read_json(PINS["initial"])["raw"]["retained_raw_text"], original)
    require(retained_observation["schema_PASS"], "RETAINED_ORIGINAL_V2_SCHEMA_REPLAY_FAILED")
    module_pins = []
    for name, module in sorted(sys.modules.items()):
        path = getattr(module, "__file__", None)
        if path and Path(path).is_relative_to(MAIN) and Path(path).suffix == ".py":
            module_pins.append(metadata(Path(path)))
    for name in prompt_names:
        module_pins.append(metadata(prompt_root / name))
    summary = {"schema": "5703_fixed_initial_checker_native_schema41_preparation_v1", "status": "OFFLINE_PREPARED_NO_API_OR_CREDENTIAL_ACCESS",
               "runner_pin": metadata(Path(__file__)), "input_pins": {k: {"path": str(v[0]), "bytes": v[1], "sha256": v[2]} for k, v in PINS.items()},
               "main_source_and_prompt_pins": module_pins, "configuration": cfg.to_dict(),
               "fixed_initial_claims": 10, "fixed_initial_units": 19, "fixed_source_fragments": 71,
               "original_initial_packet_sha256": ORIGINAL_DATA_SHA, "candidate_projection_sha256": digest(projected),
               "declared_changed_fields": ["SOURCE_SYNTACTIC_UNITS[*].source_context_candidates", "SOURCE_RELATION_SELECTION_INSTRUCTIONS removed from candidate DATA", "SYSTEM content via generation.checked.source_relation_checker_system"],
               "new_diagnostic_delta_from_candidate40": "structured_output_mode only: automatic textual schema hint replaced with identical full native response_format schema",
               "config_delta_from_candidate40": config_delta,
               "native_schema_transport_certificate": native_certificate,
               "offline_json_object_reference_plans_not_called": [{k: v for k, v in p.items() if k not in {"messages", "data", "body"}} for p in reference_plans],
               "matched_pair": False,
               "baseline_requests_this_scope": 0,
               "upstream_full_keyword_enforcement_observed": False,
               "source_system40_fresh_controls_passed": 15,
               "production_system_helper_ast_sha256": helper_ast_sha,
               "candidate_system_template_sha256": sha(candidate_system.encode()),
               "candidate_SYSTEM_contains_only_original_rubric_and_trusted_rules": True,
               "context_hint_rows": hint_rows, "accepted_rewrite_packet_separately_retained": True,
               "context_hint_claim_occurrences": hint_occurrences,
               "context_hint_source_hits": hint_source_hits,
               "context_hint_source_spans": hint_source_spans,
               "context_hint_empty_lookup_groups": hint_empty_groups,
               "empty_lookup_does_not_certify_semantic_absence": True,
               "source_anchor39_fresh_controls_passed": 22,
               "generic_instruction38_controls_retained_not_rerun": 6,
               "frozen_group_alignment_lookup_proof_not_semantic_certificate": review["specific_group_alignment_proof"],
               "retained_initial_model_schema_PASS": retained_observation["schema_PASS"],
               "retained_initial_scope_repair_triggered": retained_observation["scope_repair_triggered"],
               "retained_initial_technical_entity_binding_issues": retained_observation["technical_entity_binding_issues"],
               "accepted_rewrite_packet_not_a_pair_arm": True, "accepted_rewrite_packet_sha256": digest(final),
               "plans": [{k: v for k, v in p.items() if k not in {"messages", "data", "body"}} for p in plans],
               "new_manual_POST_limit": 1, "new_manual_reserve_USD": str(TOTAL), "per_POST_reserve_USD": str(PER),
               "prior_closed_group_POSTs": 20, "prior_known_group_cost_USD": str(PRIOR_COST),
               "maximum_cumulative_manual_POSTs": 21, "maximum_known_group_plus_new_reserve_USD": str(PRIOR_COST + TOTAL),
               "original_money_limit_USD": str(GROUP_LIMIT), "historical_unknown_holds_release_authorized": False,
               "old_scope_reuse": False, "automatic_retries": False, "teacher_calls": 0,
               "JSON_repairs": 0, "native_or_course_qualification": False,
               "API_calls": 0, "credential_preparation_calls": 0, "database_accesses": 0}
    return cfg, schema, original, plans, summary


def save_new(path, value, redactor=None):
    ordinary(path, HERE)
    value = redactor.value(value) if redactor else value
    raw = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode() + b"\n"
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return metadata(path)


def validate_output(raw, original):
    from generation.parser import strict_json
    from generation.source_relations_v2 import ReliableUnitCheck, assess_source_relations
    from generation.reliability_v4 import normalize_judgment, checker_inconsistencies, repairable_verdict_inconsistencies
    from generation.reliability_v5 import evaluate_technical_entity_bindings
    result = {"schema_PASS": False, "local_binding_and_relation_contract_PASS": False,
              "independent_source_entailment_certified": False, "native_publication": False}
    try:
        typed = ReliableUnitCheck.model_validate(strict_json(raw)).model_dump()
    except (ValueError, TypeError) as exc:
        result["schema_error_class"] = type(exc).__name__
        return result
    result["schema_PASS"] = True
    expected = [c["claim_id"] for c in original["CLAIMS"]]
    returned = [c["claim_id"] for c in typed["claims"]]
    identity_ok = len(returned) == len(expected) and len(set(returned)) == len(returned) and set(returned) == set(expected)
    normalized, issues = normalize_judgment(typed, original["ACTUAL_CITATION_BINDINGS"])
    contract, defects, assessment = assess_source_relations(typed, original["CLAIMS"],
                                                          original["ACTUAL_CITATION_BINDINGS"], original["SOURCE_FRAGMENTS"])
    coherence = checker_inconsistencies(normalized, answer_mode=original["answer_mode"], bindings=original["ACTUAL_CITATION_BINDINGS"])
    optimism = repairable_verdict_inconsistencies(normalized)
    entity_issues = evaluate_technical_entity_bindings(
        typed, original["CLAIMS"], original["ACTUAL_CITATION_BINDINGS"], original["SOURCE_FRAGMENTS"])
    result.update(exact_claim_identity_PASS=identity_ok, binding_issues=issues, source_contract_issues=contract,
                  source_semantic_defects=defects, model_relation_assessment=assessment,
                  checker_inconsistencies=coherence, repairable_verdict_inconsistencies=optimism,
                  technical_entity_binding_issues=entity_issues,
                  scope_repair_triggered=bool(entity_issues),
                  typed_judgment=typed,
                  local_binding_and_relation_contract_PASS=identity_ok and not issues and not contract and not coherence,
                  model_all_units_supported_without_local_contract_errors=identity_ok and not issues and not contract and not defects and not coherence and not optimism,
                  acceptance_contract_observer_review_pending=True,
                  all_product_publication_gates_replayed=False)
    return result


def execute(review_path, review_sha, out):
    # No credential is read until every frozen public input and planned wire passes.
    cfg, schema, original, plans, prepared = prepare()
    prior_review = read_json((ordinary(review_path, HERE), Path(review_path).stat().st_size, review_sha))
    require(prior_review == prepared, "ROOT_REVIEWED_PREPARATION_CHANGED")
    require(PRIOR_COST + TOTAL <= GROUP_LIMIT, "ORIGINAL_MONEY_LIMIT_EXCEEDED")
    out = ordinary(out, HERE)
    require(not out.exists(), "FRESH_WRITE_ONCE_SCOPE_REQUIRED")
    out.mkdir()
    report = {"schema": "5703_fixed_initial_checker_native_schema41_actual_v1", "started_at_UTC": now(),
              "status": "STARTED", "source_review_pin": metadata(Path(review_path)), "physical_POSTs": 0,
              "known_cost_USD": "0", "new_UNKNOWN_holds_USD": "0", "open_claims": 0,
              "credential_preparation_read_only_DB_legs": 0, "experiment_DB_accesses": 0,
              "credential_target_database": SOLE_DB, "arms": [], "automatic_retries": 0,
              "teacher_calls": 0, "JSON_repairs": 0, "old_scope_reuse": False,
              "historical_unknown_holds_released": False, "fresh_question_or_course_qualification": False}
    save_new(out / "intent01.json", report)
    helper = load_source("root_original_approved_credential41", PINS["credential_helper"])
    require(helper.TARGET_DB == SOLE_DB, "ORIGINAL_CREDENTIAL_HELPER_DATABASE_OUTSIDE_SOLE_SCOPE")
    for path in (MAIN, MAIN / "backend"):
        if str(path) not in sys.path:
            sys.path.append(str(path))
    os.environ.update(PYTHONDONTWRITEBYTECODE="1", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
    report["credential_preparation_read_only_DB_legs"] = 1
    key = helper.approved_credential(helper.WORKSPACE_ID)
    require(isinstance(key, str) and key, "APPROVED_CREDENTIAL_UNAVAILABLE")
    diagnostics = load_source("root_original_diagnostics41", PINS["diagnostics"])
    redactor = diagnostics.Redactor((key,))
    from generation import adapters as adapter_module
    from generation.adapters import LLMAdapter
    from generation.providers import endpoint
    require(endpoint(cfg) == URL, "EXACT_OPENROUTER_ENDPOINT_REQUIRED")
    adapter = LLMAdapter(cfg, api_key=key, retain_invalid_output=True)
    key = None
    original_open, original_pin = adapter_module.open_provider, adapter_module.pinned_address
    active = None
    stopped = False
    known, unknown = Decimal("0"), Decimal("0")
    lock = (out / "fresh-pair-budget.lock").open("xb+")
    lock.write(b"0"); lock.flush(); lock.seek(0)
    import msvcrt
    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)

    def recheck():
        for pin in prepared["main_source_and_prompt_pins"]:
            read_tuple((Path(pin["path"]), pin["bytes"], pin["sha256"]))
        for pin in PINS.values():
            read_tuple(pin)

    def pin_guard(url):
        require(active is not None and active["submitted"] and active["resolving"] is False and url == URL,
                "ACTIVE_EXACT_PROVIDER_RESOLUTION_REQUIRED")
        active["resolving"] = True
        try:
            selected = original_pin(url)
        finally:
            active["resolving"] = False
        address = ipaddress.ip_address(selected)
        require(address.is_global and not (isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped),
                "ORIGINAL_PROVIDER_PUBLIC_IP_REQUIRED")
        active["pinned_ip"] = str(address)
        return selected

    def open_guard(envelope, timeout):
        nonlocal stopped
        require(active is not None and not active["submitted"] and not stopped, "ONE_EXACT_ARM_POST_REQUIRED")
        recheck()
        plan = active["plan"]
        require(envelope.full_url == URL and envelope.get_method() == "POST" and isinstance(envelope.data, bytes),
                "EXACT_PROVIDER_POST_REQUIRED")
        require(len(envelope.data) == plan["wire_bytes"] and sha(envelope.data) == plan["wire_sha256"] and
                json.loads(envelope.data) == plan["body"], "ACTUAL_WIRE_DIFFERED_FROM_REVIEW")
        require(report["physical_POSTs"] < 2 and known + unknown + PER <= TOTAL, "FINITE_PAIR_BUDGET_CLOSED")
        active["submitted"] = True
        report["physical_POSTs"] += 1
        report["open_claims"] += 1
        save_new(out / (plan["arm"] + "-POST_STARTED_UNKNOWN01.json"),
                 {"at_UTC": now(), "arm": plan["arm"], "reserve_USD": str(PER), "wire_sha256": plan["wire_sha256"],
                  "wire_bytes": plan["wire_bytes"], "request_headers_exported": False})
        def retained(pin):
            active["raw_receipts"].append(pin)
        try:
            return diagnostics.wrap_provider_response(original_open(envelope, timeout=timeout),
                        path_prefix=out / (plan["arm"] + "-raw-provider"), redactor=redactor, on_saved=retained)
        except urlerror.HTTPError as exc:
            diagnostics.retain_http_error_reads(exc, path_prefix=out / (plan["arm"] + "-raw-provider"),
                                               redactor=redactor, on_saved=retained)
            raise

    def audit(event, values):
        if event in {"subprocess.Popen", "os.system", "os.exec", "os.spawn", "socket.bind", "socket.sendto"}:
            raise PermissionError("COMPONENT_FORBIDDEN_OPERATION")
        if event == "socket.getaddrinfo":
            require(active is not None and active["submitted"] and len(values) > 1 and values[1] == 443 and
                    (active["resolving"] and values[0] == "openrouter.ai" or values[0] == active["pinned_ip"]),
                    "ONLY_EXACT_PROVIDER_DNS_ALLOWED")
        if event == "socket.connect":
            address = values[1]
            require(active is not None and isinstance(address, tuple) and len(address) >= 2 and
                    address[0] == active["pinned_ip"] and address[1] == 443, "ONLY_PINNED_PROVIDER_CONNECT_ALLOWED")
        if event == "open" and values and not isinstance(values[0], int):
            flags = values[2] if len(values) > 2 else 0
            mode = values[1] if len(values) > 1 else "r"
            write = isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
            write = write or isinstance(mode, str) and any(c in mode for c in "wax+")
            if write:
                require(Path(os.path.abspath(os.fsdecode(values[0]))).parent == out, "ONLY_FRESH_COMPONENT_OUTPUT_WRITES_ALLOWED")
    adapter_module.pinned_address, adapter_module.open_provider = pin_guard, open_guard
    sys.addaudithook(audit)
    try:
        for plan in plans:
            if stopped:
                report["arms"].append({"arm": plan["arm"], "status": "NOT_RUN_GLOBAL_STOP"})
                continue
            active = {"plan": plan, "submitted": False, "resolving": False, "pinned_ip": None, "raw_receipts": []}
            save_new(out / (plan["arm"] + "-actual-planned-wire01.json"),
                     {"payload": plan["body"], "check_data": plan["data"], "schema": schema,
                      "schema_name": SCHEMA_NAME, "headers_exported": False}, redactor)
            began = time.perf_counter_ns()
            result = adapter.generate(plan["messages"], response_schema=schema, response_schema_name=SCHEMA_NAME,
                                      request_context={"purpose": "joint_check", "request_id": "fixed-initial-native-schema41-" + plan["arm"]},
                                      timeout_seconds=cfg.timeout_seconds)
            elapsed = (time.perf_counter_ns() - began) / 1_000_000
            submitted = active["submitted"]
            value = result.usage.get("cost") if isinstance(result.usage, dict) else None
            valid_cost = type(value) in {int, float} and math.isfinite(value) and value >= 0
            cost = Decimal(str(value)) if valid_cost else None
            route_mismatch = bool(result.error and result.error.get("code") == "PROVIDER_ROUTE_MODEL_MISMATCH")
            if submitted:
                report["open_claims"] -= 1
                if cost is None or cost > PER or route_mismatch:
                    unknown += PER; stopped = True
                else:
                    known += cost
            if result.error:
                result.error["retryable"] = False
            validation = validate_output(result.raw_text, original) if result.raw_text else {"schema_PASS": False, "raw_text_available": False}
            row = {"arm": plan["arm"], "status": "OBSERVED" if submitted else "LOCAL_CONFIGURATION_STOP",
                   "physical_POSTs": int(submitted), "known_cost_USD": str(cost) if submitted and valid_cost and not route_mismatch else None,
                   "reported_cost_USD": str(cost) if valid_cost else None,
                   "fully_settled": submitted and cost is not None and cost <= PER and not route_mismatch,
                   "latency_ms": elapsed, "timing_boundary": "LLMAdapter.generate invocation to complete return",
                   "provider_result": asdict(result), "raw_receipt_pins": active["raw_receipts"], "validation": validation}
            save_new(out / (plan["arm"] + "-POST_FINISHED01.json"), row, redactor)
            report["arms"].append(row)
            if not submitted or route_mismatch or result.error and result.error.get("details", {}).get("uncertain"):
                stopped = True
            active = None
        report.update(status="PAIRED_OBSERVATIONS_CLOSED" if report["physical_POSTs"] == 2 and not stopped else "STOPPED_RETAINED",
                      known_cost_USD=str(known), new_UNKNOWN_holds_USD=str(unknown),
                      cumulative_known_group_cost_USD=str(PRIOR_COST + known),
                      fully_settled=unknown == 0 and report["open_claims"] == 0,
                      independent_selected_source_quality_review_pending=True)
    except BaseException as exc:
        if active is not None and active["submitted"] and report["open_claims"]:
            report["open_claims"] = 0; unknown += PER
        report.update(status="STOPPED_RETAINED", error_class=type(exc).__name__, known_cost_USD=str(known),
                      new_UNKNOWN_holds_USD=str(unknown), fully_settled=False)
    finally:
        active = None
        adapter._api_key = None
        adapter_module.pinned_address, adapter_module.open_provider = original_pin, original_open
        lock.seek(0); msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1); lock.close()
        report.update(closed_at_UTC=now(), adapter_credential_reference_cleared=True,
                      credential_values_exported=False, memory_redaction_retained_until_process_exit=True,
                      fresh_lock_released=True,
                      historical_unknown_holds_released=False, no_followup_requests_authorized=True)
        save_new(out / "STOP-before-any-next-submission01.json", {"schema": "fixed_native_schema41_terminal_stop_v1", "status": report["status"], "at_UTC": now()})
        final_pin = save_new(out / "actual-checker-native-schema41-result01.json", report, redactor)
    print(json.dumps({"status": report["status"], "physical_POSTs": report["physical_POSTs"],
                      "known_cost_USD": report["known_cost_USD"], "result_pin": final_pin}))
    return 0 if report["status"] == "PAIRED_OBSERVATIONS_CLOSED" else 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-output", type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--review", type=Path)
    parser.add_argument("--review-sha256")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.execute:
        require(args.review is not None and args.review_sha256 is not None and args.output is not None,
                "EXACT_ROOT_REVIEW_AND_FRESH_OUTPUT_REQUIRED")
        return execute(args.review, args.review_sha256, args.output)
    require(args.prepare_output is not None, "EXACT_W_PREPARATION_OUTPUT_REQUIRED")
    _, _, _, _, prepared = prepare()
    pin = save_new(args.prepare_output, prepared)
    print(json.dumps({"status": prepared["status"], "review_pin": pin}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
