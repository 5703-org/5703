"""Diagnostics expose actionable workspace records without private transport data."""

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.cli import seed
from app.core.config import Settings
from app.core.security import hash_password
from app.db.base import Base
from app.main import create_app
from app.modules.answering.models import Answer, AnswerRequest, Attempt, Evidence, Job
from app.modules.identity.models import Role, User, Workspace
from app.modules.knowledge.models import Document
from app.modules.learning.models import ChatSession

SECRET = "private-provider-credential-must-not-be-returned"
ROOT = "/api/v1/admin/failures"


def test_provider_projection_keeps_typed_failure_without_echoed_payload():
    from app.modules.answering.diagnostics import provider_projection

    value = provider_projection(
        {
            "stage": "http",
            "http_status": 400,
            "provider_error_parameter": "max_tokens",
            "provider_error_code": "unsupported_parameter",
            "provider_request_id": "req-public-id",
            "message": SECRET,
            "body": SECRET,
            "headers": {"Authorization": SECRET},
            "network_error": SECRET,
            "request_submitted": True,
        }
    ).model_dump()
    assert value["http_status"] == 400
    assert value["provider_error_parameter"] == "max_tokens"
    assert SECRET not in str(value)
    assert provider_projection({"stage": SECRET}) is None


def test_publication_block_projection_rejects_non_scalar_control_fields():
    from app.modules.answering.diagnostics import publication_block_projection

    base = {
        "code": "SEMANTIC_CHECK_FAILED",
        "details": {
            "publication_block": {
                "version": "semantic_publication_block_v1",
                "stop_reason": [SECRET],
                "checker_reported_coverage": "full",
            }
        },
    }
    assert publication_block_projection(base) is None
    base["details"]["publication_block"]["stop_reason"] = "final_recheck_rejected"
    base["details"]["publication_block"]["checker_reported_coverage"] = {"secret": SECRET}
    assert publication_block_projection(base) is None


@pytest.fixture
def diagnosis(tmp_path):
    settings = Settings(
        _env_file=None,
        env="test",
        database_url="sqlite:///" + str(tmp_path / "diagnostics.db"),
        jwt_secret="diagnostics-test-secret-at-least-thirty-two",
    )
    app = create_app(settings)
    Base.metadata.create_all(app.state.engine)
    factory = sessionmaker(bind=app.state.engine, expire_on_commit=False)
    with factory() as db:
        seed(db)
        workspace = Workspace(name="Foreign", slug="foreign")
        db.add(workspace)
        db.flush()
        db.add(
            User(
                email="foreign@example.com",
                full_name="Foreign admin",
                hashed_password=hash_password("Passw0rd!"),
                role_id=db.scalar(select(Role.id).where(Role.name == "admin")),
                workspace_id=workspace.id,
            )
        )
        db.commit()
    client = TestClient(app)

    def headers(email="admin@example.com"):
        result = client.post("/api/v1/auth/login", json={"email": email, "password": "Passw0rd!"})
        assert result.status_code == 200
        return {"Authorization": "Bearer " + result.json()["data"]["access_token"]}

    def record(
        email="student@example.com",
        state="refused",
        deleted=False,
        traced=True,
        trace_fields=None,
        answer_timing=None,
        error_payload=None,
    ):
        with factory() as db:
            owner = db.scalar(select(User).where(User.email == email))
            session = ChatSession(
                user_id=owner.id,
                workspace_id=owner.workspace_id,
                title="A diagnosis fixture",
                deleted_at=datetime.now(timezone.utc) if deleted else None,
            )
            db.add(session)
            db.flush()
            req = AnswerRequest(
                owner_id=owner.id,
                session_id=session.id,
                route="fixture",
                idempotency_key=uuid4().hex,
                body_hash="0" * 64,
                mode="interactive_chat",
                response_schema="chat_response_v1",
                state=state,
                command={
                    "question": "Why does water move across a membrane?",
                    "model_config": {
                        "provider": "openai_compatible",
                        "model": "fixture",
                        "api_key": SECRET,
                    },
                    "private_gold": SECRET,
                },
                trace={"private_prompt": SECRET},
                budget={"consumed_calls": 1, "raw_error": SECRET},
            )
            if traced:
                req.trace = {
                    **req.trace,
                    "prepared_query": {"intent": "new_question", "retrieval_query": "osmosis"},
                    "evidence_selection": {
                        "candidate_count": 5,
                        "submitted_count": 2,
                        "cited_count": 1,
                        "candidate_chunk_ids": ["c1", "c2", "c3", "c4", "c5"],
                    },
                }
            if trace_fields:
                req.trace = {**req.trace, **trace_fields}
            db.add(req)
            db.flush()
            job = Job(
                request_id=req.id,
                owner_id=owner.id,
                state="failed" if state == "error" else "succeeded",
                stage="generation",
                error=error_payload
                if state == "error" and error_payload is not None
                else {"code": "PROVIDER_AUTH_ERROR", "message": SECRET, "raw_body": SECRET}
                if state == "error"
                else None,
            )
            db.add(job)
            db.flush()
            db.add(
                Attempt(
                    job_id=job.id,
                    sequence=1,
                    payload={
                        "stage": "generation",
                        "phase": "initial",
                        "latency_ms": 12,
                        "raw_body": SECRET,
                        "error": {"code": "PROVIDER_AUTH_ERROR", "message": SECRET},
                    },
                )
            )
            if state != "error":
                answer = Answer(
                    request_id=req.id,
                    job_id=job.id,
                    response_schema="chat_response_v1",
                    response={
                        "response_type": "answer",
                        "answer_text": "Water moves down its water potential gradient.",
                        "citations": ["ev1"],
                    },
                    model_mode="mock",
                    timing=answer_timing or {},
                )
                db.add(answer)
                document = Document(owner_id=owner.id, title="Authored diagnostic fixture")
                db.add(document)
                db.flush()
                for index in (1, 2):
                    db.add(
                        Evidence(
                            answer_id=answer.id,
                            evidence_id=f"ev{index}",
                            document_id=document.id,
                            chunk_id=f"c{index}",
                            payload={"text": "Authored transport fixture"},
                        )
                    )
            db.commit()
            return req.id

    yield SimpleNamespace(client=client, headers=headers, record=record)
    client.close()
    app.state.engine.dispose()


def test_diagnostics_scope_and_permissions(diagnosis):
    runtime = diagnosis
    visible = runtime.record()
    foreign = runtime.record(email="foreign@example.com")
    deleted = runtime.record(deleted=True)
    assert runtime.client.get(ROOT).status_code == 401
    assert (
        runtime.client.get(ROOT, headers=runtime.headers("student@example.com")).status_code == 403
    )
    response = runtime.client.get(ROOT, headers=runtime.headers())
    assert response.status_code == 200
    assert [row["request_id"] for row in response.json()["data"]["items"]] == [visible]
    for request_id in (foreign, deleted, "missing"):
        assert (
            runtime.client.get(f"{ROOT}/{request_id}", headers=runtime.headers()).status_code == 404
        )


def test_actual_citations_and_distinct_evidence_counts(diagnosis):
    runtime = diagnosis
    request_id = runtime.record(state="answered")
    assert runtime.client.get(ROOT, headers=runtime.headers()).json()["data"]["total"] == 0
    response = runtime.client.get(f"{ROOT}/{request_id}", headers=runtime.headers())
    assert response.status_code == 200
    row = response.json()["data"]
    assert row["counts"] == {"candidates": 5, "filtered": None, "submitted": 2, "cited": 1}
    assert row["evidence"] == {
        "candidate_chunk_ids": ["c1", "c2", "c3", "c4", "c5"],
        "submitted_chunk_ids": ["c1", "c2"],
        "cited_chunk_ids": ["c1"],
    }
    assert row["retrieval_query"] == "osmosis"
    assert SECRET not in response.text
    assert row["budget"] == {"consumed_calls": 1}


def test_unrecorded_counts_remain_unknown_and_errors_are_safe(diagnosis):
    runtime = diagnosis
    request_id = runtime.record(state="error", traced=False)
    response = runtime.client.get(f"{ROOT}/{request_id}", headers=runtime.headers())
    assert response.status_code == 200
    row = response.json()["data"]
    assert row["counts"] == {"candidates": None, "filtered": None, "submitted": None, "cited": None}
    assert SECRET not in response.text
    assert row["error_message"]
    assert row["attempts"][0]["error_code"] == "PROVIDER_AUTH_ERROR"
    assert row["evidence"] == {
        "candidate_chunk_ids": [],
        "submitted_chunk_ids": [],
        "cited_chunk_ids": [],
    }
    assert row["processing"]["understanding"]["needs_clarification"] is None
    assert row["processing"]["timing_ms"] == {}
    assert row["processing"]["coverage"] is None
    assert row["processing"]["facet_fallback"] is None


def test_semantic_publication_block_is_admin_scoped_and_content_free(diagnosis):
    error = {
        "code": "SEMANTIC_CHECK_FAILED",
        "message": SECRET,
        "details": {
            "raw_checker_text": SECRET,
            "publication_block": {
                "version": "semantic_publication_block_v1",
                "stop_reason": "insufficient_calls_for_repair_and_recheck",
                "remaining_provider_calls": 1,
                "required_calls_for_repair_and_recheck": 2,
                "checker_contract_repair_calls": 1,
                "checker_reported_body_ok": False,
                "checker_reported_non_supported_factual_claims": 1,
                "failed_checker_gate_names": ["body_ok", SECRET],
                "checker_reported_coverage": "supported_partial",
                "requirement_issue_codes": ["REQUIRED_CONTENT_OMITTED", SECRET],
                "structural_issue_codes": ["CHECK_UNDISPLAYED_SUPPORT", SECRET],
                "private_source_text": SECRET,
            },
        },
    }
    owned = diagnosis.record(state="error", error_payload=error)
    foreign = diagnosis.record(email="foreign@example.com", state="error", error_payload=error)
    assert diagnosis.client.get(f"{ROOT}/{owned}").status_code == 401
    assert (
        diagnosis.client.get(
            f"{ROOT}/{owned}", headers=diagnosis.headers("student@example.com")
        ).status_code
        == 403
    )
    assert diagnosis.client.get(f"{ROOT}/{foreign}", headers=diagnosis.headers()).status_code == 404
    response = diagnosis.client.get(f"{ROOT}/{owned}", headers=diagnosis.headers())
    assert response.status_code == 200
    projected = response.json()["data"]["publication_block"]
    assert projected["stop_reason"] == "insufficient_calls_for_repair_and_recheck"
    assert projected["remaining_provider_calls"] == 1
    assert projected["checker_contract_repair_calls"] == 1
    assert projected["failed_checker_gate_names"] == ["body_ok"]
    assert projected["requirement_issue_codes"] == ["REQUIRED_CONTENT_OMITTED"]
    assert projected["structural_issue_codes"] == ["CHECK_UNDISPLAYED_SUPPORT"]
    assert SECRET not in response.text


def test_paginated_failure_list(diagnosis):
    runtime = diagnosis
    ids = {runtime.record(), runtime.record(state="error"), runtime.record(state="answered")}
    first = runtime.client.get(
        ROOT, params={"state": "all", "limit": 2}, headers=runtime.headers()
    ).json()["data"]
    second = runtime.client.get(
        ROOT, params={"state": "all", "limit": 2, "offset": 2}, headers=runtime.headers()
    ).json()["data"]
    assert first["total"] == second["total"] == 3
    assert {row["request_id"] for row in first["items"] + second["items"]} == ids
    assert (
        runtime.client.get(ROOT, params={"limit": 101}, headers=runtime.headers()).status_code
        == 422
    )


def test_processing_trace_projects_actual_stages_and_authoritative_timing(diagnosis):
    runtime = diagnosis
    request_id = runtime.record(
        state="answered",
        answer_timing={
            "preparation_ms": 12.5,
            "retrieval_ms": 450,
            "total_ms": 620,
            "timing_scope": "worker_execution_before_answer_insert_v1",
            "raw_error": SECRET,
        },
        trace_fields={
            "preparation_ms": 462.5,
            "stage_timing": {"preparation_ms": 4000},
            "understanding": {
                "standalone_query": "Compare diffusion and osmosis at 20 degrees.",
                "intent": "factual",
                "topic_relation": "new_topic",
                "needs_clarification": False,
                "requested_facets": [
                    {
                        "id": "f1",
                        "request": "Compare diffusion and osmosis",
                        "terms": ["diffusion", "osmosis"],
                        "private_gold": SECRET,
                    }
                ],
                "comparison_targets": ["diffusion", "osmosis"],
                "constraints": {
                    "negation": ["without"],
                    "numbers": ["20"],
                    "conditions": ["at 20 degrees"],
                    "secret": SECRET,
                },
                "method": "deterministic",
                "private_reasoning": SECRET,
            },
            "local_model_execution": {
                "requested_device": "auto",
                "resolved_device": "cpu",
                "model_path": SECRET,
            },
            "retrieval_execution": {
                "relevance_gate": {
                    "policy": {
                        "version": "interactive_relevance_v1",
                        "minimum_logit": -4.0,
                        "api_key": SECRET,
                    },
                    "candidate_count": 7,
                    "accepted_count": 5,
                    "accepted_chunk_ids": ["c1", "c2", "c3", "c4", "c5"],
                    "excluded": [
                        {
                            "chunk_id": "c6",
                            "reason": "below_relevance_threshold",
                            "score": -8.5,
                            "text": SECRET,
                        },
                        {"chunk_id": "c7", "reason": SECRET, "score": False},
                    ],
                },
                "inherited_evidence": {
                    "available_count": 3,
                    "eligible_count": 1,
                    "rescored_chunk_ids": ["c1"],
                    "private": SECRET,
                    "excluded": [
                        {"chunk_id": "old", "reason": "source_unavailable", "text": SECRET}
                    ],
                },
                "candidate_merge": {"excluded": [{"chunk_id": "c20", "reason": "candidate_limit"}]},
            },
            "coverage_estimate": {
                "version": "lexical_facets_v1",
                "status": "partial",
                "uncovered_facet_ids": ["f2"],
                "scope": SECRET,
            },
            "evidence_packing": {
                "version": "complementary_v1",
                "text_token_ceiling": 3000,
                "duplicate_count": 2,
                "prompt": SECRET,
            },
            "citation_audit": {
                "version": "citation_locality_v1",
                "status": "review_required",
                "flag_count": 1,
                "raw_response": SECRET,
            },
            "teaching_plan": {
                "level": "beginner",
                "style": "socratic",
                "mode": "hint",
                "prompt": SECRET,
            },
        },
    )
    result = runtime.client.get(f"{ROOT}/{request_id}", headers=runtime.headers())
    assert result.status_code == 200
    row = result.json()["data"]
    assert row["counts"] == {"candidates": 7, "filtered": 5, "submitted": 2, "cited": 1}
    assert set(row["evidence"]["candidate_chunk_ids"]) == {f"c{i}" for i in range(1, 8)}
    processing = row["processing"]
    assert processing["understanding"]["numbers"] == ["20"]
    assert processing["understanding"]["negation"] == ["without"]
    assert processing["understanding"]["requested_facets"][0]["terms"] == ["diffusion", "osmosis"]
    assert processing["understanding"]["needs_clarification"] is False
    assert processing["requested_device"] == "auto" and processing["resolved_device"] == "cpu"
    assert processing["timing_ms"] == {"preparation_ms": 12.5, "retrieval_ms": 450, "total_ms": 620}
    assert processing["coverage"]["status"] == "partial"
    assert processing["packing"]["duplicate_count"] == 2
    assert processing["citation_audit"]["status"] == "review_required"
    assert processing["excluded"][1]["reason"] == "unrecorded_reason"
    assert processing["excluded"][1]["score"] is None
    assert processing["excluded"][2]["reason"] == "source_unavailable"
    assert processing["excluded"][3]["reason"] == "candidate_limit"
    assert processing["reuse"] == {
        "available_count": 3,
        "eligible_count": 1,
        "rescored_chunk_ids": ["c1"],
    }
    assert processing["teaching"] == {"level": "beginner", "style": "socratic", "mode": "hint"}
    assert SECRET not in result.text


def test_trace_exclusions_are_bounded_and_invalid_numeric_observations_remain_unknown(diagnosis):
    runtime = diagnosis
    request_id = runtime.record(
        state="error",
        traced=False,
        trace_fields={
            "stage_timing": {
                "preparation_ms": True,
                "retrieval_ms": -1,
                "query_preparation_ms": 3.5,
            },
            "retrieval_execution": {
                "relevance_gate": {
                    "candidate_count": True,
                    "accepted_count": -2,
                    "excluded": [
                        {"chunk_id": f"c{i}", "reason": "expanded_concept_absent"}
                        for i in range(105)
                    ],
                }
            },
            "understanding": {"needs_clarification": "false"},
        },
    )
    row = runtime.client.get(f"{ROOT}/{request_id}", headers=runtime.headers()).json()["data"]
    assert row["counts"]["candidates"] is None and row["counts"]["filtered"] is None
    assert len(row["processing"]["excluded"]) == 100
    assert row["processing"]["exclusions_truncated"] is True
    assert row["processing"]["understanding"]["needs_clarification"] is None
    assert row["processing"]["timing_ms"] == {"query_preparation_ms": 3.5}


def test_facet_fallback_uses_final_distinct_counts_and_keeps_score_queries_separate(diagnosis):
    runtime = diagnosis
    request_id = runtime.record(
        state="answered",
        trace_fields={
            "retrieval_execution": {
                "relevance_gate": {
                    "candidate_count": 6,
                    "accepted_count": 0,
                    "accepted_chunk_ids": [],
                    "excluded": [
                        {"chunk_id": f"c{i}", "reason": "below_relevance_threshold", "score": -8}
                        for i in range(1, 7)
                    ],
                },
                "final_selection": {
                    "candidate_count": 8,
                    "accepted_count": 3,
                    "candidate_chunk_ids": [f"c{i}" for i in range(1, 9)],
                    "accepted_chunk_ids": ["c1", "c2", "c8"],
                    "source": "facet_fallback",
                },
                "facet_fallback": {
                    "triggered": True,
                    "reason": "fallback_completed",
                    "policy": {"version": "interactive_facet_fallback_v1", "api_key": SECRET},
                    "elapsed_ms": 250.5,
                    "accepted_chunk_ids": ["c1", "c2", "c8"],
                    "attempted_facets": [
                        {
                            "facet_id": "part_1",
                            "query": "Explain photosynthesis.",
                            "candidate_count": 6,
                            "accepted_count": 3,
                            "accepted_chunk_ids": ["c1", "c2", "c8"],
                            "model": "pinned-reranker",
                            "revision": "revision-1",
                            "excluded": [
                                {
                                    "chunk_id": "c4",
                                    "reason": "below_relevance_threshold",
                                    "score": -6.5,
                                    "text": SECRET,
                                }
                            ],
                            "raw_prompt": SECRET,
                        },
                        {
                            "facet_id": "part_2",
                            "query": "Give tomorrow's exact Bitcoin price.",
                            "candidate_count": 6,
                            "accepted_count": 0,
                            "accepted_chunk_ids": [],
                            "model": "pinned-reranker",
                            "revision": "revision-1",
                            "excluded": [],
                        },
                    ],
                    "private_response": SECRET,
                },
            },
        },
    )
    response = runtime.client.get(f"{ROOT}/{request_id}", headers=runtime.headers())
    assert response.status_code == 200
    row = response.json()["data"]
    assert row["counts"] == {"candidates": 8, "filtered": 3, "submitted": 2, "cited": 1}
    assert row["evidence"]["candidate_chunk_ids"] == [f"c{i}" for i in range(1, 9)]
    fallback = row["processing"]["facet_fallback"]
    assert row["processing"]["selection_source"] == "facet_fallback"
    assert fallback["triggered"] is True
    assert fallback["whole_query_candidate_count"] == 6
    assert fallback["whole_query_accepted_count"] == 0
    assert fallback["elapsed_ms"] == 250.5
    assert fallback["attempted_facets"][0]["query"] == "Explain photosynthesis."
    assert fallback["attempted_facets"][0]["excluded"][0]["score"] == -6.5
    assert fallback["attempted_facets"][1]["accepted_count"] == 0
    assert SECRET not in response.text
    summary = runtime.client.get(
        ROOT, params={"state": "answered"}, headers=runtime.headers()
    ).json()["data"]["items"][0]
    assert summary["counts"] == row["counts"]
