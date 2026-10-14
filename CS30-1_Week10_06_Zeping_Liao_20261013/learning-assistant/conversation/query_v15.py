"""Conservative current-clause anchors without inferred historical subjects.

V14 remains the frozen dependency for named possessive anchors and history.
Only its source-content fallback is narrowed here: a complete primary request
must name content before a secondary request, and the primary request must not
itself point to missing discourse. This is bounded syntax, not general semantic
coreference. Bare source questions and adjective-only generic subjects remain
eligible for the historical clarification path.
"""

from __future__ import annotations

import re
from typing import Any

from contracts.models import PreparedQuery

from . import query as historical
from . import query_v14 as previous

VERSION = "conversation_preparer_v15"
BASE_VERSION = "conversation_preparer_v14"

SOURCE_POINTER = re.compile(
    r"\b(?:original|previous|prior|earlier|latest|above|below|mentioned|aforementioned|"
    r"cited|preceding|following)"
    r"(?:\s+(?:mentioned|given|provided|quoted|cited|listed|shown)){0,2}\s+sources?\b",
    re.I,
)
SECONDARY_REQUEST = re.compile(
    r"[,;.!?]\s*(?:(?:and\s+)?then|also|additionally)?\s*"
    r"(?:explain|describe|compare|distinguish|identify|trace|follow|determine)\b",
    re.I,
)
PRIMARY_REQUEST = re.compile(
    r"^(?:please\s+)?(?:explain|describe|compare|trace|follow|calculate|determine|identify)"
    r"\s+(.+)$",
    re.I,
)
PRIMARY_DISCOURSE_POINTER = re.compile(
    r"\b(?:original|previous|prior|earlier|latest|above|below|mentioned|aforementioned|"
    r"cited|preceding|following)\b|"
    r"\b(?:previously|earlier|already)\s+"
    r"(?:mentioned|described|stated|given|provided|discussed|quoted|listed|shown)\b",
    re.I,
)
PRIMARY_PREPOSITION = re.compile(
    r"\b(?:from|to|through|across|within|between|into|of|about|under|over|in|on|at|"
    r"with|without|for)\b",
    re.I,
)
GENERIC_HEADS = previous.ANCHOR_GRAMMAR | {
    "mechanism",
    "mechanisms",
    "method",
    "methods",
    "phenomenon",
    "phenomena",
    "system",
    "systems",
}
WORDS = re.compile(r"[a-z][a-z-]*", re.I)


def _named_primary_content(subject: str) -> bool:
    """Require an object head or an explicit named object of a generic path.

    A modifier such as 'complex' cannot rescue 'the complex process'. A path
    such as 'the sequence from light absorption to sugar production' contains
    explicit content. We do not infer that content from a missing earlier turn.
    """
    if PRIMARY_DISCOURSE_POINTER.search(subject):
        return False
    boundary = PRIMARY_PREPOSITION.search(subject)
    head_text = subject[: boundary.start()] if boundary else subject
    head_words = WORDS.findall(head_text.casefold())
    if not head_words:
        return False
    if head_words[-1] not in GENERIC_HEADS:
        return True
    if boundary is None or boundary.group().casefold() not in {"from", "of", "about"}:
        return False
    named_path = subject[boundary.end() :]
    # A path still needs an explicit non-generic object head. This deliberately
    # leaves vague requests for an earlier process on the clarification path.
    parts = re.split(r"\b(?:to|through|across|into)\b", named_path, flags=re.I)
    for part in parts:
        words = WORDS.findall(part.strip().casefold())
        if not words or words[-1] in GENERIC_HEADS:
            return False
    return True


def _explicit_content_clause(message: str) -> bool:
    if SOURCE_POINTER.search(message):
        return False
    source = previous.SOURCE.search(message)
    if source is None:
        return False
    boundary = SECONDARY_REQUEST.search(message[: source.start()])
    if boundary is None:
        return False
    primary = PRIMARY_REQUEST.fullmatch(message[: boundary.start()].strip())
    return bool(primary and _named_primary_content(primary.group(1)))


def prepare_query(
    message: str,
    history: list[dict[str, Any]] | None = None,
    summary: str | None = None,
    *,
    version: str = VERSION,
) -> PreparedQuery:
    if version != VERSION:
        raise ValueError("Unsupported frozen query preparation version")
    prepared = previous.prepare_query(message, history, summary, version=BASE_VERSION).model_dump()
    if prepared.get("fallback_reason") == "current_named_content_source_v14":
        if _explicit_content_clause(prepared["original_message"]):
            prepared["fallback_reason"] = "current_explicit_content_clause_v15"
        else:
            prepared = historical.prepare_query(
                message, history, summary, version=previous.BASE_VERSION
            ).model_dump()
    prepared["preparation_version"] = VERSION
    return PreparedQuery(**prepared)


def describe_requirements(
    original: str,
    prepared: dict[str, Any],
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Keep the original request and frozen V15→V14→V13 syntax dependency."""
    if prepared.get("preparation_version") != VERSION:
        raise ValueError("Unsupported frozen query preparation dependency")
    result = previous.describe_requirements(
        original, {**prepared, "preparation_version": BASE_VERSION}, history
    )
    return {
        **result,
        "preparation_dependency": {
            **result["preparation_dependency"],
            "version": "query_v15_requirement_dependency_v1",
            "frozen_preparation_version": VERSION,
            "anchor_preparation_version": BASE_VERSION,
        },
    }
