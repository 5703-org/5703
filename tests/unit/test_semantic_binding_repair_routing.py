"""Generic offline controls of existing typed V5 content-vs-contract routing."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket

import pytest

from generation import GenerationRequest, GenerationService, ModelConfig, RequestBudget
from generation import checker_claim_anchors_v3 as compact
from generation.adapters import LLMAdapter, ProviderResult, chat_value
from generation.checker_encoding import decode


SAFE = "The monitor displays temperature in degrees Celsius [ev_001]."
BAD = "The indicator is green when the signal is high [ev_002]."


@pytest.fixture(autouse=True)
def no_external_io(monkeypatch):
    attempted = []

    def deny(*args, **kwargs):
        attempted.append(True)
        raise AssertionError("Routing controls cannot access network/provider/DB")

    for name in ("connect", "connect_ex"):
        monkeypatch.setattr(socket.socket, name, deny)
    monkeypatch.setattr(socket, "getaddrinfo", deny)
    monkeypatch.setattr(LLMAdapter, "_call", deny)
    from sqlalchemy.engine import Engine

    monkeypatch.setattr(Engine, "connect", deny)
    yield
    assert not attempted


def request(policy, relation):
    texts = [
        "The monitor displays temperature in degrees Celsius.",
        "The indicator flashes twice on startup."
        if relation == "irrelevant"
        else "The indicator is red when the signal is high.",
    ]
    evidence, maps = [], {}
    for i, text in enumerate(texts, 1):
        digest = hashlib.sha256(text.encode()).hexdigest()
        chunk, unit = f"chunk-{i}", f"unit-{i}"
        evidence.append(
            dict(
                evidence_id=f"ev_{i:03d}",
                chunk_id=chunk,
                asset_id="authored",
                processing_id="authored",
                source_title="Authored device record",
                section="Operation",
                pages=[i],
                locator="Authored",
                text=text,
                text_hash=digest,
                context_order=i,
            )
        )
        maps[chunk] = dict(
            document_version_id="v1",
            processing_id="authored",
            asset_id="authored",
            chunk_text=text,
            chunk_hash=digest,
            units=[dict(id=unit, page=i, cleaned_text=text, text_hash=digest)],
            spans=[
                dict(
                    unit_id=unit, page=i, start=0, end=len(text), chunk_start=0, chunk_end=len(text)
                )
            ],
        )
    return GenerationRequest(
        request_id="generic-device-routing",
        mode="interactive_chat",
        condition="E1",
        question="Describe the monitor display and indicator behavior.",
        evidence=evidence,
        source_map=maps,
        config=ModelConfig(tokenizer_provider="estimate"),
        enhancement_version="learning_enhancement_v1",
        reliability_policy="evidence_reliability_v5",
        checker_claim_policy=policy,
        repair_policy="claim_patch_repair_v3"
        if policy is None
        else "claim_patch_citation_coordination_v4",
        teaching_context={"teaching_mode": "direct", "help_level": 0, "turn_role": "user_question"},
    )


def packet_from(messages):
    values = []
    for message in messages:
        try:
            value = json.loads(message["content"])
        except (ValueError, TypeError):
            continue
        if isinstance(value, dict) and "CLAIMS" in value and "ACTUAL_CITATION_BINDINGS" in value:
            values.append(value)
    assert len(values) == 1
    packet = values[0]
    if "CHECKER_INPUT_ENCODING" in packet:
        packet = decode(packet)
    if "SOURCE_FRAGMENT_TABLE" in packet:
        table = packet.pop("SOURCE_FRAGMENT_TABLE")
        packet["SOURCE_FRAGMENTS"] = [
            dict(zip(table["columns"], row, strict=True)) for row in table["rows"]
        ]
    return packet


def judgment(messages, policy, relation, *, initial, defect=None, final_partial=False):
    packet = packet_from(messages)
    bindings = {b["claim_id"]: b["citations"] for b in packet["ACTUAL_CITATION_BINDINGS"]}
    claims = []
    for original in packet["CLAIMS"]:
        negative = initial and "green" in original["text"]
        refs = [
            dict(
                evidence_id=b["evidence_id"],
                fragment_ids=b["allowed_fragment_ids"],
                relation=relation if negative else "supporting",
            )
            for b in bindings[original["claim_id"]]
        ]
        claims.append(
            dict(
                claim_id=original["claim_id"],
                basis="textbook",
                status="partial" if negative else "supported",
                citations=refs,
                reason="Authored contract fixture; not a measured model verdict.",
            )
        )
    negative = initial
    result = dict(
        claims=claims,
        body_ok=not negative,
        specific_help=True,
        scope_ok=True,
        suggestions_ok=True,
        evidence_display_ok=True,
        cumulative_ok=True,
        complete_answer=True,
        coverage="supported_partial" if negative or final_partial else "full",
        missing_facets=["The current indicator statement lacks its own relevant support."]
        if negative or final_partial
        else [],
        limitations_explicit=False,
        reason="Authored metadata control.",
        repair_fragment_ids=[f["fragment_id"] for f in packet["SOURCE_FRAGMENTS"]],
        attempt_evaluation_ok="not_applicable",
        tutor_question_ok=True,
        non_repetitive_next_action=True,
        requirements=[
            dict(
                requirement_id=r["id"],
                relevance="related",
                sufficiency="sufficient",
                evidence=[
                    dict(
                        evidence_id=f["evidence_id"],
                        fragment_id=f["fragment_id"],
                        quote=f["exact_text"],
                    )
                    for f in packet["SOURCE_FRAGMENTS"]
                ],
                conditions_preserved=True,
                response_coverage="covered",
                missing_information="",
                reason="Authored source coverage.",
            )
            for r in packet["CONTEXT_COVERAGE"]["requirements"]
        ],
    )
    if defect == "quote":
        result["requirements"][0]["evidence"][0]["quote"] = "An invented source quotation."
    if defect == "identity":
        result["claims"][0]["claim_id"] = "foreign-identity"
    if defect == "source":
        result["claims"][-1]["citations"][0]["fragment_ids"] = ["FOREIGN"]
    if policy is None:
        return result
    by_id = {c["claim_id"]: c for c in claims}
    primitive = {
        k: v for k, v in result.items() if k not in {"claims", "requirements", "body_ok", "reason"}
    }
    primitive.update(version=compact.POLICY, claims={}, requirements={})
    for key, target in packet[compact.CLAIM_TARGETS].items():
        # A foreign identity is represented by a foreign required-slot key in
        # this existing experimental wire; it is never silently resolved.
        original = next(c for c in packet["CLAIMS"] if c["claim_id"] == target["claim_id"])
        row = deepcopy(by_id.get(target["claim_id"], result["claims"][0]))
        row.pop("claim_id")
        row.pop("reason")
        row["unestablished_quote"] = (
            "green when the signal is high" if initial and "green" in original["text"] else ""
        )
        if defect == "witness" and row["status"] == "partial":
            row["unestablished_quote"] = "invented defect"
        if defect == "optimistic" and row["status"] == "partial":
            row["status"] = "supported"
        primitive["claims"]["FOREIGN" if defect == "identity" and key == "C1" else key] = row
    for key, target in packet[compact.REQUIREMENT_TARGETS].items():
        row = deepcopy(
            next(
                r for r in result["requirements"] if r["requirement_id"] == target["requirement_id"]
            )
        )
        row.pop("requirement_id")
        primitive["requirements"][key] = row
    return primitive


class AuthoredTransport:
    def __init__(
        self,
        policy,
        relation,
        *,
        positive=False,
        defect=None,
        final_partial=False,
        final_negative=False,
    ):
        self.policy, self.relation = policy, relation
        self.positive, self.defect = positive, defect
        self.final_partial, self.final_negative = final_partial, final_negative
        self.calls = []

    def generate(self, messages, **kwargs):
        self.calls.append((deepcopy(messages), kwargs))
        purpose = kwargs["request_context"]["purpose"]
        replacement = (
            "The indicator flashes twice on startup [ev_002]."
            if self.relation == "irrelevant"
            else "The indicator is red when the signal is high [ev_002]."
        )
        if purpose == "generation":
            value = chat_value(
                "answer",
                SAFE + " " + (replacement if self.positive else BAD),
                citations=["ev_001", "ev_002"],
            )
        elif purpose == "semantic_repair":
            data = json.loads(messages[-1]["content"].split("REPAIR_DATA_JSON:\n", 1)[1])
            assert any(c["text"] == SAFE for c in data["protected_exact_claims"])
            value = dict(
                edits=[
                    dict(claim_id=c["claim_id"], replacement_text=replacement)
                    for c in data["original_claims"]
                    if c["claim_id"] in data["editable_claim_ids"]
                ],
                append_answer_text="",
            )
        else:
            initial = not self.positive and purpose != "joint_recheck"
            value = judgment(
                messages,
                self.policy,
                self.relation,
                initial=initial,
                defect=self.defect,
                final_partial=self.final_partial and not initial,
            )
            if self.final_negative and not initial:
                if self.policy is None:
                    value["claims"][-1]["status"] = "partial"
                    value["body_ok"] = False
                else:
                    row = value["claims"][next(reversed(value["claims"]))]
                    row.update(status="partial", unestablished_quote="indicator")
        return ProviderResult(
            raw_text=json.dumps(value),
            finish_reason="stop",
            provider="authored_offline",
            model="authored",
            request_submitted=True,
        )


def run(policy, relation="irrelevant", **kwargs):
    adapter = AuthoredTransport(policy, relation, **kwargs)
    out = GenerationService(adapter).generate(request(policy, relation), RequestBudget())
    return out, adapter


@pytest.mark.parametrize("policy", [None, compact.POLICY])
@pytest.mark.parametrize("relation", ["irrelevant", "contradictory"])
def test_valid_semantic_binding_negative_reaches_content_repair_and_entire_final_check(
    policy, relation
):
    out, adapter = run(policy, relation)
    assert out.succeeded, out.error
    assert len(adapter.calls) == out.budget["consumed_calls"] == 4
    assert [a["stage"] for a in out.attempts] == [
        "generation",
        "joint_check",
        "semantic_repair",
        "joint_recheck",
    ]
    route = out.checks[0]["semantic_negative_routing"]
    assert (
        route["route"] == "semantic_repair"
        and not route["judgment_changed"]
        and not route["publication_override"]
    )
    assert any(i["code"] == "ACTUAL_CITATION_" + relation.upper() for i in route["semantic_issues"])
    assert SAFE in out.response["answer_text"] and "green" not in out.response["answer_text"]


@pytest.mark.parametrize("policy", [None, compact.POLICY])
def test_ordinary_positive_keeps_two_call_fast_checked_path(policy):
    out, adapter = run(policy, positive=True)
    assert out.succeeded, out.error
    assert len(adapter.calls) == out.budget["consumed_calls"] == 2


@pytest.mark.parametrize(
    "policy,defect",
    [
        (None, "identity"),
        (None, "source"),
        (None, "quote"),
        (compact.POLICY, "identity"),
        (compact.POLICY, "source"),
        (compact.POLICY, "quote"),
        (compact.POLICY, "witness"),
        (compact.POLICY, "optimistic"),
    ],
)
def test_real_contract_or_contradictory_metadata_cannot_be_routed_to_false_success(policy, defect):
    out, adapter = run(policy, defect=defect)
    assert out.response is None and out.error is not None
    assert len(adapter.calls) == out.budget["consumed_calls"] <= 4
    assert "semantic_repair" not in [a["stage"] for a in out.attempts]


@pytest.mark.parametrize("policy", [None, compact.POLICY])
@pytest.mark.parametrize("final", ["partial_without_limit", "negative"])
def test_final_partial_limit_or_support_failure_still_blocks_publication_at_four(policy, final):
    out, adapter = run(
        policy, final_partial=final == "partial_without_limit", final_negative=final == "negative"
    )
    assert out.response is None and out.error is not None
    assert len(adapter.calls) == out.budget["consumed_calls"] == 4


def test_actual_imports_are_candidate_and_existing_schema_modules_remain_external_to_patch():
    from generation import checked

    root = Path(__file__).resolve().parents[2]
    assert Path(checked.__file__).resolve().is_relative_to(root)
