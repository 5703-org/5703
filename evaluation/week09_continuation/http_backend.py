"""Real application-backed textbook QA adapter for a dedicated evaluation account."""

from __future__ import annotations

import hashlib
import os
import time

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from evaluation.conversations.http_backend import HttpChatBackend


def normalize_answer(result: dict, *, hint: bool) -> dict:
    """Normalize the learner-visible HTTP result without inventing model counters."""
    status = result.get("status")
    receipt = result.get("receipt") or {}
    if status == "completed":
        answer = result["answer"]
        response = answer["response"]
        if not isinstance(response.get("answer_text"), str) or not response["answer_text"].strip():
            return {
                "state": "empty_output",
                "learner_visible_output": None,
                "displayed_sources": [],
                "provider_calls": None,
                "usage": {},
                "application_receipt": {"job_id": receipt.get("job_id"), "answer_id": answer["id"]},
                "model_mode": answer.get("model_mode"),
            }
        content = {"response": response, "presentation": answer.get("presentation")}
        citations = set(response.get("citations") or [])
        views = (answer.get("presentation") or {}).get("citation_views")
        sources = (
            views
            if isinstance(views, list)
            else [
                item for item in answer.get("evidence", []) if item.get("evidence_id") in citations
            ]
        )
        completeness = answer.get("answer_completeness") or {}
        state = (
            "supported_partial"
            if completeness.get("status") == "partial"
            else ("hinted" if hint else "answered")
        )
        return {
            "state": state,
            "learner_visible_output": content,
            "displayed_sources": sources,
            "submitted_evidence": answer.get("evidence"),
            "submitted_evidence_scope": "saved_answer_evidence_not_exact_generation_prompt",
            "provider_calls": None,
            "usage": {},
            "application_receipt": {"job_id": receipt.get("job_id"), "answer_id": answer["id"]},
            "model_mode": answer.get("model_mode"),
        }
    if status in {"refused", "clarification", "social"}:
        answer = result["answer"]
        return {
            "state": {
                "refused": "evidence_refusal",
                "clarification": "clarification",
                "social": "social_response",
            }[status],
            "learner_visible_output": None,
            "published_status_text": answer["response"].get("answer_text"),
            "displayed_sources": [],
            "provider_calls": None,
            "usage": {},
            "application_receipt": {"job_id": receipt.get("job_id"), "answer_id": answer["id"]},
            "model_mode": answer.get("model_mode"),
        }
    error = result.get("error") or {}
    code = error.get("code", "UNKNOWN")
    if status == "cancelled":
        state = "cancelled"
    elif status == "incomplete":
        state = "timeout"
    elif code in {"NO_LOCAL_MODEL", "EMBEDDING_UNAVAILABLE", "RERANK_UNAVAILABLE"}:
        state = "local_model_failure"
    elif code in {"NO_EVIDENCE", "INSUFFICIENT_EVIDENCE"}:
        state = "evidence_refusal"
    elif code in {"EMPTY_PROVIDER_OUTPUT", "EMPTY_OUTPUT"}:
        state = "empty_output"
    elif code in {"INVALID_PROVIDER_OUTPUT", "INVALID_JSON"}:
        state = "invalid_output"
    else:
        state = "model_failure" if status == "error" else "execution_failure"
    return {
        "state": state,
        "learner_visible_output": None,
        "provider_calls": None,
        "usage": {},
        "error": {"code": code, "message": error.get("message")},
        "application_receipt": {"job_id": receipt.get("job_id")},
    }


class IsolatedTraceUsage:
    """Read the isolated application's saved provider accounting by job ID."""

    def __init__(self, *, database_url_env: str, expected_release_id: str):
        url = os.environ.get(database_url_env)
        if not url:
            raise ValueError("The private isolated database URL is unavailable")
        parsed = make_url(url)
        if (
            parsed.drivername != "postgresql+psycopg"
            or parsed.host not in {"127.0.0.1", "localhost"}
            or parsed.port != 16532
        ):
            raise ValueError("Pilot trace reads must use the isolated port-16532 clone")
        self.engine = create_engine(url, hide_parameters=True, connect_args={"connect_timeout": 10})
        self.expected_release_id = expected_release_id

    def __call__(self, job_id: str) -> dict:
        with Session(self.engine) as db:
            db.execute(text("SET TRANSACTION READ ONLY"))
            if db.scalar(text("SHOW transaction_read_only")) != "on":
                raise ValueError("Provider accounting was not read-only")
            observed = (
                db.execute(
                    text("""
                SELECT r.release_id, r.budget, r.trace, j.state
                FROM jobs j JOIN answer_requests r ON r.id=j.request_id
                WHERE j.id=:job
                """),
                    {"job": job_id},
                )
                .mappings()
                .one_or_none()
            )
            if observed is None:
                raise ValueError("The application job has no saved request trace")
            if observed["release_id"] != self.expected_release_id:
                raise ValueError("The answer trace uses a different corpus release")
            usage = (observed["trace"] or {}).get("usage") or {}
            budget = observed["budget"] or {}
            return {
                "provider_calls": budget.get("consumed_calls"),
                "usage": {
                    "input_tokens": usage.get("input_tokens"),
                    "output_tokens": usage.get("output_tokens"),
                    "cache_hit_input_tokens": usage.get("cache_hit_input_tokens"),
                    "cache_miss_input_tokens": usage.get("cache_miss_input_tokens"),
                },
                "usage_complete": usage.get("usage_complete") is True,
                "stage_usage": (observed["trace"] or {}).get("stage_usage", []),
                "application_job_state": observed["state"],
                "trace_scope": "saved_isolated_application_request_read_only",
            }

    def close(self):
        self.engine.dispose()


class TextbookQAHttpBackend:
    """One session per case/arm, no hidden source labels or answer key in requests."""

    def __init__(self, chat: HttpChatBackend, trace_usage: IsolatedTraceUsage | None = None):
        self.chat = chat
        self.trace_usage = trace_usage

    def _with_usage(self, result: dict, job_id: str) -> dict:
        result = {
            **result,
            "evaluation_owner_fingerprint": hashlib.sha256(
                self.chat.email.casefold().encode()
            ).hexdigest(),
        }
        if self.trace_usage is None:
            return result
        try:
            return {**result, **self.trace_usage(job_id)}
        except Exception as exc:
            # Accounting failure cannot turn an already saved learner answer into
            # an answer failure; retain the unknown amount for reconciliation.
            return {
                **result,
                "usage_trace_error": {"type": type(exc).__name__, "message": str(exc)[:300]},
            }

    def __call__(self, task: dict, arm: str, identity: str) -> dict:
        if arm != "candidate":
            raise ValueError(
                "This HTTP adapter implements candidate QA only; use separate frozen E0/E1 and old-release runners"
            )
        question = task.get("question")
        if not isinstance(question, str) or not question.strip():
            raise ValueError("QA task needs its ordinary learner question")
        session_id = self.chat.new_session()
        idempotency = hashlib.sha256(f"week09-continuation:{identity}".encode()).hexdigest()
        body = {
            "content": question,
            "answer_mode": "textbook",
            "teaching_mode": "hint" if task.get("teaching_mode") == "hint" else "direct",
            "use_profile": bool(task.get("use_profile", False)),
        }
        if task.get("reading_context"):
            body["reading_context"] = task["reading_context"]
        receipt = self.chat._request(
            "POST",
            f"/sessions/{session_id}/messages",
            body,
            {"Idempotency-Key": idempotency},
        )
        deadline = time.monotonic() + self.chat.timeout
        while True:
            job = self.chat._request("GET", "/jobs/" + receipt["job_id"])
            if job["state"] == "succeeded":
                answer = self.chat._request("GET", "/answers/" + job["answer_id"])
                response_type = answer["response"].get("response_type")
                status = {
                    "refusal": "refused",
                    "clarification": "clarification",
                    "social": "social",
                }.get(response_type, "completed")
                normalized = normalize_answer(
                    {"status": status, "receipt": receipt, "answer": answer},
                    hint=body["teaching_mode"] == "hint",
                )
                if task.get("require_live", True) and answer.get("model_mode") != "live":
                    raise ValueError("A formal candidate request returned non-live model mode")
                return self._with_usage(normalized, receipt["job_id"])
            if job["state"] in {"failed", "cancelled"}:
                return self._with_usage(
                    normalize_answer(
                        {
                            "status": "cancelled" if job["state"] == "cancelled" else "error",
                            "receipt": receipt,
                            "error": job.get("error"),
                        },
                        hint=False,
                    ),
                    receipt["job_id"],
                )
            if time.monotonic() >= deadline:
                return self._with_usage(
                    normalize_answer(
                        {
                            "status": "incomplete",
                            "receipt": receipt,
                            "error": {
                                "code": "STUDY_POLL_TIMEOUT",
                                "message": "Inspect the saved job receipt before any retry",
                            },
                        },
                        hint=False,
                    ),
                    receipt["job_id"],
                )
            time.sleep(self.chat.poll_interval)
