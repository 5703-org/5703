"""Resolve owned practice references without rewriting frozen ordinary requests."""

from __future__ import annotations

import hashlib
import re

from .query import prepare_query
from . import (
    query_v14,
    query_v15,
    query_v16,
    query_v17,
    query_v18,
    query_v19,
    query_v20,
    query_v21,
    query_v22,
)
from .requirements_v4 import describe_requirements

VERSION = "owned_public_practice_query_v1"
CONTEXT_VERSION = "practice_tutor_context_v1"

_HELP_ONLY = re.compile(
    r"^(?:please\s+)?(?:"
    r"help(?:\s+me)?\s+(?:with\s+)?(?:the|this|my)\s+(?:current\s+)?(?:practice\s+)?step"
    r"(?:\s+without\s+(?:giving|revealing)(?:\s+me)?\s+(?:the\s+)?(?:answer|solution))?"
    r"|(?:give|show|provide|offer)(?:\s+me)?\s+(?:a|another|the|one)\s+hint"
    r"|(?:continue|another\s+hint|more\s+hint|full\s+explanation)"
    r")(?:\s+please)?[.!?]*$",
    re.I,
)


def freeze_policy(teaching_context):
    practice = (teaching_context or {}).get("practice_context")
    return (
        VERSION
        if isinstance(practice, dict) and practice.get("version") == CONTEXT_VERSION
        else None
    )


def resolve(question, prepared, teaching_context, *, policy, preparation_version):
    """Use public task facts as the referent; preserve the learner's literal turn.

    The caller validates the frozen owner, source, task and progress revision
    before this pure projection. Private grading material is never read here.
    Instruction-only hint requests are distinct from textbook knowledge points.
    A new substantive learner question remains in the factual requirements.
    """
    if policy is None:
        return None
    if policy != VERSION or freeze_policy(teaching_context) != VERSION:
        raise ValueError("The frozen practice query policy is unavailable")
    practice = teaching_context["practice_context"]
    prompt = practice.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("The frozen public practice problem is unavailable")
    step = practice.get("current_step_prompt")
    factual_problem = prompt
    if step:
        factual_problem += "\nCurrent practice step: " + step
    conditions = practice.get("conditions", [])
    if conditions:
        factual_problem += "\nGiven conditions:\n" + "\n".join(conditions)
    instruction_only = bool(_HELP_ONLY.fullmatch(question.strip())) or (
        teaching_context.get("turn_role") == "learner_attempt"
    )
    factual_request = factual_problem
    if not instruction_only:
        factual_request += "\nCurrent learner question: " + question
    query = factual_problem
    concepts = practice.get("concepts", [])
    if concepts:
        query += "\nPractice concepts: " + ", ".join(concepts)
    query += "\nCurrent learner request: " + question
    active_query_preparer = (
        query_v22.prepare_query
        if preparation_version == query_v22.VERSION
        else query_v21.prepare_query
        if preparation_version == query_v21.VERSION
        else query_v20.prepare_query
        if preparation_version == query_v20.VERSION
        else query_v19.prepare_query
        if preparation_version == query_v19.VERSION
        else query_v18.prepare_query
        if preparation_version == query_v18.VERSION
        else query_v17.prepare_query
        if preparation_version == query_v17.VERSION
        else query_v16.prepare_query
        if preparation_version == query_v16.VERSION
        else query_v15.prepare_query
        if preparation_version == query_v15.VERSION
        else query_v14.prepare_query
        if preparation_version == query_v14.VERSION
        else prepare_query
    )
    contextual_prepared = active_query_preparer(
        factual_request, [], version=preparation_version
    ).model_dump()
    contextual_prepared = {
        **contextual_prepared,
        "original_message": question,
        "standalone_query": query,
        "intent": "factual",
        "topic_relation": "same_topic",
        "referenced_message_ids": [],
        "needs_clarification": False,
        "fallback_reason": VERSION,
    }
    semantic_prepared = {**contextual_prepared, "standalone_query": factual_request}
    active_requirements = (
        query_v22.describe_requirements
        if preparation_version == query_v22.VERSION
        else query_v21.describe_requirements
        if preparation_version == query_v21.VERSION
        else query_v20.describe_requirements
        if preparation_version == query_v20.VERSION
        else query_v19.describe_requirements
        if preparation_version == query_v19.VERSION
        else query_v18.describe_requirements
        if preparation_version == query_v18.VERSION
        else query_v17.describe_requirements
        if preparation_version == query_v17.VERSION
        else query_v16.describe_requirements
        if preparation_version == query_v16.VERSION
        else query_v15.describe_requirements
        if preparation_version == query_v15.VERSION
        else query_v14.describe_requirements
        if preparation_version == query_v14.VERSION
        else describe_requirements
    )
    requirements = active_requirements(factual_request, semantic_prepared)
    literal = active_requirements(question, prepared)
    resolution = {
        "version": VERSION,
        "practice_item_id": practice["item_id"],
        "practice_progress_version": practice["progress_version"],
        "current_step": practice["current_step"],
        "source_unit_id": practice["source"]["source_unit_id"],
        "public_problem_sha256": hashlib.sha256(factual_problem.encode()).hexdigest(),
        "learner_request": question,
        "learner_request_constraints": literal["preserved_constraints"],
        "request_role": "teaching_instruction" if instruction_only else "knowledge_request",
        "scope": "Owned public practice reference; no semantic correctness or mastery label.",
    }
    requirements = {
        **requirements,
        "original_message": question,
        "original_question_hash": hashlib.sha256(question.encode()).hexdigest(),
        "standalone_query": query,
        "practice_reference_resolution": resolution,
    }
    return contextual_prepared, requirements
