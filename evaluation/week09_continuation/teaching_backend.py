"""Frozen, real-source A-D first-hint generation for the continuation pilot."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path

from evaluation.week09.study import build_request as build_prior_study_request
from generation import GenerationService, RequestBudget
from generation.teaching_plan import freeze_generation_policy

from .protocol import canonical, digest_bytes, load_frozen


ARMS = {"A", "B", "C", "D"}


def normalize_teaching_outcome(outcome) -> dict:
    """Preserve the exact visible hint and observed generation/checking usage."""
    record = outcome.to_dict() if hasattr(outcome, "to_dict") else dict(outcome)
    response = record.get("response") or {}
    error = record.get("error") or {}
    usage = record.get("usage") or {}
    budget = record.get("budget") or {}
    if response:
        answer_text = response.get("answer_text")
        response_type = response.get("response_type")
        if response_type == "refusal":
            state = "evidence_refusal"
        elif response_type == "clarification":
            state = "clarification"
        elif not isinstance(answer_text, str) or not answer_text.strip():
            state = "empty_output"
        else:
            state = "hinted"
    else:
        code = str(error.get("code") or "UNKNOWN")
        state = (
            "timeout"
            if code in {"TIMEOUT", "REQUEST_TIMEOUT", "BUDGET_EXHAUSTED"}
            else "invalid_output"
            if code in {"INVALID_PROVIDER_OUTPUT", "INVALID_JSON"}
            else "empty_output"
            if code in {"EMPTY_PROVIDER_OUTPUT", "EMPTY_OUTPUT"}
            else "model_failure"
        )
    if response and record.get("model_mode") != "live":
        raise ValueError("The factorial pilot requires a real answer/checker model")
    visible = record.get("delivered_projection") or {}
    if state == "hinted" and not visible.get("response"):
        raise ValueError("A published hint lacks its final learner-visible projection")
    return {
        "state": state,
        "learner_visible_output": visible if state == "hinted" else None,
        "published_status_text": response.get("answer_text") if state != "hinted" else None,
        "displayed_sources": visible.get("citation_views", []) if state == "hinted" else [],
        "submitted_evidence": record.get("evidence"),
        "submitted_evidence_scope": "generation_outcome_selected_evidence",
        "prior_learner_exposure": record.get("teaching_context", {}).get("delivered_turns", []),
        "provider_calls": budget.get("consumed_calls"),
        "usage": {
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "cache_hit_input_tokens": usage.get("cache_hit_input_tokens"),
            "cache_miss_input_tokens": usage.get("cache_miss_input_tokens"),
        },
        "model_mode": record.get("model_mode"),
        "model": record.get("model"),
        "provider": record.get("provider"),
        "error": error or None,
        "stage_usage": record.get("stage_usage", []),
        "attempts": record.get("attempts", []),
        "timing": record.get("timing", {}),
        "checks": record.get("checks", []),
        "online_checker_decision": (
            record["checks"][-1].get("accepted") if record.get("checks") else None
        ),
    }


class TeachingPreparedBackend:
    """Use one common real retrieval snapshot for A-D; do not send labels."""

    def __init__(
        self,
        study_folder: Path,
        preparation_path: Path,
        *,
        api_key: str,
        service_factory=GenerationService,
    ):
        manifest = load_frozen(study_folder)
        expected_hash = manifest["candidate"].get("teaching_retrieval_sha256")
        if not expected_hash or digest_bytes(preparation_path.read_bytes()) != expected_hash:
            raise ValueError("Teaching retrieval differs from the candidate freeze")
        prepared = json.loads(preparation_path.read_text(encoding="utf-8"))
        if prepared.get("provider_calls") != 0 or prepared.get("corpus_unchanged") is not True:
            raise ValueError("Prepared real retrieval has not passed its read-only checks")
        if prepared["corpus"]["release_id"] != manifest["candidate"]["corpus_release_id"]:
            raise ValueError("Teaching preparation uses a different corpus release")
        self.studies = {case["id"]: case for case in prepared["cases"]}
        self.public = {case["id"]: case for case in manifest["cases"]}
        self.study_folder = study_folder
        self.prepared = prepared
        self.api_key = api_key
        self.service_factory = service_factory

    def __call__(self, task: dict, arm: str, identity: str) -> dict:
        if arm not in ARMS:
            raise ValueError("The prepared teaching adapter supports A-D only")
        case_id, actual_arm = identity.rsplit("::", 1)
        if actual_arm != arm or self.public[case_id]["task"] != task:
            raise ValueError("Teaching task identity differs from the frozen schedule")
        prepared_case = self.studies[case_id]
        expected_chunk = self.public[case_id]["source_anchors"][0]["chunk_id"]
        if expected_chunk not in {
            item["chunk_id"] for item in prepared_case["retrieval"]["evidence"]
        }:
            raise ValueError("The intended official passage is absent from frozen retrieval")
        study_case = {
            **prepared_case,
            "question": prepared_case["question"],
            "task_type": "process_reasoning",
            "pending_question": "Which structure might provide a useful first clue?",
            "attempt": "I am considering the structure named in the clue.",
            "expected_response_kind": "explanation",
        }
        item = {
            "id": identity,
            "case_id": case_id,
            "stage": "first_hint",
            "arm": arm,
            "answer_mode": "textbook",
        }
        request = build_prior_study_request(
            item,
            {
                "cases": [study_case],
                "model_config": self.prepared["model_config"],
                "checker_config": self.prepared["checker_config"],
                "provider_output_policy": "strict_v1",
            },
        )
        context = {**(request.teaching_context or {}), "current_problem": prepared_case["question"]}
        query = {**(request.prepared_query or {}), "original_message": task["question"]}
        request = replace(
            request,
            request_id=identity,
            question=task["question"],
            prepared_query=query,
            teaching_context=context,
            generation_policy=freeze_generation_policy(arm),
        )
        event_path = (
            self.study_folder / "attempt-events" / (identity.replace("::", "--") + ".jsonl")
        )
        event_path.parent.mkdir(parents=True, exist_ok=True)

        def record_attempt(event: dict):
            with event_path.open("a", encoding="utf-8") as stream:
                stream.write(
                    canonical(
                        {"recorded_at_utc": datetime.now(timezone.utc).isoformat(), **event}
                    ).decode("utf-8")
                )
                stream.flush()

        limits = self.prepared.get("study_budget") or {}
        candidate_limits = load_frozen(self.study_folder)["candidate"]["budgets"]
        budget = RequestBudget(
            max_calls=min(
                int(candidate_limits.get("max_calls", 4)), int(limits.get("max_calls", 4))
            ),
            max_active_seconds=min(
                float(candidate_limits.get("max_active_seconds", 180)),
                float(limits.get("max_active_seconds", 180)),
            ),
        )
        outcome = self.service_factory(api_key=self.api_key, checker_api_key=self.api_key).generate(
            request, budget, on_attempt=record_attempt
        )
        return normalize_teaching_outcome(outcome)
