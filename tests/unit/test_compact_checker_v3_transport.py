"""Portable offline regressions for the explicit compact checker v3 transport.

All input/source data below are authored synthetic physics fixtures. Expected
judgments are test responses, never supplied as facts in the checker context.
These tests use no credentials, external fixtures, database, HTTP or file paths.
The decoder preserves judgments; the original science validators decide release.
"""

from copy import deepcopy
import hashlib
import json
import re

import pytest
from pydantic import ValidationError

from generation import compact_findings_v3 as core
from generation.reliability_v4 import (
    checker_inconsistencies,
    compact_schema,
    given_matches,
    normalize_judgment,
    validate_derivation,
)
from generation.reliability_v5 import ReliableCheckV5, assess_requirements


SOURCE = (
    "Distance equals speed multiplied by elapsed time: distance = speed * time. 螖x = v 脳 螖t."
)
GIVENS = "Speed is 3 m/s and elapsed time is 4 s."
CLAIM_IDS = ["fixture_formula_claim", "fixture_given_claim", "fixture_result_claim"]
REQUIREMENT_ID = "fixture_distance_requirement"


def specimen():
    texts = [SOURCE + " [ev_001]", GIVENS, "The distance is 12 m. [ev_001]"]
    body, cursor, rows = "\n".join(texts), 0, []
    for index, (claim_id, text) in enumerate(zip(CLAIM_IDS, texts, strict=True)):
        rows.append(
            [
                "answer_text",
                claim_id,
                cursor + len(text),
                [] if index == 1 else ["ev_001"],
                cursor,
                text,
            ]
        )
        cursor += len(text) + 1

    def table(columns, data):
        return {"columns": columns, "rows": data}

    context = {
        "question": "Calculate distance from the given speed and elapsed time.",
        "current_problem": GIVENS,
        "answer_mode": "textbook",
        "POLICY": {
            "version": "learning_enhancement_v1",
            "teaching_mode": "direct",
            "online_check": True,
            "check_cumulative": False,
            "check_suggestions": False,
            "control_evidence": False,
        },
        "LEARNER_TURN": None,
        "ATTEMPT_EVALUATION": None,
        "TUTOR_QUESTION": None,
        "PRIOR_EXPOSURE": {"disabled": True},
        "CLAIMS": table(
            ["answer_field", "claim_id", "end", "evidence_ids", "start", "text"],
            rows,
        ),
        "ACTUAL_CITATION_BINDINGS": table(
            ["binding_ids", "claim_id"],
            [[["B001"], CLAIM_IDS[0]], [[], CLAIM_IDS[1]], [["B001"], CLAIM_IDS[2]]],
        ),
        "BINDING_BANK": table(
            ["allowed_fragment_ids", "binding_id", "evidence_id"],
            [[["F001"], "B001", "ev_001"]],
        ),
        "SOURCE_FRAGMENTS": table(
            ["block_kind", "complete_block", "evidence_id", "exact_text", "fragment_id"],
            [["prose", True, "ev_001", SOURCE, "F001"]],
        ),
        "CONTEXT_COVERAGE": {
            "requirements": [
                {
                    "id": REQUIREMENT_ID,
                    "text": "calculate distance from the given speed and elapsed time",
                }
            ]
        },
        "CHECK_SCOPE": {
            "body_and_short_answer": True,
            "current_suggestions": False,
            "current_evidence_display": False,
            "prior_actual_exposure": False,
        },
        "PROPOSED_DELIVERY": {
            "response": {
                "schema_version": "chat_response_v1",
                "response_type": "answer",
                "answer_text": body,
                "short_answer": None,
                "citations": ["ev_001"],
                "refusal_reason": None,
                "follow_up_questions": [],
                "confidence": 0.5,
            }
        },
    }
    proof = {
        "formula_basis": "textbook",
        "formula_fragment_id": "F001",
        "formula_quote": SOURCE,
        "expression": "speed * time",
        "inputs": [
            {
                "name": "speed",
                "value": "3",
                "unit": "m/s",
                "quote": "Speed is 3 m/s",
                "origin": "problem_input",
                "fragment_id": None,
            },
            {
                "name": "time",
                "value": "4",
                "unit": "s",
                "quote": "elapsed time is 4 s",
                "origin": "problem_input",
                "fragment_id": None,
            },
        ],
        "result": "12",
        "result_quote": "12 m",
        "result_unit": "m",
        "units_consistent": True,
        "formula_applicable": True,
    }
    citation = {"evidence_id": "ev_001", "fragment_ids": ["F001"], "relation": "supporting"}
    judged = {
        "claims": [
            {
                "claim_id": CLAIM_IDS[0],
                "basis": "textbook",
                "status": "supported",
                "citations": [deepcopy(citation)],
                "reason": "The source supplies the formula.",
            },
            {
                "claim_id": CLAIM_IDS[1],
                "basis": "problem_input",
                "status": "supported",
                "problem_quote": GIVENS,
                "reason": "These are the exact problem givens.",
            },
            {
                "claim_id": CLAIM_IDS[2],
                "basis": "derived_calculation",
                "status": "supported",
                "citations": [deepcopy(citation)],
                "derivation": proof,
                "reason": "Multiplying the quoted speed and time gives 12 m.",
            },
        ],
        **{flag: True for flag in core.FLAG_NAMES},
        "coverage": "full",
        "missing_facets": [],
        "repair_fragment_ids": [],
        "reason": "Authored offline response fixture, not an independent scientific rating.",
        "requirements": [
            {
                "requirement_id": REQUIREMENT_ID,
                "relevance": "related",
                "sufficiency": "sufficient",
                "conditions_preserved": True,
                "response_coverage": "covered",
                "missing_information": "",
                "evidence": [{"evidence_id": "ev_001", "fragment_id": "F001", "quote": SOURCE}],
                "reason": "The exact source formula and problem givens establish the result.",
            }
        ],
    }
    messages = [
        {"role": "system", "content": "Assess every original full V5 judgment independently."},
        {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
    ]
    prepared = core.prepare(messages, compact_schema(ReliableCheckV5))
    compact = core.compact_from_v5(judged, prepared.context)
    return messages, context, judged, prepared, compact


def original_views(full, context):
    fragments = [
        {
            "fragment_id": "F001",
            "evidence_id": "ev_001",
            "exact_text": SOURCE,
            "complete_block": True,
            "block_kind": "prose",
        }
    ]
    bindings = [
        {
            "claim_id": claim_id,
            "citations": []
            if index == 1
            else [
                {
                    "evidence_id": "ev_001",
                    "allowed_fragment_ids": ["F001"],
                }
            ],
        }
        for index, claim_id in enumerate(CLAIM_IDS)
    ]
    normalized, issues = normalize_judgment(full, bindings)
    return normalized, issues, fragments, bindings


def test_short_wire_ids_restore_exact_full_original_judgment_and_source_gates():
    messages, context, judged, prepared, compact = specimen()
    assert json.loads(messages[1]["content"]) == context
    assert json.loads(prepared.context.serialized_input) == context
    live = json.loads(prepared.messages[1]["content"])
    assert [row[1] for row in live["CLAIMS"]["rows"]] == ["C001", "C002", "C003"]
    assert live["CONTEXT_COVERAGE"]["requirements"][0]["id"] == "R001"
    assert live["COMPACT_FINDINGS_CODEBOOK"]["observed_binding_refs"] == {
        "C001": ["B001"],
        "C002": [],
        "C003": ["B001"],
    }
    assert all(
        identity not in json.dumps(prepared.messages) for identity in CLAIM_IDS + [REQUIREMENT_ID]
    )
    full = core.decode(compact, prepared.context)
    assert full == ReliableCheckV5.model_validate(judged).model_dump()
    normalized, issues, fragments, bindings = original_views(full, context)
    assert issues == []
    assert checker_inconsistencies(normalized, answer_mode="textbook", bindings=bindings) == []
    contract, defects, sufficiency = assess_requirements(
        normalized,
        context["CONTEXT_COVERAGE"],
        fragments,
        answer_mode="textbook",
        teaching_mode="direct",
    )
    assert contract == defects == [] and sufficiency["status"] == "sufficient"
    proof = full["claims"][2]["derivation"]
    assert validate_derivation(proof, "The distance is 12 m.", {"F001": fragments[0]}, [GIVENS])[
        "valid"
    ]
    assert given_matches(GIVENS, full["claims"][1]["problem_quote"], [GIVENS])
    assert prepared.context.descriptor()["scientific_judgment_defaults"] is False
    assert (
        core.original_contract_diagnostics(full, prepared.context)["publication_authorized"]
        is False
    )


def test_source_only_span_ids_restore_exact_unicode_quotes_and_reject_numeric_offsets():
    _, _, _, prepared, compact = specimen()
    wire_bank = json.loads(prepared.messages[1]["content"])["COMPACT_FINDINGS_CODEBOOK"][
        "source_span_bank"
    ]
    assert wire_bank["layout"] == "contiguous_fragment_end_groups_v1"
    assert wire_bank["columns"] == ["fragment_id", "end", "span_ids_and_starts"]
    bank = core.expand_grouped_source_span_bank(wire_bank)
    assert bank == core.source_span_bank(prepared.context)
    assert bank["columns"] == ["span_id", "fragment_id", "start", "end"]
    rows = [dict(zip(bank["columns"], row, strict=True)) for row in bank["rows"]]
    chosen_id = compact["requirements"][0]["span_ids"][0]
    chosen = next(row for row in rows if row["span_id"] == chosen_id)
    assert chosen["fragment_id"] == "F001" and chosen["start"] == 0 and chosen["end"] == len(SOURCE)
    assert len(SOURCE.encode("utf-8")) > len(SOURCE)
    assert (
        core.decode(compact, prepared.context)["requirements"][0]["evidence"][0]["quote"] == SOURCE
    )
    compact["requirements"][0]["spans"] = [
        {"fragment": "F001", "start": 0, "end": len(SOURCE.encode("utf-8"))}
    ]
    with pytest.raises(ValidationError):
        core.decode(compact, prepared.context)


@pytest.mark.parametrize("flag", core.FLAG_NAMES)
def test_each_semantic_flag_is_required_without_defaults(flag):
    _, _, _, prepared, compact = specimen()
    del compact["semantic_flags"][flag]
    with pytest.raises(ValidationError):
        core.decode(compact, prepared.context)


def test_explicit_negative_semantic_flags_are_not_inferred_positive_from_supported_claims():
    _, _, _, prepared, compact = specimen()
    compact["semantic_flags"] = {flag: False for flag in core.FLAG_NAMES}
    full = core.decode(compact, prepared.context)
    assert all(full[flag] is False for flag in core.FLAG_NAMES)
    assert all(claim["status"] == "supported" for claim in full["claims"])


@pytest.mark.parametrize("fault", ["uncited", "missing", "foreign_binding", "foreign_fragment"])
def test_actual_citation_bindings_cannot_be_invented_omitted_or_replaced(fault):
    _, _, _, prepared, compact = specimen()
    if fault == "uncited":
        compact["claims"][1]["citations"] = deepcopy(compact["claims"][0]["citations"])
    elif fault == "missing":
        compact["claims"][0]["citations"] = []
    elif fault == "foreign_binding":
        compact["claims"][0]["citations"][0]["binding"] = "B999"
    else:
        compact["claims"][0]["citations"][0]["fragments"] = ["F999"]
    with pytest.raises(core.ContractError):
        core.decode(compact, prepared.context)


def test_stale_context_and_changed_server_claim_text_are_rejected():
    messages, context, _, prepared, compact = specimen()
    changed = deepcopy(context)
    changed["question"] += " Explain the conditions."
    messages[1]["content"] = json.dumps(changed)
    fresh = core.prepare(messages, compact_schema(ReliableCheckV5))
    with pytest.raises(core.ContractError, match="FINDINGS_CONTEXT_STALE"):
        core.decode(compact, fresh.context)
    changed["CLAIMS"]["rows"][0][-1] = "Invented altered claim text."
    messages[1]["content"] = json.dumps(changed)
    with pytest.raises(core.ContractError, match="SERVER_CLAIM_TEXT_CHANGED"):
        core.prepare(messages, compact_schema(ReliableCheckV5))
    assert core.decode(compact, prepared.context)["claims"][0]["claim_id"] == CLAIM_IDS[0]


@pytest.mark.parametrize(
    "scope", ["hint", "general", "memory", "exposure", "pending", "cumulative", "offline"]
)
def test_unsupported_contexts_fail_before_any_provider_call(scope):
    messages, context, _, _, _ = specimen()
    if scope == "hint":
        context["POLICY"]["teaching_mode"] = "hint"
    elif scope == "general":
        context["answer_mode"] = "general_knowledge"
    elif scope == "memory":
        context["memory_context"] = {"entries": [{"content": "synthetic private context"}]}
    elif scope == "exposure":
        context["PRIOR_EXPOSURE"] = {"disabled": False}
    elif scope == "pending":
        context["TUTOR_QUESTION"] = {"question": "A pending action"}
    elif scope == "cumulative":
        context["POLICY"]["check_cumulative"] = True
    else:
        context["POLICY"]["online_check"] = False
    messages[1]["content"] = json.dumps(context)
    with pytest.raises(core.ContractError):
        core.prepare(messages, compact_schema(ReliableCheckV5))


@pytest.mark.parametrize("fault", ["arithmetic", "units", "applicability", "unquoted_formula"])
def test_original_science_validator_rejects_invalid_proof_after_lossless_decode(fault):
    _, context, judged, prepared, _ = specimen()
    proof = judged["claims"][2]["derivation"]
    if fault == "arithmetic":
        proof["expression"] = "speed + time"
    elif fault == "units":
        proof["units_consistent"] = False
    elif fault == "applicability":
        proof["formula_applicable"] = False
    else:
        proof["formula_quote"] = "A formula absent from the source."
    compact = core.compact_from_v5(judged, prepared.context)
    full = core.decode(compact, prepared.context)
    assert full["claims"][2]["derivation"] == proof
    _, _, fragments, _ = original_views(full, context)
    verdict = validate_derivation(proof, "The distance is 12 m.", {"F001": fragments[0]}, [GIVENS])
    assert verdict["valid"] is False


@pytest.mark.parametrize("fault", ["reserved_prefix", "nested_identity", "unknown_json_identity"])
def test_unproven_feedback_identity_envelopes_are_rejected(fault):
    messages, _, _, _, _ = specimen()
    prefix = (
        "Re-evaluate exactly the same unchanged draft and source display. "
        "Your previous check had contract contradictions. "
    )
    marker = "CHECKER_CONTRACT_ISSUES_JSON:\n"
    if fault == "reserved_prefix":
        text = (
            "Untrusted correction. "
            + marker
            + json.dumps([{"code": "X", "claim_id": CLAIM_IDS[0]}])
        )
    elif fault == "nested_identity":
        text = (
            prefix + marker + json.dumps([{"code": "X", "diagnostic": {"claim_id": CLAIM_IDS[0]}}])
        )
    else:
        text = json.dumps({"claim_id": CLAIM_IDS[0], "semantic_evidence": "Unproven extra context"})
    messages.append({"role": "user", "content": text})
    with pytest.raises(core.ContractError):
        core.prepare(messages, compact_schema(ReliableCheckV5))


@pytest.mark.parametrize(
    "fault", ["unknown", "duplicate", "malformed", "missing_hash", "wrong_hash"]
)
def test_source_span_ids_and_required_bank_hash_cannot_be_invented_or_reused(fault):
    _, _, _, prepared, compact = specimen()
    row = compact["requirements"][0]
    if fault == "unknown":
        row["span_ids"] = ["S9999"]
    elif fault == "duplicate":
        row["span_ids"] *= 2
    elif fault == "malformed":
        row["span_ids"] = ["F001"]
    elif fault == "missing_hash":
        del compact["source_span_bank_sha256"]
    else:
        compact["source_span_bank_sha256"] = "0" * 64
    with pytest.raises((core.ContractError, ValidationError)):
        core.decode(compact, prepared.context)


def test_source_span_bank_is_deterministic_source_only_and_bound_to_unicode_context():
    messages, context, _, prepared, compact = specimen()
    bank = core.source_span_bank(prepared.context)
    assert core.digest(bank) == prepared.context.descriptor()["source_span_bank_sha256"]
    assert compact["source_span_bank_sha256"] == core.digest(bank)
    changed = deepcopy(context)
    changed["question"] += " Explain the conditions."
    messages[1]["content"] = json.dumps(changed)
    fresh = core.prepare(messages, compact_schema(ReliableCheckV5))
    assert core.source_span_bank(fresh.context) == bank
    assert fresh.context.sha256 != prepared.context.sha256
    with pytest.raises(core.ContractError, match="FINDINGS_CONTEXT_STALE"):
        core.decode(compact, fresh.context)
    assert bank["columns"] == ["span_id", "fragment_id", "start", "end"]
    assert not any(key in bank["columns"] for key in ["quote", "reason", "basis", "status", "gold"])
    rows = [dict(zip(bank["columns"], row, strict=True)) for row in bank["rows"]]
    assert all(
        row["fragment_id"] == "F001" and 0 <= row["start"] < row["end"] <= len(SOURCE)
        for row in rows
    )


def test_actual_public_arithmetic_probe_rejects_twelve_span_ids_without_truncation():
    """Replay public call14 content; its model judgments are not a scientific pass."""
    raw = (
        '{"version":"compact_findings_v3","context_sha256":"3b5f82eef9617968442'
        'a912d20ec7b6b0e004f92fda5240ac1788ef1d77a2912","source_span_bank_sha25'
        '6":"edd6818a0fba8d10ebbe0666f093695120b523f860b1e7fd0a24fc989c041cb1",'
        '"claims":[{"claim_id":"C001","basis":"textbook","status":"supported","'
        'reason":"Distance equation is directly supported by fragment F001.","c'
        'itations":[{"binding":"B001","fragments":["F001"],"relation":"supporti'
        'ng"}],"problem_quote":null,"derivation":null},{"claim_id":"C002","basi'
        's":"problem_input","status":"supported","reason":"Speed and time are d'
        'irectly given in the problem statement.","citations":[],"problem_quote'
        '":"Speed is 3 m/s and elapsed time is 4 s.","derivation":null},{"claim'
        '_id":"C003","basis":"derived_calculation","status":"supported","reason'
        '":"Calculation correctly multiplies speed by time.","citations":[{"bin'
        'ding":"B001","fragments":["F001"],"relation":"supporting"}],"problem_q'
        'uote":null,"derivation":{"expression":"speed * time","formula_applicab'
        'le":true,"formula_basis":"textbook","formula_fragment_id":"F001","form'
        'ula_quote":"Distance equals speed multiplied by elapsed time: distance'
        ' = speed * time.","inputs":[{"fragment_id":null,"name":"speed","origin'
        '":"problem_input","quote":"Speed is 3 m/s","unit":"m/s","value":"3"},{'
        '"fragment_id":null,"name":"time","origin":"problem_input","quote":"ela'
        'psed time is 4 s","unit":"s","value":"4"}],"result":"12","result_quote'
        '":"The distance is 12 m.","result_unit":"m","units_consistent":true}}]'
        ',"requirements":[{"requirement_id":"R001","relevance":"related","suffi'
        'ciency":"sufficient","span_ids":["S0001","S0002","S0003","S0004","S000'
        '5","S0006","S0007","S0008","S0009","S0010","S0011","S0012"],"condition'
        's_preserved":true,"response_coverage":"covered","missing_information":'
        '"","reason":"The requirement is fully supported by the source text and'
        ' problem input."}],"semantic_flags":{"body_ok":true,"specific_help":tr'
        'ue,"scope_ok":true,"suggestions_ok":true,"evidence_display_ok":true,"c'
        'umulative_ok":true,"complete_answer":true,"limitations_explicit":true,'
        '"attempt_evaluation_ok":true,"tutor_question_ok":true,"non_repetitive_'
        'next_action":true},"missing_facets":[],"reason":"All claims and requir'
        'ements are fully supported.","repair_fragment_ids":[]}'
    )
    assert hashlib.sha256(raw.encode("utf-8")).hexdigest() == (
        "392f02136822fc00c810b4773efc5ecc68d37d00a7778ca798f3beb9b9e20f10"
    )
    compact = json.loads(raw)
    assert compact["requirements"][0]["span_ids"] == [f"S{i:04}" for i in range(1, 13)]
    before = deepcopy(compact)
    with pytest.raises(ValidationError) as rejected:
        core.CompactFindings.model_validate(compact)
    errors = rejected.value.errors(include_url=False, include_input=False)
    assert len(errors) == 1
    assert errors[0]["loc"] == ("requirements", 0, "span_ids")
    assert errors[0]["type"] == "too_long"
    assert errors[0]["ctx"]["max_length"] == 8
    assert compact == before


def test_grouped_prompt_span_limit_matches_schema_and_keeps_all_source_alternatives():
    _, _, _, prepared, compact = specimen()
    schema_limit = prepared.schema["$defs"]["RequirementFinding"]["properties"]["span_ids"][
        "maxItems"
    ]
    instruction = re.search(
        r"For each requirement, select at most (\d+) distinct ORIGINAL span_ids",
        prepared.messages[0]["content"],
    )
    assert instruction is not None and int(instruction.group(1)) == schema_limit == 8
    wire_bank = json.loads(prepared.messages[1]["content"])["COMPACT_FINDINGS_CODEBOOK"][
        "source_span_bank"
    ]
    bank = core.source_span_bank(prepared.context)
    assert len(bank["rows"]) > schema_limit
    assert core.expand_grouped_source_span_bank(wire_bank) == bank
    evidence = core.decode(compact, prepared.context)["requirements"][0]["evidence"]
    assert evidence == [{"evidence_id": "ev_001", "fragment_id": "F001", "quote": SOURCE}]


def test_saved_modes_send_distinct_complete_compact_checker_wire_contracts():
    from dataclasses import replace

    from generation import google_schema_compiler04 as google
    from generation import providers
    from generation.types import ModelConfig

    messages, _, _, prepared, _ = specimen()
    canonical_schema = compact_schema(ReliableCheckV5)
    original_messages = deepcopy(messages)
    original_schema = deepcopy(canonical_schema)
    schema_config = ModelConfig(
        provider="openai_compatible",
        model="google/gemini-3.5-flash-lite",
        base_url="https://openrouter.ai/api/v1",
        temperature=None,
        max_tokens=4096,
        window_tokens=131072,
        structured_output_mode="json_schema",
        configuration_id="authored-offline-compact-schema-v1",
        openrouter_route_profile="gemini35_google_vertex_compact_checker_v3",
    )
    object_config = replace(
        schema_config,
        structured_output_mode="json_object",
        configuration_id="authored-offline-compact-object-v1",
    )
    saved_schema_config = schema_config.to_dict()
    saved_object_config = object_config.to_dict()
    certificate = google.compile_google_contract(
        prepared.schema, target="gemini_response_json_schema"
    )
    schema_body = providers.payload(schema_config, messages, canonical_schema, "joint_check_v5")
    object_body = providers.payload(object_config, messages, canonical_schema, "joint_check_v5")

    assert schema_body["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "compact_findings_v3",
            "strict": True,
            "schema": certificate["schema"],
        },
    }
    wire_schema = schema_body["response_format"]["json_schema"]["schema"]
    requirement = wire_schema["properties"]["requirements"]["items"]
    assert requirement["properties"]["span_ids"]["maxItems"] == 8
    assert set(requirement["required"]) == {
        "requirement_id",
        "relevance",
        "sufficiency",
        "span_ids",
        "conditions_preserved",
        "response_coverage",
        "missing_information",
        "reason",
    }
    claim = wire_schema["properties"]["claims"]["items"]
    assert set(claim["required"]) == {
        "claim_id",
        "basis",
        "status",
        "reason",
        "citations",
        "problem_quote",
        "derivation",
    }
    proof = next(
        branch
        for branch in claim["properties"]["derivation"]["anyOf"]
        if branch.get("type") == "object"
    )
    assert set(proof["required"]) == {
        "formula_basis",
        "formula_fragment_id",
        "formula_quote",
        "expression",
        "inputs",
        "result",
        "result_quote",
        "result_unit",
        "units_consistent",
        "formula_applicable",
    }
    assert set(proof["properties"]["inputs"]["items"]["required"]) == {
        "name",
        "value",
        "unit",
        "quote",
        "origin",
        "fragment_id",
    }
    flags = wire_schema["properties"]["semantic_flags"]
    assert set(flags["required"]) == set(core.FLAG_NAMES)
    assert len(flags["required"]) == 11
    assert schema_body["messages"] == prepared.messages
    assert object_body["response_format"] == {"type": "json_object"}
    schema_prompt = object_body["messages"][0]["content"].split("Match this JSON schema: ", 1)
    assert len(schema_prompt) == 2 and json.loads(schema_prompt[1]) == certificate["schema"]
    assert object_body["messages"][1:] == schema_body["messages"][1:]
    assert object_body["provider"] == schema_body["provider"]
    assert schema_config.to_dict() == saved_schema_config
    assert object_config.to_dict() == saved_object_config
    assert messages == original_messages and canonical_schema == original_schema
