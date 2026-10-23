"""Authored engineering fixtures; no labels here measure semantic accuracy."""

from copy import deepcopy
import hashlib
import json

from generation import GenerationRequest, ModelConfig, RequestBudget
from generation import assertion_provenance_v1 as assertions
from generation import assertion_reselection_v1 as reselection
from generation.checker_encoding import decode
from generation.reliability_v5 import response_claims
from generation.types import ProviderResult
from retrieval.source_spans import map_fragments


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fixture_request():
    blocks = [
        (
            "ev_001",
            [
                "When valve A is open, pressure from chamber P moves piston T.",
                "This motion lifts the load attached to piston T against gravity.",
                "Motion of piston U closes valve B.",
            ],
        ),
        ("ev_002", ["A lever rotates around a fixed pivot."]),
    ]
    evidence, source_map = [], {}
    for number, (eid, quotes) in enumerate(blocks, 1):
        text = "\n\n".join(quotes)
        chunk, unit = f"authored-chunk-{number}", f"authored-unit-{number}"
        positions, cursor = [], 0
        for quote in quotes:
            positions.append({"start": cursor, "end": cursor + len(quote), "kind": "prose"})
            cursor += len(quote) + 2
        evidence.append(
            {
                "evidence_id": eid,
                "chunk_id": chunk,
                "asset_id": f"authored-asset-{number}",
                "processing_id": "authored-processing",
                "source_title": "Authored mechanical control",
                "section": "Conditions and links",
                "pages": [number],
                "locator": f"Authored page {number}",
                "text": text,
                "text_hash": sha(text),
                "context_order": number,
                "inherited_from": None,
                "license": None,
                "source_url": None,
            }
        )
        source_map[chunk] = {
            "document_version_id": "authored-version",
            "processing_id": "authored-processing",
            "asset_id": f"authored-asset-{number}",
            "chunk_text": text,
            "chunk_hash": sha(text),
            "units": [
                {
                    "id": unit,
                    "page": number,
                    "cleaned_text": text,
                    "text_hash": sha(text),
                    "blocks": positions,
                }
            ],
            "spans": [
                {
                    "unit_id": unit,
                    "page": number,
                    "start": 0,
                    "end": len(text),
                    "chunk_start": 0,
                    "chunk_end": len(text),
                }
            ],
        }
    return GenerationRequest(
        request_id="authored-phase163-parent",
        mode="interactive_chat",
        condition="E1",
        question="Under what condition does pressure move the piston and lift its attached load?",
        evidence=evidence,
        source_map=source_map,
        enhancement_version="learning_enhancement_v1",
        reliability_policy="evidence_reliability_v5",
        checker_payload_policy="lossless_checker_tables_v1",
        assertion_source_policy=assertions.POLICY,
        teaching_context={"turn_role": "user_question", "teaching_mode": "direct", "help_level": 0},
        prepared_query={
            "intent": "factual",
            "topic_relation": "new_topic",
            "needs_clarification": False,
        },
        config=ModelConfig(
            provider="openai",
            model="gpt-6-luna",
            temperature=None,
            token_limit_parameter="max_completion_tokens",
            window_tokens=65536,
            tokenizer_provider="estimate",
            token_count_fallback="error",
        ),
    )


def private_draft(*, source_ids=None):
    return {
        "schema_version": "chat_response_v1",
        "response_type": "answer",
        "answer_text": [
            {
                "assertion_id": "A001",
                "text": "When valve A is open, pressure from chamber P moves piston T and that motion lifts the load attached to T against gravity.",
                "source_ids": source_ids or ["F001"],
            },
            {
                "assertion_id": "A002",
                "text": "A lever rotates around a fixed pivot.",
                "source_ids": ["F004"],
            },
        ],
        "short_answer": None,
        "citations": ["ev_001", "ev_002"],
        "refusal_reason": None,
        "follow_up_questions": [],
        "confidence": None,
        "tutor_question": None,
        "learner_attempt_evaluation": None,
    }


def checker_labels(provenance, *, negative_target=True):
    rows = []
    for row in provenance["assertions"]:
        grouped = {}
        for source in row["sources"]:
            grouped.setdefault(source["evidence_id"], []).append(source["source_id"])
        negative = row["assertion_id"] == "A001" and negative_target
        rows.append(
            {
                "claim_id": row["claim_id"],
                "basis": "textbook",
                "status": "partial" if negative else "supported",
                "reason": "Authored control label; not measured entailment.",
                "citations": [
                    {"evidence_id": eid, "fragment_ids": ids, "relation": "supporting"}
                    for eid, ids in grouped.items()
                ],
                "proof_audit": {
                    "all_predicates_entailed": not negative,
                    "actor_identity_preserved": True,
                    "conditions_preserved": True,
                    "causal_bridges_entailed": not negative,
                    "missing_predicates": ["The selected union lacks the load-lifting link."]
                    if negative
                    else [],
                    "reason": "Authored source-selection control; no native or human gold claim.",
                },
            }
        )
    first = provenance["assertions"][0]["sources"][0]
    return {
        "claims": rows,
        "body_ok": not negative_target,
        "specific_help": True,
        "scope_ok": True,
        "suggestions_ok": True,
        "evidence_display_ok": True,
        "cumulative_ok": True,
        "complete_answer": True,
        "coverage": "full",
        "missing_facets": [],
        "limitations_explicit": True,
        "reason": "Authored engineering state only.",
        "repair_fragment_ids": [],
        "attempt_evaluation_ok": "not_applicable",
        "tutor_question_ok": True,
        "non_repetitive_next_action": True,
        "requirements": [
            {
                "requirement_id": "requirement_01",
                "relevance": "related",
                "sufficiency": "sufficient",
                "evidence": [
                    {
                        "evidence_id": first["evidence_id"],
                        "fragment_id": first["source_id"],
                        "quote": first["exact_text"],
                    }
                ],
                "conditions_preserved": True,
                "response_coverage": "covered",
                "missing_information": "",
                "reason": "Authored whole-bank availability label; independent of selected claim support.",
            }
        ],
    }


def authored_parent(*, source_ids=None):
    request = fixture_request()
    fragments, issues = map_fragments(request.evidence, request.source_map)
    if issues:
        raise AssertionError("Authored complete source blocks must map without issues")
    draft = private_draft(source_ids=source_ids)
    public, provenance = assertions.compile_draft(draft, fragments)
    public.pop("tutor_question")
    public.pop("learner_attempt_evaluation")
    typed = checker_labels(provenance)
    budget = RequestBudget(consumed_calls=2, active_seconds=1.0).to_dict()
    parent = {
        "response": None,
        "error": {
            "code": "SEMANTIC_CHECK_FAILED",
            "message": "Authored initial selection failure.",
            "details": {},
        },
        "evidence": deepcopy(request.evidence),
        "attribution": {"fragments": deepcopy(fragments)},
        "token_budget": {},
        "budget": budget,
        "drafts": [
            {
                "revision": 0,
                "published": False,
                "response": public,
                "assertion_provenance": provenance,
                "raw_model_output": json.dumps(draft),
                "tutor_question": None,
                "learner_attempt_evaluation": None,
            }
        ],
        "checks": [
            {
                "revision": 0,
                "accepted": False,
                "validation_state": "validated",
                "checker_inconsistencies": [],
                "checker_contract_revision": 0,
                "typed_judgment_raw_aliases": typed,
                "actual_citation_bindings": assertions.checker_bindings(
                    response_claims(public), provenance, fragments
                ),
                "structural_issues": [],
                "publication_block": {
                    "requirement_issue_codes": [],
                    "failed_checker_gate_names": ["body_ok"],
                },
            }
        ],
        "attempts": [
            {
                "stage": stage,
                "request_submitted": True,
                "error": None,
                "usage": {"total_tokens": 100},
                "provider": "deliberately_scripted_offline",
                "model": "authored_control",
            }
            for stage in ("generation", "joint_check")
        ],
    }
    return request, parent, fragments


def diagnosis_for(request, parent, fragments, *, candidate_ids=None, target_index=0):
    row = parent["drafts"][0]["assertion_provenance"]["assertions"][target_index]
    bank = assertions.source_bank(fragments, parent["evidence"])
    return {
        "version": reselection.DIAGNOSIS_VERSION,
        "parent_outcome_sha256": reselection.canonical_sha256(parent),
        "request_binding_sha256": reselection.request_sha256(request),
        "source_bank_sha256": reselection.canonical_sha256(bank),
        "targets": [
            {
                "claim_id": row["claim_id"],
                "kind": "selection_gap",
                "prior_binding_sha256": reselection.binding_sha256(row),
                "missing_predicates": ["A possible load-lifting premise is unselected."],
                "candidate_source_ids": candidate_ids if candidate_ids is not None else ["F002"],
                "reason": "Authored independent diagnosis, not a model-derived support override.",
            }
        ],
    }


def freeze(request, parent, fragments, *, diagnosis=None):
    return reselection.freeze_continuation(
        request,
        parent,
        diagnosis or diagnosis_for(request, parent, fragments),
        parent_draft_id="authored-saved-draft",
        parent_check_id="authored-saved-check",
        source_admission={"release_id": "authored-release", "source_epoch": "authored-epoch"},
    )


def prepare_fixture(*, source_ids=None, candidate_ids=None):
    request, parent, fragments = authored_parent(source_ids=source_ids)
    diagnosis = diagnosis_for(request, parent, fragments, candidate_ids=candidate_ids)
    continuation = freeze(request, parent, fragments, diagnosis=diagnosis)
    budget = RequestBudget.from_dict(parent["budget"])
    plan = reselection.prepare(request, continuation, fragments, parent["evidence"], budget)
    return request, parent, fragments, continuation, plan


def proposal_for(plan, *, ids=None):
    target = plan["diagnosis"]["targets"][0]
    return {
        "plan_sha256": plan["plan_sha256"],
        "replacements": [
            {
                "claim_id": target["claim_id"],
                "prior_binding_sha256": target["prior_binding_sha256"],
                "selections": [
                    {
                        "evidence_id": "ev_001",
                        "source_ids": ids if ids is not None else ["F001", "F002"],
                    }
                ],
            }
        ],
    }


def packet_from_messages(messages):
    value = json.loads(messages[-1]["content"])
    if "CHECKER_INPUT_ENCODING" in value:
        value = decode(value)
    if "SOURCE_FRAGMENT_TABLE" in value:
        table = value.pop("SOURCE_FRAGMENT_TABLE")
        value["SOURCE_FRAGMENTS"] = [
            dict(zip(table["columns"], row, strict=True)) for row in table["rows"]
        ]
    return value


class ScriptedTransport:
    """Finite explicit selector/check messages; no production model fallback."""

    def __init__(self, values):
        self.values = list(values)
        self.calls = []

    def generate(self, messages, **kwargs):
        if len(self.calls) >= len(self.values):
            raise AssertionError("Unexpected extra offline transport invocation")
        value = self.values[len(self.calls)]
        self.calls.append((deepcopy(messages), deepcopy(kwargs)))
        if callable(value):
            value = value(messages)
        if isinstance(value, ProviderResult):
            return value
        return ProviderResult(
            raw_text=value if isinstance(value, str) else json.dumps(value),
            finish_reason="stop",
            provider="deliberately_scripted_offline",
            model="authored_control",
            request_submitted=True,
        )
