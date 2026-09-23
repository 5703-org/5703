"""Real HTTP/PG provenance plumbing; authored sources and scripted verdicts only."""

from copy import deepcopy
import hashlib
import json
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import select
from generation import GenerationService
from generation.adapters import chat_value
from generation.types import ProviderResult
from app.modules.answering.models import Answer, AnswerRequest
from app.modules.learning_state.models import PrivateAnswerDraft
from .test_chat_runtime import call, session, submit, corpus
from .test_learning_state import execute

GIVEN = "A sample has mass 12 g and volume 3 mL."
FORMULA = "Density equals mass divided by volume."


def density_corpus(rt):
    admin = rt.headers("admin@example.com")
    result = rt.client.post(
        "/api/v1/documents",
        headers=admin,
        data={"title": "Authored density fixture " + uuid4().hex},
        files={
            "file": (
                "density.txt",
                ("# Density " + uuid4().hex + "\n" + FORMULA + "\n").encode(),
                "text/plain",
            )
        },
    )
    assert result.status_code == 201
    doc = result.json()["data"]["document"]
    process = call(rt, "POST", "/documents/" + doc["id"] + "/process", {}, admin, 202)
    assert rt.work()
    build = call(
        rt,
        "POST",
        "/corpus/releases",
        {"processing_run_ids": [process["processing_id"]]},
        admin,
        202,
    )
    assert rt.work()
    call(rt, "POST", "/corpus/releases/" + build["release_id"] + "/activate", {}, admin)


class DensityTransport:
    def generate(self, messages, **kwargs):
        if kwargs["response_schema_name"] == "joint_check_v2":
            data = json.loads(messages[-1]["content"])
            source = next(f for f in data["SOURCE_FRAGMENTS"] if FORMULA in f["exact_text"])
            proof = {
                "formula_basis": "textbook",
                "formula_fragment_id": source["fragment_id"],
                "formula_quote": FORMULA,
                "expression": "mass / volume",
                "inputs": [
                    {
                        "name": "mass",
                        "value": "12",
                        "unit": "g",
                        "quote": GIVEN,
                        "origin": "problem_input",
                        "fragment_id": None,
                    },
                    {
                        "name": "volume",
                        "value": "3",
                        "unit": "mL",
                        "quote": GIVEN,
                        "origin": "problem_input",
                        "fragment_id": None,
                    },
                ],
                "result": "4",
                "result_quote": "4 g/mL",
                "result_unit": "g/mL",
                "units_consistent": True,
                "formula_applicable": True,
            }
            value = {
                "claims": [
                    {
                        "claim_id": c["claim_id"],
                        "factual": True,
                        "status": "supported",
                        "fragment_ids": [source["fragment_id"]],
                        "basis": "derived_calculation",
                        "problem_quote": None,
                        "derivation": proof,
                        "reason": "Scripted fixture proof, not a scientific quality rating.",
                    }
                    for c in data["CLAIMS"]
                ],
                "body_ok": True,
                "specific_help": True,
                "scope_ok": True,
                "suggestions_ok": True,
                "evidence_display_ok": True,
                "cumulative_ok": True,
                "complete_answer": True,
                "coverage": "full",
                "missing_facets": [],
                "limitations_explicit": False,
                "reason": "Authored fixture checks persistence only.",
                "repair_fragment_ids": [],
            }
        else:
            value = chat_value("answer", "The density is 4 g/mL. [ev_001]", citations=["ev_001"])
        return ProviderResult(
            raw_text=json.dumps(value),
            provider="scripted_fixture",
            model="scripted_fixture",
            request_submitted=True,
        )


def factory(**kwargs):
    transport = DensityTransport()
    return GenerationService(transport, checker_adapter=transport, **kwargs)


def test_http_derived_support_has_exact_sources_private_proof_and_reload(runtime):
    rt = runtime
    density_corpus(rt)
    s = session(rt)
    receipt = submit(rt, s, GIVEN + " Calculate its density.")
    with patch("app.modules.answering.service.GenerationService", factory):
        result = execute(rt, receipt)
    support = result["attribution"]["claims"][0]["support"]
    assert support["basis"] == "derived_calculation"
    assert support["derivation_validation"]["arithmetic_checked"]
    assert support["derivation_validation"]["human_rating"] is None
    assert "inputs" not in json.dumps(support) and "expression" not in json.dumps(support)
    for fragment in result["attribution"]["fragments"]:
        assert hashlib.sha256(fragment["exact_text"].encode()).hexdigest() == fragment["text_hash"]
    assert call(rt, "GET", "/answers/" + result["id"])["attribution"] == result["attribution"]
    assert (
        call(rt, "GET", f"/sessions/{s['id']}/messages")["items"][-1]["answer"]["attribution"]
        == result["attribution"]
    )
    with rt.db() as db:
        frozen = db.get(AnswerRequest, receipt["request_id"])
        assert frozen.command["reliability_policy"] == "evidence_reliability_v2"
        assert frozen.budget["consumed_calls"] == 2
        private = list(
            db.scalars(select(PrivateAnswerDraft).where(PrivateAnswerDraft.request_id == frozen.id))
        )
        assert any('"expression": "mass / volume"' in json.dumps(p.payload) for p in private)


def test_frozen_legacy_mock_still_reads_with_nullable_derived_metadata(runtime):
    rt = runtime
    corpus(rt)
    receipt = submit(rt, session(rt))
    with rt.db() as db:
        row = db.get(AnswerRequest, receipt["request_id"])
        command = deepcopy(row.command)
        for key in ("reliability_policy", "generation_context_policy", "repair_policy"):
            command.pop(key, None)
        row.command = command
        db.commit()
    result = execute(rt, receipt)
    assert result["response"]["response_type"] == "answer"
    assert all(
        c["support"]["derivation_validation"] is None for c in result["attribution"]["claims"]
    )
    assert all(c["support"]["status"] is None for c in result["attribution"]["claims"])


def test_tampered_exact_source_span_never_publishes_answer(runtime):
    rt = runtime
    density_corpus(rt)
    receipt = submit(rt, session(rt), GIVEN + " Calculate its density.")

    def corrupt(**kwargs):
        service = factory(**kwargs)
        original = service.generate

        def generate(*args, **values):
            result = original(*args, **values)
            assert result.succeeded
            result.attribution["fragments"][0]["start"] += 1
            return result

        service.generate = generate
        return service

    with patch("app.modules.answering.service.GenerationService", corrupt):
        assert rt.work()
    job = call(rt, "GET", "/jobs/" + receipt["job_id"])
    assert job["state"] == "failed"
    with rt.db() as db:
        assert db.scalar(select(Answer).where(Answer.request_id == receipt["request_id"])) is None
