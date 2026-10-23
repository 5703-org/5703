"""Source-combination integration in disposable PostgreSQL; authored judgments.

The normal worker, GenerationService, storage and HTTP paths run unchanged.
Script replaces only model transport; this is not an online quality measurement.
"""

from copy import deepcopy
import hashlib
import json

import pytest
from sqlalchemy import func, select

from app.modules.answering import service
from app.modules.answering.models import Answer, AnswerRequest
from app.modules.learning_state.models import PrivateAnswerDraft
from generation import GenerationService
from generation import checked
from generation.claim_feedback_transport_v1 import HEADER, decode_claim_feedback
from generation.local_repair import VERSION as REPAIR
from generation.repair_context import CONTEXT_PREFIX, restore_source_text
from generation.source_evidence_combinations_v1 import VERSION as COMBINATIONS
from generation.source_relations_v2 import VERSION as RELATIONS
from tests.integration.test_chat_runtime import call, corpus, session, submit
from tests.integration.test_source_relation_correction_runtime import (
    authored_unit_check,
    input_data,
)
from tests.unit.test_enhancement_generation import Script, answer


ORIGINAL_CLAIM = (
    "Photosynthesis uses light to convert carbon dioxide and water into sugars. [ev_001]"
)
REPLACEMENT_CLAIM = (
    "Light supplies energy to convert carbon dioxide and water into sugars. [ev_001]"
)
PROTECTED_CLAIM = "Oxygen is released. [ev_001]"
PARTIAL_REASON = "Authored selected-source gap; retain partial until the complete final check."
FINAL_PARTIAL_REASON = (
    "Authored final partial remains a publication blocker after local supplementation."
)
SCHEMA = "joint_check_source_relations_v2"


def repair_data(messages, codec_inputs):
    payload = json.loads(messages[-1]["content"].split("REPAIR_DATA_JSON:\n", 1)[1])
    context = next(
        json.loads(row["content"][len(CONTEXT_PREFIX) :])
        for row in messages
        if row["content"].startswith(CONTEXT_PREFIX)
    )
    if HEADER in payload:
        # Only this authored test decodes the trusted producer's exact wrapper.
        payload = decode_claim_feedback(
            payload,
            encoded=True,
            **codec_inputs,
        )
    if "source_ref_version" in payload:
        payload = restore_source_text(payload, messages, context["CURRENT_EVIDENCE"])
    return payload


def select_exact_source(value, data, claim_index, text):
    row = value["claims"][claim_index]
    binding = next(
        item for item in data["ACTUAL_CITATION_BINDINGS"] if item["claim_id"] == row["claim_id"]
    )
    allowed = {fid for item in binding["citations"] for fid in item["allowed_fragment_ids"]}
    source = next(
        fragment
        for fragment in data["SOURCE_FRAGMENTS"]
        if text in fragment["exact_text"] and fragment["fragment_id"] in allowed
    )
    assert source["complete_block"]
    row["citations"] = [
        {
            "evidence_id": source["evidence_id"],
            "fragment_ids": [source["fragment_id"]],
            "relation": "supporting",
        }
    ]
    for unit in row["units"]:
        unit["fragment_ids"] = [source["fragment_id"]]
    return source


@pytest.mark.parametrize(
    "negative", [False, True], ids=["combined-supported", "honest-final-partial"]
)
def test_source_combination_survives_real_worker_storage_and_http(runtime, monkeypatch, negative):
    rt = runtime
    corpus(rt)
    rt.settings.chat_source_relation_policy = RELATIONS
    rt.settings.chat_query_preparation_policy = "anchored_reference_v14"
    rt.settings.model_window_tokens = 32768
    rt.settings.max_provider_calls = 4
    expected = {}
    codec_inputs = {}
    original_encoder = checked.encode_claim_feedback

    def observe_encoder(feedback, **kwargs):
        codec_inputs.clear()
        codec_inputs.update(deepcopy(kwargs))
        return original_encoder(feedback, **kwargs)

    monkeypatch.setattr(checked, "encode_claim_feedback", observe_encoder)

    def selection_gap(messages):
        data = input_data(messages)
        value = authored_unit_check(messages)
        assert len(value["claims"]) == 2
        row = value["claims"][0]
        row["units"][0].update(status="partial", reason=PARTIAL_REASON)
        select_exact_source(value, data, 1, "Oxygen is released.")
        expected.update(
            claim_id=row["claim_id"],
            unit_id=row["units"][0]["unit_id"],
            selected=list(row["units"][0]["fragment_ids"]),
        )
        return value

    def local_patch(messages):
        data = repair_data(messages, codec_inputs)
        plan = data["source_evidence_combinations"]
        assert plan["version"] == COMBINATIONS and plan["candidate_only"]
        assert not plan["publication_override"] and not plan["source_entailment_certified"]
        assert data["original_claims"][0]["text"] == ORIGINAL_CLAIM
        assert [row["text"] for row in data["protected_exact_claims"]] == [PROTECTED_CLAIM]
        assert data["editable_claim_ids"] == [expected["claim_id"]]
        proposals = [row for row in plan["proposals"] if row["claim_id"] == expected["claim_id"]]
        assert proposals and all(row["checker_status"] == "partial" for row in proposals)
        candidates = {row["fragment_id"]: row for row in data["source_repair_candidates"]}
        added = plan["candidate_fragment_ids"]
        assert added and all(fid.startswith("span_") for fid in added)
        assert all(fid in candidates for fid in added)
        assert any(
            "Light supplies energy to convert carbon dioxide and water into sugars."
            in candidates[fid]["exact_text"]
            for fid in added
        )
        for proposal in proposals:
            assert not proposal["diagnostic"]["semantic_absence_certified"]
            assert not proposal["diagnostic"]["predicate_ownership_certified"]
            for source in proposal["source_refs"]:
                if source["fragment_id"] in added:
                    exact = candidates[source["fragment_id"]]["exact_text"]
                    assert source["text_hash"] == hashlib.sha256(exact.encode("utf-8")).hexdigest()
        expected["plan"] = deepcopy(plan)
        return {
            "edits": [{"claim_id": expected["claim_id"], "replacement_text": REPLACEMENT_CLAIM}],
            "append_answer_text": "",
        }

    def complete_final_check(messages):
        data = input_data(messages)
        value = authored_unit_check(messages)
        assert [row["text"] for row in data["CLAIMS"]] == [REPLACEMENT_CLAIM, PROTECTED_CLAIM]
        select_exact_source(
            value, data, 0, "Light supplies energy to convert carbon dioxide and water into sugars."
        )
        select_exact_source(value, data, 1, "Oxygen is released.")
        if negative:
            value["claims"][0]["units"][0].update(status="partial", reason=FINAL_PARTIAL_REASON)
        return value

    transport = Script(
        [
            answer(ORIGINAL_CLAIM + " " + PROTECTED_CLAIM),
            selection_gap,
            local_patch,
            complete_final_check,
        ]
    )

    def factory(**kwargs):
        return GenerationService(transport, checker_adapter=transport, **kwargs)

    monkeypatch.setattr(service, "GenerationService", factory)
    chat = session(rt)
    receipt = submit(rt, chat, "What is photosynthesis?")
    with rt.db() as db:
        frozen = deepcopy(db.get(AnswerRequest, receipt["request_id"]).command)
    assert frozen["repair_policy"] == REPAIR
    assert frozen["source_relation_policy"] == RELATIONS
    assert rt.work()
    job = call(rt, "GET", "/jobs/" + receipt["job_id"])
    assert len(transport.calls) == 4
    assert [row[1]["request_context"]["purpose"] for row in transport.calls] == [
        "generation",
        "joint_check",
        "semantic_repair",
        "joint_recheck",
    ]
    assert transport.calls[1][1]["response_schema_name"] == SCHEMA
    assert transport.calls[2][1]["response_schema_name"] == "claim_patch_repair_v1"
    assert transport.calls[3][1]["response_schema_name"] == SCHEMA

    with rt.db() as db:
        request = db.get(AnswerRequest, receipt["request_id"])
        assert request.command == frozen
        assert request.budget["consumed_calls"] == request.budget["max_calls"] == 4
        records = list(
            db.scalars(
                select(PrivateAnswerDraft).where(
                    PrivateAnswerDraft.request_id == request.id,
                    PrivateAnswerDraft.phase == "online_check",
                )
            )
        )
        stored = sorted(
            (record.payload for record in records), key=lambda payload: payload["revision"]
        )
        assert len(stored) == 2
        assert [payload["revision"] for payload in stored] == [0, 1]
        assert [payload["checker_contract_revision"] for payload in stored] == [0, 0]
        assert stored[0]["source_evidence_combinations"] == expected["plan"]
        first_raw = stored[0]["typed_judgment_raw_aliases"]["claims"][0]["units"][0]
        assert first_raw["status"] == "partial" and first_raw["reason"] == PARTIAL_REASON
        assert first_raw["fragment_ids"] == expected["selected"]
        assert not stored[0]["source_relation_assessment"]["accepted"]
        assert not stored[1]["source_relation_assessment"]["source_entailment_locally_certified"]
        if negative:
            assert job["state"] == "failed" and job["answer_id"] is None
            assert job["error"]["code"] == "SEMANTIC_CHECK_FAILED"
            assert request.state == "error"
            assert (
                db.scalar(
                    select(func.count()).select_from(Answer).where(Answer.request_id == request.id)
                )
                == 0
            )
            assert not stored[1]["source_relation_assessment"]["accepted"]
            assert (
                stored[1]["typed_judgment_raw_aliases"]["claims"][0]["units"][0]["status"]
                == "partial"
            )
            assert (
                stored[1]["typed_judgment_raw_aliases"]["claims"][0]["units"][0]["reason"]
                == FINAL_PARTIAL_REASON
            )
            assert stored[1]["publication_block"]["stop_reason"] == "final_recheck_rejected"
        else:
            assert job["state"] == "succeeded" and job["answer_id"] is not None
            assert stored[1]["source_relation_assessment"]["accepted"]

    if not negative:
        public = call(rt, "GET", "/answers/" + job["answer_id"])
        assert public["response"]["answer_text"] == REPLACEMENT_CLAIM + " " + PROTECTED_CLAIM
        fragments = {row["fragment_id"]: row for row in public["attribution"]["fragments"]}
        for claim in stored[1]["source_relation_assessment"]["claims"]:
            for unit in claim["obligations"]:
                assert unit["fragment_ids"] == [
                    quote["fragment_id"] for quote in unit["source_quotes"]
                ]
                for quote in unit["source_quotes"]:
                    source = fragments[quote["fragment_id"]]
                    assert (quote["evidence_id"], quote["quote"]) == (
                        source["evidence_id"],
                        source["exact_text"],
                    )
        history = call(rt, "GET", "/sessions/" + chat["id"] + "/messages")
        assert history["items"][-1]["active_answer_id"] == public["id"]
        assert history["items"][-1]["answer"]["attribution"] == public["attribution"]
        assert call(rt, "GET", "/answers/" + public["id"])["attribution"] == public["attribution"]
