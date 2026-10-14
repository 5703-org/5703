"""Workspace-scoped failure inspection with explicitly selected diagnostic fields."""

from datetime import datetime
import math
from typing import Literal, cast

from pydantic import Field
from sqlalchemy import func, or_, select

from contracts.models import Contract
from generation.provider_diagnostics import identifier
from app.core.errors import safe_message_for
from app.core.exceptions import AppError
from app.modules.answering.models import Answer, AnswerRequest, Attempt, Evidence, Job
from app.modules.identity.models import User
from app.modules.learning.models import ChatSession


class FailureCounts(Contract):
    candidates: int | None = None
    filtered: int | None = None
    submitted: int | None = None
    cited: int | None = None


class FailureModel(Contract):
    provider: str | None = None
    model: str | None = None
    configuration_id: str | None = None


class FailureSummary(Contract):
    request_id: str
    session_id: str | None = None
    owner_id: str
    question: str
    state: str
    response_type: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    model: FailureModel
    counts: FailureCounts


class FailurePage(Contract):
    items: list[FailureSummary]
    total: int
    limit: int
    offset: int


class FailureStage(Contract):
    stage: str
    status: str
    detail: str


class FailureProviderDiagnostic(Contract):
    stage: Literal["configuration", "network", "http", "decode", "validation", "completed"]
    http_status: int | None = None
    provider_error_type: str | None = None
    provider_error_code: str | None = None
    provider_error_parameter: str | None = None
    provider_request_id: str | None = None
    finish_reason: str | None = None
    network_error: Literal["dns", "tls", "connection", "timeout"] | None = None
    request_submitted: bool | None = None


class FailureAttempt(Contract):
    stage: str
    status: str
    error_code: str | None = None
    duration_ms: float | None = None
    created_at: datetime
    provider_diagnostic: FailureProviderDiagnostic | None = None


class FailureEvidence(Contract):
    candidate_chunk_ids: list[str] = Field(default_factory=list)
    submitted_chunk_ids: list[str] = Field(default_factory=list)
    cited_chunk_ids: list[str] = Field(default_factory=list)


class FailurePublicationBlock(Contract):
    """Allowlisted checker gate summary; never a model response or source excerpt."""

    version: Literal["semantic_publication_block_v1"]
    stop_reason: Literal[
        "final_recheck_rejected",
        "active_time_exhausted",
        "insufficient_calls_for_repair_and_recheck",
    ]
    remaining_provider_calls: int = Field(ge=0, le=4)
    required_calls_for_repair_and_recheck: int = Field(ge=0, le=2)
    checker_contract_repair_calls: int = Field(ge=0, le=4)
    checker_reported_body_ok: bool
    checker_reported_non_supported_factual_claims: int = Field(ge=0, le=100)
    failed_checker_gate_names: list[str] = Field(max_length=12)
    checker_reported_coverage: Literal["full", "supported_partial", "none"]
    requirement_issue_codes: list[str] = Field(max_length=16)
    structural_issue_codes: list[str] = Field(max_length=16)


class ProcessingFacet(Contract):
    id: str | None = None
    request: str | None = None
    terms: list[str] = Field(default_factory=list)


class ProcessingCorrection(Contract):
    replacement: str | None = None
    excluded: list[str] = Field(default_factory=list)
    prior_question: str | None = None


class ProcessingUnderstanding(Contract):
    standalone_query: str | None = None
    intent: str | None = None
    topic_relation: str | None = None
    needs_clarification: bool | None = None
    clarification_reason: str | None = None
    requested_facets: list[ProcessingFacet] = Field(default_factory=list)
    comparison_targets: list[str] = Field(default_factory=list)
    negation: list[str] = Field(default_factory=list)
    numbers: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    correction: ProcessingCorrection | None = None
    method: str | None = None
    limitations: list[str] = Field(default_factory=list)


class ProcessingExclusion(Contract):
    chunk_id: str | None = None
    reason: str
    stage: Literal["relevance", "budget", "reuse"]
    score: float | None = None


class ProcessingCoverage(Contract):
    version: str | None = None
    status: Literal["none", "partial", "full"] | None = None
    uncovered_facet_ids: list[str] = Field(default_factory=list)
    scope: str = "Lexical request coverage; independent support review remains separate."


class ProcessingPacking(Contract):
    version: str | None = None
    text_token_ceiling: int | None = None
    duplicate_count: int | None = None


class ProcessingCitationAudit(Contract):
    version: str | None = None
    status: Literal["review_required", "no_heuristic_flags", "not_applicable"] | None = None
    flag_count: int | None = None


class ProcessingReuse(Contract):
    available_count: int | None = None
    eligible_count: int | None = None
    rescored_chunk_ids: list[str] = Field(default_factory=list)


class ProcessingTeaching(Contract):
    level: str | None = None
    style: str | None = None
    mode: str | None = None


class ProcessingProgressPlan(Contract):
    version: str | None = None
    enabled: bool | None = None
    arm: Literal["A", "B", "C", "D"] | None = None
    content_plan: bool | None = None
    display_selection: bool | None = None
    current_step: int | None = None
    action: (
        Literal[
            "complete_explanation",
            "locate_error",
            "recall_concept",
            "split_step",
            "check_understanding",
            "assess_then_adapt",
            "assess_then_reduce_step",
            "assess_then_guarded_small_step",
            "reduce_step",
            "complete_missing_reason",
            "transfer_or_explain",
        ]
        | None
    ) = None
    allowed_disclosure: str | None = None
    expected_response_kind: str | None = None
    previous_delivered_turn_count: int | None = None


class ProcessingContextCoverage(Contract):
    version: str | None = None
    estimate: Literal["lexically_complete", "partial", "none"] | None = None
    required_count: int | None = None
    missing_requirement_ids: list[str] = Field(default_factory=list)
    distributed_requirement_ids: list[str] = Field(default_factory=list)
    budget_lost_requirement_ids: list[str] = Field(default_factory=list)
    supplementary_retrieval_passes: int | None = None
    supplementary_added_count: int | None = None
    semantic_status: (
        Literal["sufficient", "partial", "absent", "conflicting", "not_applicable"] | None
    ) = None
    semantic_method: Literal["online_checker_model"] | None = None
    semantic_missing_requirement_ids: list[str] = Field(default_factory=list)
    independent_semantic_evaluation: bool = False
    candidate_coverage: dict | None = None
    semantic_sufficiency: dict | None = None
    claim_support: dict | None = None


class ProcessingFacetAttempt(Contract):
    facet_id: str | None = None
    query: str | None = None
    candidate_count: int | None = None
    accepted_count: int | None = None
    accepted_chunk_ids: list[str] = Field(default_factory=list)
    model: str | None = None
    revision: str | None = None
    excluded: list[ProcessingExclusion] = Field(default_factory=list)


class ProcessingFacetFallback(Contract):
    triggered: bool | None = None
    reason: str | None = None
    policy_version: str | None = None
    whole_query_candidate_count: int | None = None
    whole_query_accepted_count: int | None = None
    elapsed_ms: float | None = None
    attempted_facets: list[ProcessingFacetAttempt] = Field(default_factory=list)
    accepted_chunk_ids: list[str] = Field(default_factory=list)


class ProcessingMemory(Contract):
    status: Literal["ready", "disabled", "unavailable"]
    policy_version: str | None = None
    error_code: str | None = None
    semantic_status: str | None = None
    candidate_count: int | None = None
    selected_count: int | None = None
    source_reread_count: int | None = None


class FailureProcessing(Contract):
    understanding: ProcessingUnderstanding
    corpus_release_id: str | None = None
    requested_device: str | None = None
    resolved_device: str | None = None
    relevance_policy: str | None = None
    relevance_minimum_logit: float | None = None
    reranker_model: str | None = None
    excluded: list[ProcessingExclusion] = Field(default_factory=list)
    exclusions_truncated: bool = False
    timing_ms: dict[str, float] = Field(default_factory=dict)
    timing_scope: str | None = None
    coverage: ProcessingCoverage | None = None
    packing: ProcessingPacking | None = None
    citation_audit: ProcessingCitationAudit | None = None
    reuse: ProcessingReuse | None = None
    teaching: ProcessingTeaching | None = None
    facet_fallback: ProcessingFacetFallback | None = None
    selection_source: Literal["whole_query", "facet_fallback"] | None = None
    memory: ProcessingMemory | None = None
    progress_plan: ProcessingProgressPlan | None = None
    context_coverage: ProcessingContextCoverage | None = None


class FailureDetail(FailureSummary):
    http_trace_id: str | None = None
    stages: list[FailureStage]
    budget: dict[str, int | float]
    attempts: list[FailureAttempt]
    retrieval_query: str | None = None
    evidence: FailureEvidence
    answer_text: str | None = None
    refusal_reason: str | None = None
    processing: FailureProcessing | None = None
    publication_block: FailurePublicationBlock | None = None


FailureFilter = Literal["all", "error", "refused", "clarification", "cancelled", "answered"]


def scoped_requests(actor):
    return (
        select(AnswerRequest)
        .join(User, AnswerRequest.owner_id == User.id)
        .outerjoin(ChatSession, AnswerRequest.session_id == ChatSession.id)
        .where(
            User.workspace_id == actor.workspace_id,
            AnswerRequest.mode == "interactive_chat",
            or_(AnswerRequest.session_id.is_(None), ChatSession.deleted_at.is_(None)),
        )
    )


def _text(value, limit=160):
    return value[:limit] if isinstance(value, str) else None


def _count(value):
    return value if type(value) is int and value >= 0 else None


def _dict(value):
    return value if isinstance(value, dict) else {}


_PUBLICATION_GATE_NAMES = frozenset(
    {
        "body_ok",
        "attempt_evaluation_ok",
        "tutor_question_ok",
        "specific_help",
        "scope_ok",
        "suggestions_ok",
        "evidence_display_ok",
        "cumulative_ok",
        "complete_answer",
        "limitations_explicit",
    }
)
_PUBLICATION_ISSUE_CODES = frozenset(
    {
        "ACTUAL_CITATION_ASSESSMENT_MISSING",
        "ACTUAL_CITATION_FRAGMENT_INVALID",
        "ACTUAL_CITATION_FRAGMENT_MISSING",
        "ACTUAL_CITATION_IRRELEVANT",
        "ACTUAL_CITATION_CONTRADICTORY",
        "UNEXPECTED_CITATION_FOR_BASIS",
        "CHECK_CITATION_SOURCE_MISMATCH",
        "CHECK_DERIVATION_INVALID",
        "CHECK_GENERAL_KNOWLEDGE_BASIS_INVALID",
        "CHECK_LIMITATION_BASIS_INVALID",
        "CHECK_PROBLEM_QUOTE_MISMATCH",
        "CHECK_SUPPORT_WITHOUT_SOURCE",
        "CHECK_INCOMPLETE_ATOMIC_BLOCK",
        "CHECK_UNDISPLAYED_SUPPORT",
        "REQUIREMENT_CONDITION_LOST",
        "REQUIRED_CONTENT_OMITTED",
        "SUFFICIENT_CONTEXT_UNDERUSED",
        "INSUFFICIENT_CONTEXT_FULL_COVERAGE",
        "REQUIREMENT_LIMITATION_MISSING",
        "TUTOR_ACTION_REPEATS_DISCLOSED_ANSWER",
    }
)


def publication_block_projection(error):
    """Expose only bounded known checker status values to the admin endpoint."""
    error = _dict(error)
    data = _dict(_dict(error.get("details")).get("publication_block"))
    if error.get("code") != "SEMANTIC_CHECK_FAILED" or data.get("version") != (
        "semantic_publication_block_v1"
    ):
        return None
    if not isinstance(data.get("stop_reason"), str) or data["stop_reason"] not in {
        "final_recheck_rejected",
        "active_time_exhausted",
        "insufficient_calls_for_repair_and_recheck",
    }:
        return None
    if not isinstance(data.get("checker_reported_coverage"), str) or data[
        "checker_reported_coverage"
    ] not in {"full", "supported_partial", "none"}:
        return None
    count_names = (
        "remaining_provider_calls",
        "required_calls_for_repair_and_recheck",
        "checker_contract_repair_calls",
        "checker_reported_non_supported_factual_claims",
    )
    counts = {name: _count(data.get(name)) for name in count_names}
    if any(value is None for value in counts.values()) or any(
        counts[name] > limit for name, limit in zip(count_names, (4, 2, 4, 100), strict=True)
    ):
        return None
    if type(data.get("checker_reported_body_ok")) is not bool:
        return None

    def known(values, allowed, limit):
        if not isinstance(values, list):
            return []
        return list(dict.fromkeys(v for v in values[:64] if isinstance(v, str) and v in allowed))[
            :limit
        ]

    return FailurePublicationBlock(
        version="semantic_publication_block_v1",
        stop_reason=data["stop_reason"],
        **counts,
        checker_reported_body_ok=data["checker_reported_body_ok"],
        failed_checker_gate_names=known(
            data.get("failed_checker_gate_names"), _PUBLICATION_GATE_NAMES, 12
        ),
        checker_reported_coverage=data["checker_reported_coverage"],
        requirement_issue_codes=known(
            data.get("requirement_issue_codes"), _PUBLICATION_ISSUE_CODES, 16
        ),
        structural_issue_codes=known(
            data.get("structural_issue_codes"), _PUBLICATION_ISSUE_CODES, 16
        ),
    )


def _strings(value):
    return (
        list(dict.fromkeys(v[:160] for v in value if isinstance(v, str)))
        if isinstance(value, list)
        else []
    )


def _finite(value, *, nonnegative=False):
    if type(value) not in (int, float):
        return None
    try:
        number = float(value)
    except (ValueError, OverflowError):
        return None
    if not math.isfinite(number):
        return None
    return number if not nonnegative or number >= 0 else None


def _limited_strings(value):
    return [item[:240] for item in _strings(value)[:24]]


def _relevance(trace):
    return _dict(_dict(trace.get("retrieval_execution")).get("relevance_gate"))


def _final_selection(trace):
    return _dict(_dict(trace.get("retrieval_execution")).get("final_selection"))


def processing_projection(req, answer):
    """Project named observations only; never expose arbitrary trace/configuration JSON."""
    trace = _dict(req.trace)
    prepared = _dict(trace.get("prepared_query"))
    understanding = _dict(trace.get("understanding")) or _dict(prepared.get("understanding"))
    constraints = _dict(understanding.get("constraints"))
    correction = _dict(understanding.get("correction"))
    facets = understanding.get("requested_facets")
    execution = _dict(trace.get("local_model_execution"))
    gate = _relevance(trace)
    policy = _dict(gate.get("policy"))
    selection = _dict(trace.get("evidence_selection"))
    token_budget = _dict(trace.get("token_budget"))
    coverage = _dict(trace.get("coverage_estimate")) or _dict(token_budget.get("coverage_estimate"))
    packing = _dict(trace.get("evidence_packing")) or _dict(token_budget.get("evidence_packing"))
    audit = _dict(trace.get("citation_audit")) or _dict(token_budget.get("citation_audit"))
    teaching = _dict(trace.get("teaching_plan")) or _dict(token_budget.get("teaching_plan"))
    progress = _dict(trace.get("progress_plan")) or _dict(token_budget.get("progress_plan"))
    progress_flags = _dict(progress.get("policy_flags"))
    context_coverage = _dict(trace.get("context_coverage")) or _dict(
        token_budget.get("context_coverage")
    )
    final_coverage = _dict(context_coverage.get("packed_coverage")) or _dict(
        context_coverage.get("candidate_coverage")
    )
    retrieval = _dict(trace.get("retrieval_execution"))
    inherited = _dict(retrieval.get("inherited_evidence"))
    merged = _dict(retrieval.get("candidate_merge"))
    fallback = _dict(retrieval.get("facet_fallback"))
    supplement = _dict(retrieval.get("coverage_supplement"))
    final_selection = _final_selection(trace)
    memory_stage = _dict(trace.get("memory_stage"))
    safe_reasons = {
        "expanded_concept_absent",
        "below_relevance_threshold",
        "exact_duplicate",
        "contained_duplicate",
        "evidence_ceiling",
        "whole_window_limit",
        "token_budget",
        "unconfirmed_inherited",
        "token_budget_exceeded",
        "evidence_token_limit",
        "source_unavailable",
        "outside_frozen_release",
        "source_identity_mismatch",
        "candidate_limit",
        "inherited_limit",
    }
    excluded = []
    for stage, values in [
        ("relevance", gate.get("excluded")),
        ("budget", selection.get("excluded_evidence", token_budget.get("excluded_evidence"))),
        ("reuse", inherited.get("excluded")),
        ("reuse", merged.get("excluded")),
    ]:
        for item in values if isinstance(values, list) else []:
            row = _dict(item)
            reason = row.get("reason")
            excluded.append(
                ProcessingExclusion(
                    chunk_id=_text(row.get("chunk_id")),
                    reason=reason
                    if isinstance(reason, str) and reason in safe_reasons
                    else "unrecorded_reason",
                    stage=cast(Literal["relevance", "budget", "reuse"], stage),
                    score=_finite(row.get("score")),
                )
            )
    for chunk_id in _strings(gate.get("unconfirmed_inherited_chunk_ids")):
        excluded.append(
            ProcessingExclusion(chunk_id=chunk_id, reason="unconfirmed_inherited", stage="reuse")
        )
    timings = _dict(answer.timing) if answer else {}
    # Answer timings are authoritative; the old aggregate preparation_ms includes retrieval.
    if not timings:
        timings = _dict(trace.get("stage_timing"))
    timing_keys = {
        "preparation_ms",
        "query_preparation_ms",
        "retrieval_ms",
        "generation_wall_ms",
        "adapter_ms",
        "validation_ms",
        "total_ms",
        "queue_ms",
        "token_count_ms",
        "teaching_plan_ms",
        "submission_to_worker_start_ms",
    }
    timing_ms = {
        key: number
        for key, value in timings.items()
        if key in timing_keys and (number := _finite(value, nonnegative=True)) is not None
    }
    clarification = understanding.get("needs_clarification", prepared.get("needs_clarification"))
    fallback_attempts = fallback.get("attempted_facets")
    safe_fallback_attempts = []
    for item in fallback_attempts[:2] if isinstance(fallback_attempts, list) else []:
        attempt = _dict(item)
        rejected = attempt.get("excluded")
        safe_fallback_attempts.append(
            ProcessingFacetAttempt(
                facet_id=_text(attempt.get("facet_id")),
                query=_text(attempt.get("query"), 4000),
                candidate_count=_count(attempt.get("candidate_count")),
                accepted_count=_count(attempt.get("accepted_count")),
                accepted_chunk_ids=_limited_strings(attempt.get("accepted_chunk_ids"))[:20],
                model=_text(attempt.get("model")),
                revision=_text(attempt.get("revision")),
                excluded=[
                    ProcessingExclusion(
                        chunk_id=_text(_dict(row).get("chunk_id")),
                        reason=_dict(row).get("reason")
                        if _dict(row).get("reason")
                        in ("expanded_concept_absent", "below_relevance_threshold")
                        else "unrecorded_reason",
                        stage="relevance",
                        score=_finite(_dict(row).get("score")),
                    )
                    for row in (rejected[:20] if isinstance(rejected, list) else [])
                ],
            )
        )
    return FailureProcessing(
        memory=ProcessingMemory(
            status=memory_stage["status"],
            policy_version=identifier(memory_stage.get("policy_version")),
            error_code=identifier(memory_stage.get("error_code") or memory_stage.get("code")),
            semantic_status=identifier(memory_stage.get("semantic_status")),
            candidate_count=_count(memory_stage.get("candidate_count")),
            selected_count=_count(memory_stage.get("selected_count")),
            source_reread_count=_count(memory_stage.get("source_reread_count")),
        )
        if memory_stage.get("status") in {"ready", "disabled", "unavailable"}
        else None,
        progress_plan=ProcessingProgressPlan(
            version=identifier(progress.get("version")),
            enabled=progress.get("enabled") if type(progress.get("enabled")) is bool else None,
            arm=progress_flags.get("arm")
            if progress_flags.get("arm") in {"A", "B", "C", "D"}
            else None,
            content_plan=progress_flags.get("content_plan")
            if type(progress_flags.get("content_plan")) is bool
            else None,
            display_selection=progress_flags.get("display_selection")
            if type(progress_flags.get("display_selection")) is bool
            else None,
            current_step=_count(progress.get("current_step")),
            action=progress.get("action")
            if progress.get("action")
            in {
                "complete_explanation",
                "locate_error",
                "recall_concept",
                "split_step",
                "check_understanding",
                "assess_then_adapt",
                "assess_then_reduce_step",
                "assess_then_guarded_small_step",
                "reduce_step",
                "complete_missing_reason",
                "transfer_or_explain",
            }
            else None,
            allowed_disclosure=_text(
                _dict(progress.get("allowed_disclosure")).get("constraint"), 1000
            ),
            expected_response_kind=identifier(
                _dict(progress.get("expected_learner_reply")).get("kind")
            ),
            previous_delivered_turn_count=_count(progress.get("previous_delivered_turn_count")),
        )
        if progress
        else None,
        context_coverage=ProcessingContextCoverage(
            version=identifier(context_coverage.get("version")),
            estimate=context_coverage.get("context_sufficiency_estimate")
            if context_coverage.get("context_sufficiency_estimate")
            in {"lexically_complete", "partial", "none"}
            else None,
            required_count=len(final_coverage.get("requirements", []))
            if isinstance(final_coverage.get("requirements"), list)
            else None,
            missing_requirement_ids=_limited_strings(final_coverage.get("missing_requirement_ids"))[
                :8
            ],
            distributed_requirement_ids=_limited_strings(
                context_coverage.get("distributed_requirement_ids")
            )[:8],
            budget_lost_requirement_ids=_limited_strings(
                context_coverage.get("budget_lost_requirement_ids")
            )[:8],
            supplementary_retrieval_passes=_count(supplement.get("retrieval_passes")),
            supplementary_added_count=len(supplement.get("added_chunk_ids", []))
            if isinstance(supplement.get("added_chunk_ids"), list)
            else None,
            semantic_status=_dict(context_coverage.get("semantic_sufficiency")).get("status")
            if _dict(context_coverage.get("semantic_sufficiency")).get("status")
            in {"sufficient", "partial", "absent", "conflicting", "not_applicable"}
            else None,
            semantic_method="online_checker_model"
            if _dict(context_coverage.get("semantic_sufficiency")).get("method")
            == "online_checker_model"
            else None,
            semantic_missing_requirement_ids=[
                identifier(row.get("requirement_id"))
                for row in _dict(context_coverage.get("semantic_sufficiency")).get(
                    "requirements", []
                )
                if isinstance(row, dict)
                and row.get("sufficiency") in {"partial", "absent", "conflicting"}
                and identifier(row.get("requirement_id"))
            ],
            candidate_coverage={
                "version": identifier(context_coverage.get("version")),
                "method": identifier(context_coverage.get("estimate_method")),
                "status": identifier(
                    _dict(context_coverage.get("candidate_coverage")).get("status")
                ),
                "semantic_certification": False,
            },
            semantic_sufficiency={
                "version": identifier(
                    _dict(context_coverage.get("semantic_sufficiency")).get("version")
                ),
                "method": "online_checker_model",
                "status": identifier(
                    _dict(context_coverage.get("semantic_sufficiency")).get("status")
                ),
                "independent_evaluation": False,
            }
            if context_coverage.get("semantic_sufficiency")
            else None,
            claim_support={
                "version": identifier(_dict(token_budget.get("claim_support")).get("version")),
                "accepted": _dict(token_budget.get("claim_support")).get("accepted"),
                "factual_claim_count": _count(
                    _dict(token_budget.get("claim_support")).get("factual_claim_count")
                ),
                "textbook_status_counts": {
                    key: _count(
                        _dict(
                            _dict(token_budget.get("claim_support")).get("textbook_status_counts")
                        ).get(key)
                    )
                    for key in ("supported", "partial", "unsupported")
                },
                "independent_evaluation": False,
            }
            if token_budget.get("claim_support")
            else None,
        )
        if context_coverage
        else None,
        understanding=ProcessingUnderstanding(
            standalone_query=_text(
                understanding.get("standalone_query")
                or prepared.get("standalone_query")
                or prepared.get("retrieval_query")
                or prepared.get("query"),
                4000,
            ),
            intent=_text(understanding.get("intent") or prepared.get("intent")),
            topic_relation=_text(
                understanding.get("topic_relation") or prepared.get("topic_relation")
            ),
            needs_clarification=clarification if type(clarification) is bool else None,
            clarification_reason=_text(
                understanding.get("clarification_reason") or prepared.get("fallback_reason"), 240
            ),
            requested_facets=[
                ProcessingFacet(
                    id=_text(_dict(row).get("id")),
                    request=_text(_dict(row).get("request"), 400),
                    terms=_limited_strings(_dict(row).get("terms")),
                )
                for row in (facets[:12] if isinstance(facets, list) else [])
            ],
            comparison_targets=_limited_strings(understanding.get("comparison_targets")),
            negation=_limited_strings(constraints.get("negation")),
            numbers=_limited_strings(constraints.get("numbers")),
            conditions=_limited_strings(constraints.get("conditions")),
            correction=ProcessingCorrection(
                replacement=_text(correction.get("replacement"), 400),
                excluded=_limited_strings(
                    [correction["excluded"]]
                    if isinstance(correction.get("excluded"), str)
                    else correction.get("excluded")
                ),
                prior_question=_text(correction.get("prior_question"), 4000),
            )
            if correction
            else None,
            method=_text(understanding.get("method")),
            limitations=_limited_strings(understanding.get("limitations")),
        ),
        corpus_release_id=_text(req.release_id),
        requested_device=_text(
            execution.get("requested_device") or _dict(req.command).get("local_model_device")
        ),
        resolved_device=_text(execution.get("resolved_device")),
        relevance_policy=_text(policy.get("version")),
        relevance_minimum_logit=_finite(policy.get("minimum_logit")),
        reranker_model=_text(policy.get("reranker_model")),
        excluded=excluded[:100],
        exclusions_truncated=len(excluded) > 100,
        timing_ms=timing_ms,
        timing_scope=_text(timings.get("timing_scope")),
        coverage=ProcessingCoverage(
            version=_text(coverage.get("version")),
            status=coverage.get("status")
            if coverage.get("status") in ("none", "partial", "full")
            else None,
            uncovered_facet_ids=_limited_strings(coverage.get("uncovered_facet_ids")),
        )
        if coverage
        else None,
        packing=ProcessingPacking(
            version=_text(packing.get("version")),
            text_token_ceiling=_count(packing.get("text_token_ceiling")),
            duplicate_count=_count(packing.get("duplicate_count")),
        )
        if packing
        else None,
        citation_audit=ProcessingCitationAudit(
            version=_text(audit.get("version")),
            status=audit.get("status")
            if audit.get("status") in ("review_required", "no_heuristic_flags", "not_applicable")
            else None,
            flag_count=_count(audit.get("flag_count")),
        )
        if audit
        else None,
        reuse=ProcessingReuse(
            available_count=_count(inherited.get("available_count")),
            eligible_count=_count(inherited.get("eligible_count")),
            rescored_chunk_ids=_limited_strings(inherited.get("rescored_chunk_ids")),
        )
        if inherited
        else None,
        teaching=ProcessingTeaching(
            level=_text(teaching.get("level")),
            style=_text(teaching.get("style")),
            mode=_text(teaching.get("mode")),
        )
        if teaching
        else None,
        facet_fallback=ProcessingFacetFallback(
            triggered=fallback.get("triggered")
            if type(fallback.get("triggered")) is bool
            else None,
            reason=fallback.get("reason")
            if fallback.get("reason")
            in (
                "whole_query_accepted",
                "policy_unavailable",
                "insufficient_explicit_facets",
                "no_meaningful_facets",
                "fallback_completed",
                "budget_exhausted",
            )
            else None,
            policy_version=_text(_dict(fallback.get("policy")).get("version")),
            whole_query_candidate_count=_count(gate.get("candidate_count")),
            whole_query_accepted_count=_count(gate.get("accepted_count")),
            elapsed_ms=_finite(fallback.get("elapsed_ms"), nonnegative=True),
            attempted_facets=safe_fallback_attempts,
            accepted_chunk_ids=_limited_strings(fallback.get("accepted_chunk_ids"))[:20],
        )
        if fallback
        else None,
        selection_source=final_selection.get("source")
        if final_selection.get("source") in ("whole_query", "facet_fallback")
        else None,
    )


def summarize(db, req):
    answer = db.scalar(select(Answer).where(Answer.request_id == req.id))
    job = db.scalar(
        select(Job).where(Job.request_id == req.id).order_by(Job.created_at.desc(), Job.id.desc())
    )
    response = _dict(answer.response) if answer else {}
    error = _dict(job.error) if job else {}
    trace = _dict(req.trace)
    selection = _dict(trace.get("evidence_selection"))
    candidates = trace.get("retrieval_candidates")
    evidence = (
        list(db.scalars(select(Evidence).where(Evidence.answer_id == answer.id))) if answer else []
    )
    submitted_ids = _strings(selection.get("submitted_evidence_ids"))
    cited_ids = _strings(response.get("citations"))
    model = _dict(_dict(req.command).get("model_config"))
    counts = FailureCounts(
        candidates=_count(selection.get("candidate_count")),
        submitted=_count(selection.get("submitted_count")),
        cited=_count(selection.get("cited_count")),
    )
    gate = _relevance(trace)
    if _count(gate.get("candidate_count")) is not None:
        counts.candidates = _count(gate.get("candidate_count"))
    counts.filtered = _count(gate.get("accepted_count"))
    if counts.candidates is None and isinstance(candidates, list):
        counts.candidates = len(candidates)
    final_selection = _final_selection(trace)
    if final_selection:
        # The final path has its own distinct candidate pool. Whole-query work is
        # retained separately; summing per-facet counts double-counts overlaps.
        counts.candidates = _count(final_selection.get("candidate_count"))
        counts.filtered = _count(final_selection.get("accepted_count"))
    if counts.submitted is None and (answer or submitted_ids):
        counts.submitted = len(evidence) if answer else len(submitted_ids)
    if answer:
        counts.cited = len(cited_ids)
    code = _text(error.get("code"))
    summary = FailureSummary(
        request_id=req.id,
        session_id=req.session_id,
        owner_id=req.owner_id,
        question=_text(_dict(req.command).get("question"), 4000) or "",
        state=req.state,
        response_type=_text(response.get("response_type")),
        error_code=code,
        # Provider/transport text can contain credentials or response bodies.
        error_message=safe_message_for(code) if code else None,
        created_at=req.created_at,
        model=FailureModel(
            **{k: _text(model.get(k)) for k in ("provider", "model", "configuration_id")}
        ),
        counts=counts,
    )
    return summary, answer, job, evidence


def list_failures(db, actor, limit=50, offset=0, state=None):
    query = scoped_requests(actor)
    if state != "all":
        query = (
            query.where(AnswerRequest.state == state)
            if state
            else query.where(
                AnswerRequest.state.in_(["error", "refused", "clarification", "cancelled"])
            )
        )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(AnswerRequest.created_at.desc(), AnswerRequest.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return FailurePage(
        items=[summarize(db, row)[0] for row in rows], total=total, limit=limit, offset=offset
    )


def failure_detail(db, actor, request_id):
    req = db.scalar(scoped_requests(actor).where(AnswerRequest.id == request_id))
    if not req:
        raise AppError("NOT_FOUND")
    summary, answer, job, stored = summarize(db, req)
    trace = _dict(req.trace)
    selection = _dict(trace.get("evidence_selection"))
    candidates = trace.get("retrieval_candidates")
    candidate_ids = _strings(selection.get("candidate_chunk_ids"))
    gate = _relevance(trace)
    if _count(gate.get("candidate_count")) is not None:
        excluded_rows = gate.get("excluded")
        candidate_ids = (
            _strings(
                _strings(gate.get("accepted_chunk_ids"))
                + [
                    _dict(row).get("chunk_id")
                    for row in (excluded_rows if isinstance(excluded_rows, list) else [])
                ]
            )
            or candidate_ids
        )
    if not candidate_ids and isinstance(candidates, list):
        candidate_ids = _strings([_dict(item).get("chunk_id") for item in candidates])
    final_selection = _final_selection(trace)
    if final_selection:
        candidate_ids = _strings(final_selection.get("candidate_chunk_ids"))
    response = _dict(answer.response) if answer else {}
    cited_ids = _strings(response.get("citations"))
    prepared = _dict(trace.get("prepared_query"))
    attempts = []
    records = db.scalars(
        select(Attempt)
        .join(Job, Attempt.job_id == Job.id)
        .where(Job.request_id == req.id)
        .order_by(Attempt.created_at, Attempt.sequence)
    )
    for record in records:
        payload = _dict(record.payload)
        error = _dict(payload.get("error"))
        elapsed = payload.get("latency_ms")
        attempts.append(
            FailureAttempt(
                stage=_text(payload.get("stage")) or "generation",
                status="error" if error else (_text(payload.get("phase")) or "recorded"),
                error_code=_text(error.get("code")),
                duration_ms=elapsed if type(elapsed) in (int, float) and elapsed >= 0 else None,
                created_at=record.created_at,
                provider_diagnostic=provider_projection(payload.get("diagnostic")),
            )
        )
    count = summary.counts
    stages = [
        FailureStage(
            stage="query",
            status="recorded" if prepared else "unavailable",
            detail=_text(prepared.get("intent")) or "Question preparation",
        ),
        FailureStage(
            stage="retrieval",
            status="recorded" if count.candidates is not None else "unavailable",
            detail=f"Candidate passages: {count.candidates}"
            if count.candidates is not None
            else "Candidate count was not recorded",
        ),
        FailureStage(
            stage="evidence",
            status="recorded" if count.submitted is not None else "unavailable",
            detail=f"Submitted passages: {count.submitted}"
            if count.submitted is not None
            else "Submitted count was not recorded",
        ),
        FailureStage(
            stage=job.stage if job else "request",
            status=job.state if job else req.state,
            detail=summary.error_message or summary.response_type or req.state,
        ),
    ]
    budget = {
        k: v
        for k, v in _dict(req.budget).items()
        if k
        in {
            "consumed_calls",
            "active_seconds",
            "format_repairs",
            "transient_retries",
            "max_calls",
            "max_active_seconds",
        }
        and type(v) in (int, float)
    }
    return FailureDetail(
        **summary.model_dump(),
        http_trace_id=_text(trace.get("http_trace_id")),
        stages=stages,
        budget=budget,
        attempts=attempts,
        retrieval_query=_text(
            prepared.get("standalone_query")
            or prepared.get("retrieval_query")
            or prepared.get("query"),
            4000,
        ),
        evidence=FailureEvidence(
            candidate_chunk_ids=candidate_ids,
            submitted_chunk_ids=[item.chunk_id for item in stored]
            or _strings(selection.get("submitted_chunk_ids")),
            cited_chunk_ids=[item.chunk_id for item in stored if item.evidence_id in cited_ids],
        ),
        answer_text=_text(response.get("answer_text"), 30000),
        refusal_reason=_text(response.get("refusal_reason")),
        processing=processing_projection(req, answer),
        publication_block=publication_block_projection(job.error if job else None),
    )


def provider_projection(value):
    """Select typed transport observations; omit echoed messages and response bodies."""
    data = _dict(value)
    if data.get("stage") not in {
        "configuration",
        "network",
        "http",
        "decode",
        "validation",
        "completed",
    }:
        return None
    status = data.get("http_status")
    return FailureProviderDiagnostic(
        stage=data["stage"],
        http_status=status if type(status) is int and 100 <= status <= 599 else None,
        **{
            name: identifier(data.get(name))
            for name in (
                "provider_error_type",
                "provider_error_code",
                "provider_error_parameter",
                "provider_request_id",
                "finish_reason",
            )
        },
        network_error=data.get("network_error")
        if data.get("network_error") in {"dns", "tls", "connection", "timeout"}
        else None,
        request_submitted=data.get("request_submitted")
        if type(data.get("request_submitted")) is bool
        else None,
    )
