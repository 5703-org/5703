"""Restate the last verified whole answer without resolving its individual objects.

The caller supplies query-only metadata bound to the frozen owned conversation
snapshot. This wrapper never reads an assistant body to infer a topic. New
knowledge requests and object-specific follow-ups retain the frozen V15 rules.
"""

from __future__ import annotations

import re
from typing import Any

from contracts.models import PreparedQuery

from . import query_v15 as previous

VERSION = "conversation_preparer_v16"
BASE_VERSION = "conversation_preparer_v15"
RESTATEMENT_VERSION = "verified_whole_answer_restatement_v1"
_OBJECT = r"(?:it|that|this|(?:the|your)\s+(?:previous\s+|whole\s+)?(?:answer|explanation))"
_STYLE = (
    r"(?:more\s+simply|in\s+(?:simpler|simple)\s+terms|in\s+plain\s+language|"
    r"(?:with|using)\s+simpler\s+words|more\s+briefly|briefly|again)"
)
PURE_RESTATEMENT = re.compile(
    r"^(?:please\s+)?(?:(?:can|could|would|will)\s+you\s+(?:please\s+)?)?(?:"
    rf"(?:explain|describe)\s+{_OBJECT}\s+{_STYLE}"
    rf"|(?:rephrase|rewrite|summari[sz]e|simplify)\s+{_OBJECT}(?:\s+{_STYLE})?"
    rf"|make\s+{_OBJECT}\s+(?:simpler|shorter)"
    r")(?:\s+please)?[.!?]*$",
    re.I,
)
_UNAVAILABLE_STATES = {
    "failed",
    "error",
    "cancelled",
    "queued",
    "pending",
    "processing",
    "running",
    "partial",
}


def _last_verified_pair(history: list[dict[str, Any]]) -> tuple[dict, dict] | None:
    if len(history) < 2:
        return None
    user, assistant = history[-2:]
    if user.get("role") != "user" or assistant.get("role") != "assistant":
        return None
    if user.get("state") in _UNAVAILABLE_STATES or assistant.get("state") in _UNAVAILABLE_STATES:
        return None
    if (
        not isinstance(user.get("content"), str)
        or not user["content"].strip()
        or not user.get("message_id")
        or not assistant.get("message_id")
        or not assistant.get("answer_id")
        or assistant.get("answer_response_type") != "answer"
        or assistant.get("latest_exchange_available") is not True
    ):
        return None
    return user, assistant


def prepare_query(
    message: str,
    history: list[dict[str, Any]] | None = None,
    summary: str | None = None,
    *,
    version: str = VERSION,
) -> PreparedQuery:
    if version != VERSION:
        raise ValueError("Unsupported frozen query preparation version")
    result = previous.prepare_query(message, history, summary, version=BASE_VERSION).model_dump()
    original = result["original_message"]
    result["preparation_version"] = VERSION
    if not PURE_RESTATEMENT.fullmatch(original):
        return PreparedQuery(**result)
    pair = _last_verified_pair(history or [])
    if pair is None:
        # Never search older answers or a summary past an unavailable last turn.
        # V16 introduces this conservative fence only for a whole-answer request.
        result.update(
            standalone_query=None,
            intent="clarification",
            topic_relation="unclear",
            referenced_message_ids=[],
            needs_clarification=True,
            fallback_reason="missing_verified_whole_answer",
        )
    else:
        user, _ = pair
        result.update(
            standalone_query=original + " Prior learner question: " + user["content"],
            intent="reexplain",
            topic_relation="same_topic",
            referenced_message_ids=[user["message_id"]],
            needs_clarification=False,
            fallback_reason=RESTATEMENT_VERSION,
        )
    return PreparedQuery(**result)


def describe_requirements(
    original: str,
    prepared: dict[str, Any],
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Retain V16 identity while delegating the frozen V15→V14→V13 grammar."""
    if prepared.get("preparation_version") != VERSION:
        raise ValueError("Unsupported frozen query preparation dependency")
    result = previous.describe_requirements(
        original, {**prepared, "preparation_version": BASE_VERSION}, history
    )
    return {
        **result,
        "preparation_dependency": {
            **result["preparation_dependency"],
            "version": "query_v16_requirement_dependency_v1",
            "frozen_preparation_version": VERSION,
            "restatement_preparation_version": BASE_VERSION,
        },
    }
