"""Reading-aware requirement extraction without changing frozen V3 requests."""

from __future__ import annotations

import re

from .requirements import describe_requirements as describe_requirements_v3
from .understanding import requirement_terms

VERSION = "question_requirements_v4"

_READING_PREFIX = re.compile(
    r"^\s*(?:according to|based on|using|in|from)\s+(?:this|the)\s+"
    r"(?:selected\s+)?(?:passage|paragraph|excerpt|text)\s*[,;:]\s*",
    re.I,
)
_READING_SUFFIX = re.compile(
    r"\s+(?:(?:in|from)\s+|(?:according to|based on)\s+)"
    r"(?:this|the)\s+(?:selected\s+)?"
    r"(?:passage|paragraph|excerpt|text)\s*[?.!]*\s*$",
    re.I,
)
_SOURCE_BOUND_REQUEST = re.compile(
    r"^\s*(?:please\s+)?(?:explain|summari[sz]e|clarify)\s+"
    r"(?:this|the)\s+(?:selected\s+)?(?:passage|paragraph|excerpt|text)\s*[?.!]*\s*$",
    re.I,
)


def describe_requirements(original, prepared, history=None):
    """Keep reader locators in retrieval/context, outside factual requirements.

    The frozen reading context already identifies the exact section and passage.
    Only a clear adjunct is removed; a question whose object is the passage
    itself remains unchanged for the checker to interpret.
    """
    if prepared.get("fallback_reason") != "verified_reading_selection":
        result = describe_requirements_v3(original, prepared, history)
        return {**result, "version": VERSION}

    normalized = _READING_PREFIX.sub("", original.strip())
    normalized = _READING_SUFFIX.sub("", normalized).strip()
    if not requirement_terms(normalized):
        normalized = original.strip()
    # The original question and frozen reader selection still enter the model
    # request. The section-augmented retrieval query is never a second user task.
    semantic_prepared = {**prepared, "standalone_query": normalized}
    result = describe_requirements_v3(original, semantic_prepared, history)
    source_bound = bool(_SOURCE_BOUND_REQUEST.fullmatch(original))
    if source_bound:
        # The object is the verified selected source itself. `paragraph` is a
        # reference, not a scientific term to search for in that source.
        points = [
            {
                **point,
                "terms": [],
                "origin": "verified_selected_source_referent_v1",
                "referent": "exact_selected_passage",
            }
            for point in result["required_knowledge"]
        ]
        result = {**result, "required_knowledge": points, "requested_facets": points}
    return {
        **result,
        "version": VERSION,
        "reader_reference_resolution": {
            "version": "frozen_reading_locator_v1",
            "status": "source_bound"
            if source_bound
            else "adjunct_removed"
            if normalized != original.strip()
            else "unchanged",
            "retrieval_query_kept_separate": True,
        },
    }
