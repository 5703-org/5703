"""Pinned chapter admission and V5 execution in disposable PostgreSQL."""

from uuid import uuid4
from unittest.mock import patch

from sqlalchemy import select

from app.modules.answering.models import AnswerRequest, Job
from app.modules.knowledge.models import SourceUnit
from app.modules.knowledge.service import retrieve
from .test_chat_runtime import call, corpus, session, finish, submit


def context_for(rt, doc, build):
    with rt.db() as db:
        unit = db.scalar(
            select(SourceUnit).where(
                SourceUnit.processing_id == build.get("processing_id", "missing")
            )
        )
        if unit is None:
            from app.modules.knowledge.models import Chunk, ReleaseChunk

            chunk = db.scalar(
                select(Chunk)
                .join(ReleaseChunk, ReleaseChunk.chunk_id == Chunk.id)
                .where(
                    ReleaseChunk.release_id == build["release_id"], Chunk.document_id == doc["id"]
                )
                .order_by(Chunk.id)
            )
            units = list(
                db.scalars(
                    select(SourceUnit)
                    .where(SourceUnit.processing_id == chunk.processing_id)
                    .order_by(SourceUnit.sequence)
                )
            )
            unit = next(u for u in units if "Photosynthesis captures" in u.cleaned_text)
        return {
            "scope": "chapter",
            "document_id": doc["id"],
            "source_unit_id": unit.id,
            "selection": {"start": 0, "end": len(unit.cleaned_text), "text": unit.cleaned_text},
        }


def send(rt, s, context, content="What is photosynthesis?", key=None):
    return call(
        rt,
        "POST",
        f"/sessions/{s['id']}/messages",
        {"content": content, "reading_context": context},
        {**rt.headers(), "Idempotency-Key": key or str(uuid4())},
        202,
    )


def test_reading_scope_frozen_and_applied_before_dense_and_lexical_ranking(runtime):
    rt = runtime
    doc, build = corpus(rt)
    context = context_for(rt, doc, build)
    receipt = send(rt, session(rt), context)
    try:
        with rt.db() as db:
            req = db.get(AnswerRequest, receipt["request_id"])
            frozen = req.command["reading_context"]
            assert frozen["release_id"] == build["release_id"]
            assert frozen["selected_chunk_ids"]
            allowed = set(frozen["allowed_chunk_ids"])
            for variant in ("R0", "R1", "R2"):
                rows = retrieve(
                    db,
                    "Diffusion from high to low concentration",
                    req.release_id,
                    variant=variant,
                    top_k=10,
                    allowed_chunk_ids=list(allowed),
                )
                assert {r["chunk_id"] for r in rows} <= allowed
                assert all(r["section"] == frozen["section"] for r in rows)
            assert req.command["reliability_policy"] == "evidence_reliability_v5"
            assert req.command["generation_policy"]["version"] == "generation_controls_v10"
        answer = finish(rt, receipt)
        assert answer["reading_context"]["scope_hash"] == frozen["scope_hash"]
        assert "allowed_chunk_ids" not in answer["reading_context"]
        assert all(ev["chunk_id"] in allowed for ev in answer["evidence"])

    finally:
        job = call(rt, "GET", "/jobs/" + receipt["job_id"])
        if job["state"] in {"queued", "running", "retry_wait"}:
            cancelled = call(rt, "POST", "/jobs/" + receipt["job_id"] + "/cancel", {})
            assert cancelled["state"] == "cancelled"


def test_selected_passage_resolves_this_and_remains_in_frozen_generator_context(runtime):
    from app.modules.answering.service import safe_prompt_trace

    rt = runtime
    doc, build = corpus(rt)
    reading = context_for(rt, doc, build)
    receipt = send(rt, session(rt), reading, "Explain this paragraph.")
    # Inspect the actual generated messages before the production trace privacy
    # projection. Memory-enabled requests intentionally persist hashes only.
    with patch(
        "app.modules.answering.service.safe_prompt_trace", wraps=safe_prompt_trace
    ) as record_trace:
        answer = finish(rt, receipt)
    assert record_trace.call_count == 1
    messages, memory_context = record_trace.call_args.args
    assert any(reading["selection"]["text"] in row["content"] for row in messages)
    with rt.db() as db:
        req = db.get(AnswerRequest, receipt["request_id"])
        assert req.trace["prepared_query"]["needs_clarification"] is False
        assert req.trace["understanding"]["reader_reference_resolution"]["status"] == "source_bound"
        assert req.trace["context_coverage"]["targeted_query"] is None
        assert "read that exact source" in req.trace["context_coverage"]["response_guidance"]
        assert req.trace["model_messages"] == safe_prompt_trace(messages, memory_context)
        if memory_context:
            assert all("content" not in row for row in req.trace["model_messages"])
            assert all(row["redacted"] == "memory_context" for row in req.trace["model_messages"])
    assert answer["response"]["response_type"] != "clarification"


def test_selected_passage_location_does_not_create_missing_science_requirements(runtime):
    rt = runtime
    doc, build = corpus(rt)
    reading = context_for(rt, doc, build)
    receipt = send(
        rt,
        session(rt),
        reading,
        "What is photosynthesis in this selected passage?",
    )
    answer = finish(rt, receipt)
    with rt.db() as db:
        req = db.get(AnswerRequest, receipt["request_id"])
        assert req.command["requirements_version"] == "question_requirements_v4"
        assert req.trace["understanding"]["version"] == "question_requirements_v4"
        points = req.trace["understanding"]["required_knowledge"]
        assert len(points) == 1 and points[0]["terms"] == ["photosynthesis"]
        assert (
            req.trace["context_coverage"]["candidate_coverage"]["requirements"][0][
                "missing_term_groups"
            ]
            == []
        )
        diagnostic = {
            "refusal_reason": answer["response"].get("refusal_reason"),
            "context_estimate": req.trace["context_coverage"]["context_sufficiency_estimate"],
            "response_origin": req.trace.get("response_origin"),
            "retrieval_candidates": len(req.trace.get("retrieval_candidates", [])),
            "packed_evidence": req.trace.get("evidence_packing"),
        }
    assert answer["response"]["response_type"] == "answer", diagnostic
    assert answer["response"]["citations"]


def test_saved_pre_v4_reading_request_keeps_its_requirement_policy(runtime):
    rt = runtime
    doc, build = corpus(rt)
    receipt = send(
        rt,
        session(rt),
        context_for(rt, doc, build),
        "What is photosynthesis in this selected passage?",
    )
    with rt.db() as db:
        req = db.get(AnswerRequest, receipt["request_id"])
        command = dict(req.command)
        command.pop("requirements_version")
        req.command = command
        db.commit()
    finish(rt, receipt)
    with rt.db() as db:
        req = db.get(AnswerRequest, receipt["request_id"])
        assert req.trace["understanding"]["version"] == "question_requirements_v3"
        assert len(req.trace["understanding"]["required_knowledge"]) == 2


def test_changed_source_selection_and_scope_identity_are_rejected_before_execution(runtime):
    rt = runtime
    doc, build = corpus(rt)
    reading = context_for(rt, doc, build)
    bad = {
        **reading,
        "selection": {**reading["selection"], "text": "X" * len(reading["selection"]["text"])},
    }
    call(
        rt,
        "POST",
        f"/sessions/{session(rt)['id']}/messages",
        {"content": "Explain", "reading_context": bad},
        {**rt.headers(), "Idempotency-Key": str(uuid4())},
        422,
    )
    receipt = send(rt, session(rt), reading)
    with rt.db() as db:
        req = db.get(AnswerRequest, receipt["request_id"])
        value = {**req.command["reading_context"], "allowed_chunk_ids": []}
        req.command = {**req.command, "reading_context": value}
        db.commit()
    assert rt.work()
    job = call(rt, "GET", "/jobs/" + receipt["job_id"])
    assert job["state"] == "failed" and job["error"]["code"] == "EVIDENCE_UNAVAILABLE"


def test_omitted_and_explicit_null_reading_context_keep_idempotency_identity(runtime):
    rt = runtime
    s, key = session(rt), str(uuid4())
    first = submit(rt, s, "Hello", key)
    same = call(
        rt,
        "POST",
        f"/sessions/{s['id']}/messages",
        {"content": "Hello", "use_profile": True, "reading_context": None},
        {**rt.headers(), "Idempotency-Key": key},
        202,
    )
    assert same == first
    finish(rt, first)


def test_v4_frozen_command_still_executes_old_coverage_and_checker_policy(runtime):
    from generation.teaching_plan import freeze_generation_policy

    rt = runtime
    corpus(rt)
    receipt = submit(rt, session(rt))
    with rt.db() as db:
        req = db.get(AnswerRequest, receipt["request_id"])
        historical_command = dict(req.command)
        historical_command.pop("provider_output_policy")
        req.command = {
            **historical_command,
            "reliability_policy": "evidence_reliability_v4",
            "repair_policy": "cause_specific_repair_v2",
            "generation_policy": freeze_generation_policy(),
        }
        db.commit()
    answer = finish(rt, receipt)
    with rt.db() as db:
        req = db.get(AnswerRequest, receipt["request_id"])
        assert "provider_output_policy" not in req.command
        assert req.trace["token_budget"]["reliability_policy"] == "evidence_reliability_v4"
        assert req.trace["token_budget"]["context_coverage"]["version"] == "context_coverage_v1"
    assert answer["reading_context"] is None


def test_new_scope_excludes_old_citations_before_reuse(runtime):
    rt = runtime
    doc, build = corpus(rt)
    s = session(rt)
    first = finish(rt, submit(rt, s, "What is diffusion?"))
    reading = context_for(rt, doc, build)
    reading["selection"] = None
    second = finish(rt, send(rt, s, reading, "Explain that more simply."))
    with rt.db() as db:
        req = db.get(AnswerRequest, second["request_id"])
        allowed = set(req.command["reading_context"]["allowed_chunk_ids"])
        assert all(ev["chunk_id"] in allowed for ev in second["evidence"])
        assert all(
            ev["section"] == req.command["reading_context"]["section"] for ev in second["evidence"]
        )
    assert first["response"]["response_type"] == "answer"


def test_selected_paragraph_does_not_override_unresolved_domain_ambiguity(runtime):
    rt = runtime
    doc, build = corpus(rt)
    receipt = send(rt, session(rt), context_for(rt, doc, build), "What is RAG?")
    answer = finish(rt, receipt)
    assert answer["response"]["response_type"] == "clarification"
    with rt.db() as db:
        req = db.get(AnswerRequest, receipt["request_id"])
        assert req.budget["consumed_calls"] == 0
        assert req.trace["prepared_query"]["fallback_reason"] == "ambiguous_abbreviation:RAG"
