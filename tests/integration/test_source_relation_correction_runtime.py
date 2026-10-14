"""Real API/worker/storage with authored Script judgments; no live quality claim."""

from copy import deepcopy
import json

import pytest
from sqlalchemy import func, select

from app.modules.answering import service
from app.modules.answering.models import Answer, AnswerRequest
from app.modules.learning_state.models import PrivateAnswerDraft
from generation import GenerationService
from generation.source_relations_v2 import VERSION
from tests.integration.test_chat_runtime import call, corpus, session, submit
from tests.integration.test_learning_state import authored_requirements, checker_input
from tests.unit.test_enhancement_generation import Script, answer


SCHEMA = "joint_check_source_relations_v2"


def input_data(messages):
    """Reuse the integration decoder for original DATA during a correction turn."""
    message = next(row for row in messages if row["content"].startswith("{"))
    return checker_input([message])


def authored_unit_check(messages):
    data = input_data(messages)
    bindings = {row["claim_id"]: row["citations"] for row in data["ACTUAL_CITATION_BINDINGS"]}
    units = {row["claim_id"]: row["units"] for row in data["SOURCE_SYNTACTIC_UNITS"]}
    claims = []
    for claim in data["CLAIMS"]:
        citations = [
            {
                "evidence_id": binding["evidence_id"],
                "fragment_ids": binding["allowed_fragment_ids"][:1],
                "relation": "supporting",
            }
            for binding in bindings[claim["claim_id"]]
        ]
        assert citations and all(row["fragment_ids"] for row in citations)
        selected = [fid for citation in citations for fid in citation["fragment_ids"]]
        claims.append(
            {
                "claim_id": claim["claim_id"],
                "basis": "textbook",
                "status": "supported",
                "citations": citations,
                "units": [
                    {
                        "unit_id": unit["unit_id"],
                        "status": "supported",
                        "fragment_ids": selected,
                        "relation_preserved": True,
                        "conditions_preserved": True,
                        "reason": "Authored transport association; not a semantic quality rating.",
                    }
                    for unit in units[claim["claim_id"]]
                ],
                "reason": "Authored transport association; not a semantic quality rating.",
            }
        )
    return {
        "claims": claims,
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
        "reason": "Authored integration control, not live model or human acceptance.",
        "repair_fragment_ids": [],
        "attempt_evaluation_ok": True,
        "tutor_question_ok": True,
        "requirements": authored_requirements(data),
        "non_repetitive_next_action": True,
    }


@pytest.mark.parametrize("negative", [False, True], ids=["corrected-supported", "honest-partial"])
def test_source_relation_correction_survives_worker_storage_and_http(runtime, monkeypatch, negative):
    rt = runtime
    corpus(rt)
    rt.settings.chat_source_relation_policy = VERSION
    rt.settings.chat_query_preparation_policy = "anchored_reference_v14"
    rt.settings.model_window_tokens = 32768
    rt.settings.max_provider_calls = 3
    expected = {}

    def missing_assessment(messages):
        data = input_data(messages)
        value = authored_unit_check(messages)
        row = value["claims"][0]
        selected = {fid for citation in row["citations"] for fid in citation["fragment_ids"]}
        binding = next(b for b in data["ACTUAL_CITATION_BINDINGS"] if b["claim_id"] == row["claim_id"])
        fragments = {f["fragment_id"]: f for f in data["SOURCE_FRAGMENTS"]}
        # Inject exactly the missing claim assessment, using a permitted complete block.
        fid = next(
            fid
            for citation in binding["citations"]
            for fid in citation["allowed_fragment_ids"]
            if fid not in selected and fragments[fid]["complete_block"]
        )
        unit = row["units"][0]
        unit["fragment_ids"] = [fid]
        expected.update(
            code="RELATION_ASSESSED_FRAGMENT_MISMATCH",
            claim_id=row["claim_id"],
            unit_id=unit["unit_id"],
            fragment_id=fid,
            evidence_id=fragments[fid]["evidence_id"],
        )
        return value

    def corrected(messages):
        feedback = messages[-1]["content"]
        assert "Return the complete " + SCHEMA + " schema" in feedback
        assert "Return the complete joint_check_v5 schema." not in feedback
        issues = json.loads(feedback.split("CHECKER_CONTRACT_ISSUES_JSON:\n", 1)[1])
        assert expected in issues
        value = authored_unit_check(messages)
        if negative:
            value["claims"][0]["units"][0].update(
                status="partial", reason="Authored honest partial; do not publish this draft."
            )
        return value

    transport = Script([answer(), missing_assessment, corrected])

    def factory(**kwargs):
        return GenerationService(transport, checker_adapter=transport, **kwargs)

    monkeypatch.setattr(service, "GenerationService", factory)
    chat = session(rt)
    receipt = submit(rt, chat, "What is photosynthesis?")
    with rt.db() as db:
        frozen = deepcopy(db.get(AnswerRequest, receipt["request_id"]).command)
    assert rt.work()
    job = call(rt, "GET", "/jobs/" + receipt["job_id"])
    assert len(transport.calls) == 3
    assert [call[1]["request_context"]["purpose"] for call in transport.calls] == [
        "generation", "joint_check", "checker_contract_repair"
    ]
    assert transport.calls[1][1]["response_schema_name"] == SCHEMA
    assert transport.calls[2][1]["response_schema_name"] == SCHEMA
    assert input_data(transport.calls[1][0]) == input_data(transport.calls[2][0])

    with rt.db() as db:
        request = db.get(AnswerRequest, receipt["request_id"])
        assert request.command == frozen
        assert request.budget["consumed_calls"] == 3
        assert request.budget["max_calls"] == 3
        records = list(
            db.scalars(
                select(PrivateAnswerDraft).where(
                    PrivateAnswerDraft.request_id == request.id,
                    PrivateAnswerDraft.phase == "online_check",
                )
            )
        )
        stored = sorted((record.payload for record in records), key=lambda p: p["checker_contract_revision"])
        assert len(stored) == 2
        assert [payload["checker_contract_revision"] for payload in stored] == [0, 1]
        assert [payload["revision"] for payload in stored] == [0, 0]
        assert expected in stored[0]["checker_inconsistencies"]
        assert stored[0]["validation_state"] == "checker_inconsistent"
        assert stored[1]["checker_contract_revision"] == 1
        assert not stored[1]["source_relation_assessment"]["source_entailment_locally_certified"]
        first = stored[0]["typed_judgment_raw_aliases"]["claims"][0]
        assert first["units"][0]["fragment_ids"] == [expected["fragment_id"]]
        assert expected["fragment_id"] not in {
            fid for citation in first["citations"] for fid in citation["fragment_ids"]
        }
        if negative:
            assert job["state"] == "failed" and job["answer_id"] is None
            assert job["error"]["code"] == "SEMANTIC_CHECK_FAILED"
            assert request.state == "error"
            assert db.scalar(select(func.count()).select_from(Answer).where(Answer.request_id == request.id)) == 0
            assert not stored[1]["source_relation_assessment"]["accepted"]
            assert "SOURCE_RELATION_PARTIAL" in stored[1]["source_relation_assessment"]["semantic_defect_codes"]
            assert stored[1]["typed_judgment_raw_aliases"]["claims"][0]["units"][0]["status"] == "partial"
        else:
            assert job["state"] == "succeeded" and job["answer_id"] is not None
            assert stored[1]["source_relation_assessment"]["accepted"]

    if not negative:
        public = call(rt, "GET", "/answers/" + job["answer_id"])
        history = call(rt, "GET", "/sessions/" + chat["id"] + "/messages")
        assert history["items"][-1]["active_answer_id"] == public["id"]
        assert history["items"][-1]["answer"]["attribution"] == public["attribution"]
        # The HTTP response must expose exact canonical provenance, never raw F aliases.
        fragments = {f["fragment_id"]: f for f in public["attribution"]["fragments"]}
        for claim in stored[1]["source_relation_assessment"]["claims"]:
            for unit in claim["obligations"]:
                assert unit["fragment_ids"] == [quote["fragment_id"] for quote in unit["source_quotes"]]
                for quote in unit["source_quotes"]:
                    assert quote["fragment_id"] in fragments
                    fragment = fragments[quote["fragment_id"]]
                    assert (quote["evidence_id"], quote["quote"]) == (fragment["evidence_id"], fragment["exact_text"])
        assert call(rt, "GET", "/answers/" + public["id"])["attribution"] == public["attribution"]

