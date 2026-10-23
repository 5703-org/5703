"""Frozen real failures and authored provenance controls; no semantic score override."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import socket
from types import SimpleNamespace
from urllib import request as urllib_request

import pytest
from pydantic import ValidationError

from generation import GenerationRequest, GenerationService, ModelConfig, RequestBudget
from generation import assertion_provenance_v1 as transport
from generation.adapters import LLMAdapter
from generation.checker_encoding import decode, dumps, encode
from generation.parser import parse_response
from generation.reliability_v4 import normalize_judgment
from generation.reliability_v5 import OrdinaryQuestionCheckV5, response_claims
from generation.types import ProviderResult

FIXTURES = Path(__file__).parents[1] / "fixtures" / "assertion161"
CAPTURE = json.loads((FIXTURES / "captured160-cases.json").read_text(encoding="utf-8"))
CASES = {row["case_id"]: row for row in CAPTURE["cases"]}


@pytest.fixture(autouse=True)
def no_external_io(monkeypatch):
    """Block sockets, actual model adapter and engine connection paths per test."""
    attempts = []

    def blocked(*args, **kwargs):
        attempts.append("blocked_external_io")
        raise AssertionError("Phase161 tests permit no network, provider or database access")

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)
    monkeypatch.setattr(urllib_request, "urlopen", blocked)
    monkeypatch.setattr(LLMAdapter, "generate", blocked)
    from sqlalchemy.engine import Engine

    monkeypatch.setattr(Engine, "connect", blocked)
    yield
    assert attempts == [], "An external call was attempted and blocked"


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fragment(fid, eid, text, **changes):
    return {
        "fragment_id": fid,
        "evidence_id": eid,
        "exact_text": text,
        "complete_block": True,
        "text_hash": sha(text),
        **changes,
    }


def sources():
    return [
        fragment(
            "original-valve",
            "ev_001",
            "When valve A is open, sodium moves downhill through transporter T.",
        ),
        fragment(
            "original-bridge",
            "ev_002",
            "This sodium movement supplies the energy to move attached glucose uphill through transporter T.",
        ),
        fragment(
            "original-definition",
            "ev_003",
            "A symporter carries two substances in the same direction.",
        ),
    ]


def private_draft(text=None, ids=None, *, extra=False, short=False):
    rows = [
        {
            "assertion_id": "A001",
            "text": text
            or "When valve A is open, sodium movement supplies the energy to move attached glucose uphill through transporter T.",
            "source_ids": ["F001", "F002"] if ids is None else ids,
        }
    ]
    if extra:
        rows.append(
            {
                "assertion_id": "A002",
                "text": "A symporter carries two substances in the same direction.",
                "source_ids": ["F003"],
            }
        )
    eids = []
    lookup = {"F001": "ev_001", "F002": "ev_002", "F003": "ev_003"}
    for row in rows:
        eids.extend(lookup[fid] for fid in row["source_ids"] if fid in lookup)
    return {
        "schema_version": "chat_response_v1",
        "response_type": "answer",
        "answer_text": rows,
        "short_answer": {
            "assertion_id": "S001",
            "text": "The sodium movement drives attached glucose uphill when valve A is open.",
            "source_ids": ["F001", "F002"],
        }
        if short
        else None,
        "citations": list(dict.fromkeys(eids)),
        "refusal_reason": None,
        "follow_up_questions": [],
        "confidence": None,
        "tutor_question": None,
        "learner_attempt_evaluation": None,
    }


def compiled(*, extra=False, short=False):
    public, provenance = transport.compile_draft(private_draft(extra=extra, short=short), sources())
    return public, provenance, response_claims(public)


def authored_claims(provenance):
    """Deliberately canned labels test transport/gates, never factual entailment."""
    rows = []
    for target in provenance["assertions"]:
        grouped = {}
        for source in target["sources"]:
            grouped.setdefault(source["evidence_id"], []).append(source["source_id"])
        rows.append(
            {
                "claim_id": target["claim_id"],
                "basis": "textbook",
                "status": "supported",
                "reason": "Authored semantic label for mechanical regression only.",
                "citations": [
                    {"evidence_id": eid, "fragment_ids": ids, "relation": "supporting"}
                    for eid, ids in grouped.items()
                ],
                "proof_audit": {
                    "all_predicates_entailed": True,
                    "actor_identity_preserved": True,
                    "conditions_preserved": True,
                    "causal_bridges_entailed": True,
                    "missing_predicates": [],
                    "reason": "Authored label; semantic accuracy is not measured.",
                },
            }
        )
    return {"claims": rows}


@pytest.mark.parametrize("case_id", ["Q01", "Q02"])
def test_exact_original_body_check_transport_hashes_and_failed_status_remain(case_id):
    case = CASES[case_id]
    assert sha(case["original_draft_raw"]) == case["original_generation_content_sha256"]
    assert sha(case["original_checker_raw"]) == case["original_joint_check_content_sha256"]
    packet = decode(encode(case["checker_packet"]))
    assert packet == case["checker_packet"]
    assert sha(dumps(encode(packet))) == case["original_checker_packet_transport_sha256"]
    draft = json.loads(case["original_draft_raw"])
    public = {
        key: value
        for key, value in draft.items()
        if key not in {"tutor_question", "learner_attempt_evaluation"}
    }
    parsed = parse_response(
        json.dumps(public),
        mode="interactive_chat",
        condition="E1",
        evidence_ids=[row["evidence_id"] for row in case["selected_evidence"]],
        answer_mode="textbook",
    )
    assert response_claims(parsed) == packet["CLAIMS"]
    typed = OrdinaryQuestionCheckV5.model_validate(
        json.loads(case["original_checker_raw"])
    ).model_dump()
    judgment, issues = normalize_judgment(typed, packet["ACTUAL_CITATION_BINDINGS"])
    assert judgment["body_ok"] is False
    assert any(row["status"] != "supported" for row in judgment["claims"])
    assert case["original_native_failure"]["error"]["code"] == "SEMANTIC_CHECK_FAILED"
    assert case["original_native_failure"]["answer_id"] is None
    assert case["original_outcome"] == "FAIL"
    if case_id == "Q01":
        assert packet["ACTUAL_CITATION_BINDINGS"][1]["citations"] == []
        assert {row["code"] for row in issues} == {"ACTUAL_CITATION_FRAGMENT_INVALID"}
        wrong = next(row for row in packet["SOURCE_FRAGMENTS"] if row["fragment_id"] == "F048")
        assert wrong["evidence_id"] == "ev_006"
    else:
        assert issues == []
        generic = next(row for row in packet["SOURCE_FRAGMENTS"] if row["fragment_id"] == "F019")
        assert (
            generic["evidence_id"] == "ev_003"
            and "sodium" not in generic["exact_text"].lower()
            and "glucose" not in generic["exact_text"].lower()
        )


@pytest.mark.parametrize(
    "case_id,claim_index,ids", [("Q01", 0, ["F007"]), ("Q02", 0, ["F001", "F002", "F003", "F007"])]
)
def test_declared_real_support_derivative_keeps_whole_prose_and_exact_union_without_relabelling(
    case_id, claim_index, ids
):
    case = CASES[case_id]
    original = deepcopy(case)
    claim = case["checker_packet"]["CLAIMS"][claim_index]
    text = re.sub(r"\s*\[ev_\d{3,}\]", "", claim["text"]).strip()
    fragments = case["checker_packet"]["SOURCE_FRAGMENTS"]
    chosen = [row for row in fragments if row["fragment_id"] in ids]
    value = private_draft(text, ids)
    value["citations"] = list(dict.fromkeys(row["evidence_id"] for row in chosen))
    public, provenance = transport.compile_draft(value, fragments)
    packet = transport.checker_packet(provenance)
    assert public["answer_text"].startswith(text)
    assert packet["assertions"][0]["full_assertion"] == text
    assert packet["assertions"][0]["selected_source_union"] == [
        {
            "fragment_id": row["fragment_id"],
            "evidence_id": row["evidence_id"],
            "exact_text": row["exact_text"],
            "text_sha256": sha(row["exact_text"]),
            "source_locator": {},
        }
        for row in chosen
    ]
    assert packet["semantic_support_certified"] is False
    assert case == original and case["original_outcome"] == "FAIL"
    assert CAPTURE["annotations"]["originals_relabelled"] is False


def test_compiler_public_parser_and_checker_share_ids_whole_prose_sources_and_hashes():
    public, provenance, claims = compiled(extra=True, short=True)
    parsed = parse_response(
        json.dumps(
            {
                key: value
                for key, value in public.items()
                if key not in {"tutor_question", "learner_attempt_evaluation"}
            }
        ),
        mode="interactive_chat",
        condition="E1",
        evidence_ids=["ev_001", "ev_002", "ev_003"],
        answer_mode="textbook",
    )
    assert response_claims(parsed) == claims
    bindings = transport.checker_bindings(claims, provenance, sources())
    packet = transport.checker_packet(provenance)
    assert [row["assertion_id"] for row in packet["assertions"]] == ["A001", "A002", "S001"]
    assert [row["claim_id"] for row in packet["assertions"]] == [row["claim_id"] for row in claims]
    assert bindings[0]["citations"] == [
        {"evidence_id": "ev_001", "allowed_fragment_ids": ["F001"]},
        {"evidence_id": "ev_002", "allowed_fragment_ids": ["F002"]},
    ]
    assert bindings[1]["citations"] == [{"evidence_id": "ev_003", "allowed_fragment_ids": ["F003"]}]
    for proof, row in zip(packet["assertions"], provenance["assertions"], strict=True):
        assert proof["full_assertion"] == row["assertion_text"]
        assert proof["assertion_sha256"] == sha(row["assertion_text"])
        for source in proof["selected_source_union"]:
            assert source["text_sha256"] == sha(source["exact_text"])
    assert provenance["semantic_support_certified"] is False


@pytest.mark.parametrize(
    "defect",
    [
        "unknown_alias",
        "duplicate_source",
        "missing_assertion_id",
        "wrong_assertion_id",
        "duplicate_assertion_id",
        "inline_marker",
        "multiple_sentences",
        "hidden_prefix",
        "wrong_citations",
        "bad_fragment_hash",
        "duplicate_fragment",
        "incomplete_block",
    ],
)
def test_invalid_private_draft_cannot_create_public_citation_binding(defect):
    value, fragments = private_draft(extra=True), sources()
    if defect == "unknown_alias":
        value["answer_text"][0]["source_ids"] = ["F999"]
    elif defect == "duplicate_source":
        value["answer_text"][0]["source_ids"] = ["F001", "F001"]
    elif defect == "missing_assertion_id":
        del value["answer_text"][0]["assertion_id"]
    elif defect == "wrong_assertion_id":
        value["answer_text"][0]["assertion_id"] = "A002"
    elif defect == "duplicate_assertion_id":
        value["answer_text"][1]["assertion_id"] = "A001"
    elif defect == "inline_marker":
        value["answer_text"][0]["text"] += " [ev_003]"
    elif defect == "multiple_sentences":
        value["answer_text"][0]["text"] += " A second unrelated fact follows."
    elif defect == "hidden_prefix":
        value["answer_text"][0]["text"] = "\n" + value["answer_text"][0]["text"]
    elif defect == "wrong_citations":
        value["citations"] = ["ev_003"]
    elif defect == "bad_fragment_hash":
        fragments[0]["text_hash"] = "0" * 64
    elif defect == "duplicate_fragment":
        fragments[1]["fragment_id"] = fragments[0]["fragment_id"]
    elif defect == "incomplete_block":
        fragments[0]["complete_block"] = False
    with pytest.raises((ValueError, ValidationError)):
        transport.compile_draft(value, fragments)


@pytest.mark.parametrize(
    "defect",
    [
        "claim_text",
        "claim_id",
        "claim_start",
        "claim_evidence",
        "source_text",
        "source_parent",
        "source_alias_order",
        "provenance_text",
        "duplicate_selected_source",
    ],
)
def test_consumer_rejects_drift_in_same_assertion_and_actual_source_binding(defect):
    public, provenance, claims = compiled()
    fragments = sources()
    if defect == "claim_text":
        claims[0]["text"] += " Extra."
    elif defect == "claim_id":
        claims[0]["claim_id"] = "foreign-claim"
    elif defect == "claim_start":
        claims[0]["start"] += 1
    elif defect == "claim_evidence":
        claims[0]["evidence_ids"] = ["ev_003"]
    elif defect == "source_text":
        fragments[0]["exact_text"] += " Altered."
        fragments[0]["text_hash"] = sha(fragments[0]["exact_text"])
    elif defect == "source_parent":
        fragments[0]["evidence_id"] = "ev_003"
    elif defect == "source_alias_order":
        fragments.reverse()
    elif defect == "provenance_text":
        provenance["assertions"][0]["assertion_text"] = "A different proposition."
        provenance["assertions"][0]["assertion_sha256"] = sha("A different proposition.")
    elif defect == "duplicate_selected_source":
        provenance["assertions"][0]["sources"].append(
            deepcopy(provenance["assertions"][0]["sources"][0])
        )
    with pytest.raises(ValueError):
        transport.checker_bindings(claims, provenance, fragments)


@pytest.mark.parametrize(
    "defect",
    [
        "missing_claim",
        "duplicate_claim",
        "foreign_claim",
        "drop_source",
        "add_foreign_source",
        "wrong_parent",
        "duplicate_citation",
        "wrong_basis",
    ],
)
def test_checker_cannot_replace_or_borrow_another_assertions_actual_sources(defect):
    _, provenance, _ = compiled(extra=True)
    value = authored_claims(provenance)
    if defect == "missing_claim":
        value["claims"].pop()
    elif defect == "duplicate_claim":
        value["claims"].append(deepcopy(value["claims"][0]))
    elif defect == "foreign_claim":
        value["claims"][0]["claim_id"] = "foreign-claim"
    elif defect == "drop_source":
        value["claims"][0]["citations"].pop()
    elif defect == "add_foreign_source":
        value["claims"][0]["citations"].append(deepcopy(value["claims"][1]["citations"][0]))
    elif defect == "wrong_parent":
        value["claims"][0]["citations"][0]["fragment_ids"] = ["F003"]
    elif defect == "duplicate_citation":
        value["claims"][0]["citations"].append(deepcopy(value["claims"][0]["citations"][0]))
    elif defect == "wrong_basis":
        value["claims"][0]["basis"] = "nonfactual"
    assert transport.assess_judgment(value, provenance)


@pytest.mark.parametrize(
    "field",
    [
        "all_predicates_entailed",
        "actor_identity_preserved",
        "conditions_preserved",
        "causal_bridges_entailed",
        "missing_predicates",
    ],
)
def test_full_selected_union_never_overrides_a_reported_semantic_gap(field):
    _, provenance, _ = compiled()
    value = authored_claims(provenance)
    value["claims"][0]["proof_audit"][field] = (
        ["Missing required condition"] if field == "missing_predicates" else False
    )
    assert transport.assess_judgment(value, provenance) == [
        {"code": "ASSERTION_PROOF_AUDIT_FAILED", "claim_id": value["claims"][0]["claim_id"]}
    ]


@pytest.mark.parametrize("ids", [["F001"], ["F002"], ["F003"], []])
def test_source_membership_is_not_a_semantic_support_override(ids):
    value = private_draft(ids=ids)
    if not ids:
        with pytest.raises(ValueError, match="SELECTION_REQUIRED"):
            transport.compile_draft(value, sources())
        return
    public, provenance = transport.compile_draft(value, sources())
    assert provenance["semantic_support_certified"] is False
    if ids:
        negative = authored_claims(provenance)
        negative["claims"][0]["status"] = "partial"
        negative["claims"][0]["proof_audit"].update(
            all_predicates_entailed=False,
            actor_identity_preserved=False,
            conditions_preserved=False,
            causal_bridges_entailed=False,
            missing_predicates=[
                "Own selected union lacks at least one required actor, condition or causal bridge"
            ],
        )
        assert negative["claims"][0]["status"] == "partial"
        # Valid negative remains unchanged; ordinary body support gate rejects it.
        assert transport.assess_judgment(negative, provenance) == []


@pytest.mark.parametrize(
    "changes",
    [
        {"answer_mode": "general_knowledge"},
        {"mode": "benchmark_openqa"},
        {"condition": "E0"},
        {"reading_context": {"text": "reading"}},
        {"source_relation_policy": "source_relation_v2"},
        {"joint_checker_policy": "typed_joint_v10"},
        {"teaching_context": {"teaching_mode": "hint"}},
        {"teaching_context": {"turn_role": "learner_attempt"}},
        {"teaching_context": {"practice_context": {"id": "p"}}},
    ],
)
def test_private_policy_does_not_escape_ordinary_direct_textbook_scope(changes):
    request = request_fixture(**changes)
    teaching = {
        "teaching_mode": (request.teaching_context or {}).get("teaching_mode", "direct"),
        "online_check": True,
    }
    with pytest.raises(ValueError, match="INCOMPATIBLE"):
        transport.eligible(request, teaching)


def request_fixture(**changes):
    values = dict(
        request_id="phase161-authored",
        mode="interactive_chat",
        condition="E1",
        question="Under what condition does the paired transport occur?",
        enhancement_version="learning_enhancement_v1",
        reliability_policy="evidence_reliability_v5",
        checker_payload_policy="lossless_checker_tables_v1",
        assertion_source_policy=transport.POLICY,
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
        ),
    )
    values.update(changes)
    return GenerationRequest(**values)


def test_old_requests_remain_opt_out_and_current_lossless_checker_route_eligible():
    request = request_fixture()
    assert transport.eligible(request, {"teaching_mode": "direct", "online_check": True}) is True
    request.assertion_source_policy = None
    assert transport.eligible(request, {"teaching_mode": "direct", "online_check": True}) is False
    request.assertion_source_policy = "unknown-private-policy"
    with pytest.raises(ValueError, match="UNKNOWN"):
        transport.eligible(request, {"teaching_mode": "direct", "online_check": True})


class ScriptedTransport:
    def __init__(self, values):
        self.values = iter(values)
        self.calls = []

    def generate(self, messages, **kwargs):
        self.calls.append((deepcopy(messages), deepcopy(kwargs)))
        value = next(self.values)
        if callable(value):
            value = value(messages)
        if isinstance(value, ProviderResult):
            return value
        return ProviderResult(
            raw_text=value if isinstance(value, str) else json.dumps(value),
            finish_reason="stop",
            provider="deliberately_scripted_offline",
            model="captured_or_authored_fixture",
            request_submitted=True,
        )


def decode_packet(messages):
    data = json.loads(messages[-1]["content"])
    if "CHECKER_INPUT_ENCODING" in data:
        data = decode(data)
    if "SOURCE_FRAGMENT_TABLE" in data:
        table = data.pop("SOURCE_FRAGMENT_TABLE")
        data["SOURCE_FRAGMENTS"] = [
            dict(zip(table["columns"], row, strict=True)) for row in table["rows"]
        ]
    return data


def mapped_request(**changes):
    evidence, maps = [], {}
    for number, row in enumerate(sources(), 1):
        text, chunk, unit = row["exact_text"], f"chunk-{number}", f"unit-{number}"
        evidence.append(
            {
                "evidence_id": row["evidence_id"],
                "chunk_id": chunk,
                "asset_id": f"asset-{number}",
                "processing_id": "authored-processing",
                "source_title": "Authored transport fixture",
                "section": "Bounded conditions",
                "pages": [number],
                "locator": f"Authored page {number}",
                "text": text,
                "text_hash": sha(text),
                "context_order": number,
            }
        )
        maps[chunk] = {
            "document_version_id": "authored-version",
            "processing_id": "authored-processing",
            "asset_id": f"asset-{number}",
            "chunk_text": text,
            "chunk_hash": sha(text),
            "units": [
                {
                    "id": unit,
                    "page": number,
                    "cleaned_text": text,
                    "text_hash": sha(text),
                    "blocks": [{"start": 0, "end": len(text), "kind": "prose"}],
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
    return request_fixture(evidence=evidence, source_map=maps, **changes)


def authored_full_checker(messages, defect=None):
    """Control verdicts only exercise service guards, not a semantic evaluator."""
    packet = decode_packet(messages)
    proofs = packet["ASSERTION_PROOFS"]["assertions"]
    banks = {row["fragment_id"]: row for row in packet["SOURCE_FRAGMENTS"]}
    rows = []
    for proof in proofs:
        selected = proof["selected_source_union"]
        grouped = {}
        for source in selected:
            bank = banks[source["fragment_id"]]
            assert (bank["evidence_id"], bank["exact_text"]) == (
                source["evidence_id"],
                source["exact_text"],
            )
            assert source["text_sha256"] == sha(source["exact_text"])
            grouped.setdefault(source["evidence_id"], []).append(source["fragment_id"])
        rows.append(
            {
                "claim_id": proof["claim_id"],
                "basis": "textbook",
                "status": "supported",
                "reason": "Authored offline fixture, not measured semantic accuracy.",
                "citations": [
                    {"evidence_id": eid, "fragment_ids": ids, "relation": "supporting"}
                    for eid, ids in grouped.items()
                ],
                "proof_audit": {
                    "all_predicates_entailed": True,
                    "actor_identity_preserved": True,
                    "conditions_preserved": True,
                    "causal_bridges_entailed": True,
                    "missing_predicates": [],
                    "reason": "Authored fixture gate label.",
                },
            }
        )
    source = proofs[0]["selected_source_union"][0]
    result = {
        "claims": rows,
        "body_ok": True,
        "specific_help": True,
        "scope_ok": True,
        "suggestions_ok": True,
        "evidence_display_ok": True,
        "cumulative_ok": True,
        "complete_answer": True,
        "coverage": "full",
        "missing_facets": [],
        "limitations_explicit": True,
        "reason": "Authored offline contract test only.",
        "repair_fragment_ids": [],
        "attempt_evaluation_ok": "not_applicable",
        "tutor_question_ok": True,
        "requirements": [
            {
                "requirement_id": point["id"],
                "relevance": "related",
                "sufficiency": "sufficient",
                "evidence": [
                    {
                        "evidence_id": source["evidence_id"],
                        "fragment_id": source["fragment_id"],
                        "quote": source["exact_text"],
                    }
                ],
                "conditions_preserved": True,
                "response_coverage": "covered",
                "missing_information": "",
                "reason": "Authored requirements label only.",
            }
            for point in packet["CONTEXT_COVERAGE"]["requirements"]
        ],
        "non_repetitive_next_action": True,
    }
    if defect in {"conditions_preserved", "actor_identity_preserved", "causal_bridges_entailed"}:
        rows[0]["proof_audit"][defect] = False
    elif defect == "contradiction":
        rows[0]["citations"][0]["relation"] = "contradictory"
    elif defect == "wrong_parent":
        rows[0]["citations"][0]["fragment_ids"] = ["F003"]
    elif defect == "other_assertion":
        rows[0]["citations"].append(deepcopy(rows[1]["citations"][0]))
    elif defect == "negative_status":
        rows[0].update(status="partial", reason="Authored missing causal bridge.")
        rows[0]["proof_audit"].update(
            causal_bridges_entailed=False,
            missing_predicates=["A required causal bridge is absent from the selected union"],
        )
        result["body_ok"] = False
    elif defect == "missing_audit":
        del rows[0]["proof_audit"]
    elif defect == "duplicate_claim":
        result["claims"].append(deepcopy(rows[0]))
    return result


def test_real_generation_service_compiles_whole_assertions_then_checks_the_exact_union():
    request = mapped_request()
    before = deepcopy(request)
    adapter = ScriptedTransport([private_draft(extra=True, short=True), authored_full_checker])
    events = []
    out = GenerationService(adapter).generate(request, RequestBudget(max_calls=2), events.append)
    assert out.succeeded, out.error
    assert request == before and len(adapter.calls) == out.budget["consumed_calls"] == 2
    assert [row["stage"] for row in out.attempts] == ["generation", "joint_check"]
    assert out.budget["format_repairs"] == out.budget["transient_retries"] == 0
    assert len(events) == 4 and [row["phase"] for row in events] == [
        "start",
        "finish",
        "start",
        "finish",
    ]
    generation_context = next(
        json.loads(row["content"].split("\n", 1)[1])
        for row in adapter.calls[0][0]
        if row["content"].startswith("CONTEXT_DATA_JSON:")
    )
    packet = decode_packet(adapter.calls[1][0])
    original_bank = {
        row["source_id"]: row
        for row in transport.decode_generation_source_bank(
            {
                key: generation_context[key]
                for key in (
                    "ASSERTION_SOURCE_BANK",
                    "ASSERTION_SOURCE_LOCATORS",
                    "GENERATION_INPUT_ENCODING",
                )
            }
        )
    }
    stored = out.drafts[0]["assertion_provenance"]
    assert [row["assertion_id"] for row in stored["assertions"]] == ["A001", "A002", "S001"]
    for proof in packet["ASSERTION_PROOFS"]["assertions"]:
        for source in proof["selected_source_union"]:
            original = original_bank[source["fragment_id"]]
            assert source["exact_text"] == original["exact_text"]
            assert source["evidence_id"] == original["evidence_id"]
            assert source["text_sha256"] == original["text_sha256"]
    assert out.response["answer_text"] == "\n\n".join(
        row["rendered_text"] for row in stored["assertions"] if row["answer_field"] == "answer_text"
    )
    assert out.response["short_answer"] == stored["assertions"][-1]["rendered_text"]
    assert out.response["citations"] == ["ev_001", "ev_002", "ev_003"]
    assert out.checks[0]["assertion_proof_audit"]["issues"] == []


@pytest.mark.parametrize(
    "defect",
    [
        "conditions_preserved",
        "actor_identity_preserved",
        "causal_bridges_entailed",
        "contradiction",
        "wrong_parent",
        "other_assertion",
        "negative_status",
        "missing_audit",
        "duplicate_claim",
    ],
)
def test_service_negative_or_malformed_check_never_publishes_or_retries(defect):
    request = mapped_request()
    adapter = ScriptedTransport(
        [private_draft(extra=True), lambda messages: authored_full_checker(messages, defect)]
    )
    out = GenerationService(adapter).generate(request, RequestBudget(max_calls=4))
    assert out.response is None and out.delivered_projection == {}
    assert out.error is not None
    assert len(adapter.calls) == out.budget["consumed_calls"] == 2
    assert out.budget["format_repairs"] == out.budget["transient_retries"] == 0
    assert all(not row["published"] for row in out.drafts)


@pytest.mark.parametrize(
    "value",
    ["not valid json", '{"schema_version": "chat_response_v1"}', {"error": "wrong private shape"}],
)
def test_service_private_format_failure_does_not_issue_a_format_repair(value):
    adapter = ScriptedTransport([value])
    out = GenerationService(adapter).generate(mapped_request(), RequestBudget(max_calls=4))
    assert out.response is None and out.error is not None
    assert len(adapter.calls) == out.budget["consumed_calls"] == 1
    assert out.budget["format_repairs"] == out.budget["transient_retries"] == 0


def test_service_private_transient_error_is_terminal_without_automatic_retry():
    result = ProviderResult(
        error={
            "code": "RATE_LIMITED",
            "message": "Authored retryable transport fault",
            "retryable": True,
            "details": {},
        },
        provider="deliberately_scripted_offline",
        model="fixture",
        request_submitted=True,
    )
    adapter = ScriptedTransport([result])
    out = GenerationService(adapter).generate(mapped_request(), RequestBudget(max_calls=4))
    assert out.response is None and out.error["code"] == "RATE_LIMITED"
    assert len(adapter.calls) == out.budget["consumed_calls"] == 1
    assert out.budget["transient_retries"] == 0


@pytest.mark.parametrize("case_id", ["Q01", "Q02"])
def test_generation_service_replays_exact_captured_body_sources_and_checker_to_original_failure(
    case_id,
):
    """Reconstruct only in-memory mapping metadata; captured selected text is exact."""
    case = CASES[case_id]
    maps = {}
    for evidence in case["selected_evidence"]:
        text, chunk = evidence["text"], evidence["chunk_id"]
        unit = f"offline-selected-{evidence['evidence_id']}"
        blocks, cursor = [], 0
        for source in case["checker_packet"]["SOURCE_FRAGMENTS"]:
            if source["evidence_id"] != evidence["evidence_id"]:
                continue
            start = text.find(source["exact_text"], cursor)
            assert start >= 0
            cursor = start + len(source["exact_text"])
            blocks.append({"start": start, "end": cursor, "kind": source["block_kind"]})
        maps[chunk] = {
            "document_version_id": "offline-captured-selected-version",
            "processing_id": evidence["processing_id"],
            "asset_id": evidence["asset_id"],
            "chunk_text": text,
            "chunk_hash": sha(text),
            "units": [
                {
                    "id": unit,
                    "page": evidence["pages"][0],
                    "cleaned_text": text,
                    "text_hash": sha(text),
                    "blocks": blocks,
                }
            ],
            "spans": [
                {
                    "unit_id": unit,
                    "page": evidence["pages"][0],
                    "start": 0,
                    "end": len(text),
                    "chunk_start": 0,
                    "chunk_end": len(text),
                }
            ],
        }
    coverage = case["checker_packet"]["CONTEXT_COVERAGE"]
    understanding = {
        "required_knowledge": [
            {
                key: row[key]
                for key in (
                    "id",
                    "request",
                    "origin",
                    "conditions",
                    "objects",
                    "relation",
                    "intent",
                )
                if key in row
            }
            for row in coverage["requirements"]
        ]
    }
    request = request_fixture(
        request_id=f"offline-original-{case_id}",
        question=case["question"],
        assertion_source_policy=None,
        generation_context_policy="legacy_context_v1",
        evidence=deepcopy(case["selected_evidence"]),
        source_map=maps,
        teaching_context=deepcopy(case["prepared_context"]["teaching_context"]),
        understanding=understanding,
        config=ModelConfig(
            provider="openai",
            model="gpt-6-luna",
            temperature=None,
            token_limit_parameter="max_completion_tokens",
            window_tokens=65536,
            tokenizer_provider="tiktoken",
            tokenizer_name="o200k_base",
            token_count_fallback="error",
        ),
    )

    def exact_captured_checker(messages):
        packet = decode_packet(messages)
        assert "ASSERTION_PROOFS" not in packet
        assert packet["CLAIMS"] == case["checker_packet"]["CLAIMS"]
        assert packet["SOURCE_FRAGMENTS"] == case["checker_packet"]["SOURCE_FRAGMENTS"]
        assert (
            packet["ACTUAL_CITATION_BINDINGS"] == case["checker_packet"]["ACTUAL_CITATION_BINDINGS"]
        )
        return case["original_checker_raw"]

    adapter = ScriptedTransport([case["original_draft_raw"], exact_captured_checker])
    before = deepcopy(case)
    out = GenerationService(adapter).generate(request, RequestBudget(max_calls=2))
    assert out.response is None and out.error["code"] == "SEMANTIC_CHECK_FAILED", out.error
    assert out.drafts[0]["raw_model_output"] == case["original_draft_raw"]
    assert (
        out.drafts[0]["response"]["answer_text"]
        == json.loads(case["original_draft_raw"])["answer_text"]
    )
    assert (
        out.checks[0]["typed_judgment_raw_aliases"]
        == OrdinaryQuestionCheckV5.model_validate(
            json.loads(case["original_checker_raw"])
        ).model_dump()
    )
    assert out.delivered_projection == {} and not out.drafts[0]["published"]
    assert len(adapter.calls) == out.budget["consumed_calls"] == 2
    assert out.budget["format_repairs"] == out.budget["transient_retries"] == 0
    assert case == before and case["original_native_failure"]["answer_id"] is None


@pytest.mark.parametrize("task_type", ["simple_calculation", "concept_comparison"])
def test_private_source_producer_and_consumer_skip_nonprocess_tasks(task_type):
    settings = SimpleNamespace(
        chat_joint_checker_policy="typed_joint_v5",
        chat_source_relation_policy="off",
        chat_checker_schema_policy=None,
        chat_checker_output_policy=None,
        chat_qualification_transport_policy="off",
    )
    teaching = {"turn_role": "user_question", "teaching_mode": "direct", "task_type": task_type}
    assert (
        transport.submission_fields(
            settings,
            answer_mode="textbook",
            teaching=teaching,
            reading_context=None,
            provider="openai",
            checker_provider="openai",
        )
        == {}
    )
    request = request_fixture(teaching_context=teaching)
    with pytest.raises(ValueError, match="INCOMPATIBLE"):
        transport.eligible(
            request, {"teaching_mode": "direct", "online_check": True, "task_type": task_type}
        )


def test_private_short_answer_cannot_introduce_a_source_not_bound_to_the_body():
    value = private_draft(ids=["F001"])
    value["short_answer"] = {
        "assertion_id": "S001",
        "text": "A symporter carries two substances in the same direction.",
        "source_ids": ["F003"],
    }
    value["citations"] = ["ev_001", "ev_003"]
    with pytest.raises(ValueError):
        transport.compile_draft(value, sources())


@pytest.mark.parametrize("status", ["partial", "unsupported"])
def test_private_negative_status_with_all_positive_audits_is_contract_error_without_rewrite(status):
    _, provenance, _ = compiled()
    value = authored_claims(provenance)
    value["claims"][0]["status"] = status
    before = deepcopy(value)
    assert transport.assess_judgment(value, provenance)
    assert value == before


@pytest.mark.parametrize("missing", [[""], [" "], ["x" * 1001]])
def test_missing_predicate_labels_are_bounded_nonblank_strings(missing):
    from generation.assertion_provenance_v1 import ProofAudit

    audit = authored_claims(compiled()[1])["claims"][0]["proof_audit"]
    audit["missing_predicates"] = missing
    with pytest.raises(ValidationError):
        ProofAudit.model_validate(audit)


def test_private_projection_displays_every_selected_fragment_in_a_three_part_proof():
    """Source views must display the immutable selected union, not lexical top-two."""
    parts = [
        "Transporter T carries sodium and glucose.",
        "When valve A is open, sodium moves downhill through transporter T.",
        "This sodium movement supplies energy to move attached glucose uphill through transporter T.",
    ]
    text = "\n\n".join(parts)
    blocks, cursor = [], 0
    for part in parts:
        start = text.find(part, cursor)
        cursor = start + len(part)
        blocks.append({"start": start, "end": cursor, "kind": "prose"})
    evidence = [
        {
            "evidence_id": "ev_001",
            "chunk_id": "three-part",
            "asset_id": "authored-three-part",
            "processing_id": "authored-processing",
            "source_title": "Authored three-part proof",
            "section": "Whole assertion",
            "pages": [1],
            "locator": "Authored page 1",
            "text": text,
            "text_hash": sha(text),
            "context_order": 1,
            "source_url": None,
            "license": None,
            "inherited_from": None,
        }
    ]
    mapping = {
        "document_version_id": "authored-version",
        "processing_id": "authored-processing",
        "asset_id": "authored-three-part",
        "chunk_text": text,
        "chunk_hash": sha(text),
        "units": [
            {
                "id": "three-part-unit",
                "page": 1,
                "cleaned_text": text,
                "text_hash": sha(text),
                "blocks": blocks,
            }
        ],
        "spans": [
            {
                "unit_id": "three-part-unit",
                "page": 1,
                "start": 0,
                "end": len(text),
                "chunk_start": 0,
                "chunk_end": len(text),
            }
        ],
    }
    request = request_fixture(evidence=evidence, source_map={"three-part": mapping})
    draft = private_draft(
        text="When valve A is open, transporter T uses downhill sodium movement to supply energy for attached glucose to move uphill.",
        ids=["F001", "F002", "F003"],
    )
    draft["citations"] = ["ev_001"]
    adapter = ScriptedTransport([draft, authored_full_checker])
    out = GenerationService(adapter).generate(request, RequestBudget(max_calls=2))
    assert out.succeeded, out.error
    generation_context = next(
        json.loads(row["content"].split("\n", 1)[1])
        for row in adapter.calls[0][0]
        if row["content"].startswith("CONTEXT_DATA_JSON:")
    )
    assert generation_context["CURRENT_EVIDENCE"] == evidence
    generation_bank = transport.decode_generation_source_bank(
        {
            key: generation_context[key]
            for key in (
                "ASSERTION_SOURCE_BANK",
                "ASSERTION_SOURCE_LOCATORS",
                "GENERATION_INPUT_ENCODING",
            )
        }
    )
    assert [row["exact_text"] for row in generation_bank] == parts
    proof = out.drafts[0]["assertion_provenance"]["assertions"][0]
    selected_ids = [row["fragment_id"] for row in proof["sources"]]
    view = out.delivered_projection["citation_views"][0]
    assert len(selected_ids) == 3 and view["fragment_ids"] == selected_ids
    assert view["disclosure"] == "precise_excerpt"
    assert view["preview"] == "\n\u2026\n".join(parts)
    highlighted = [row for row in view["segments"] if row["highlight"]]
    assert [row["text"] for row in highlighted] == parts
    assert [row["fragment_ids"][0] for row in highlighted] == selected_ids
    assert view["available_actions"] == ["full_source"]
    assert out.token_budget["evidence_tokens"] <= 3000
    assert out.budget["consumed_calls"] == 2
