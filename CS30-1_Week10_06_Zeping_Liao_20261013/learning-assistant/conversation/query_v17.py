"""Retain V16 preparation with independently versioned requirements."""

from __future__ import annotations

from contracts.models import PreparedQuery

from . import query_v16 as previous
from . import requirements_v5 as requirement_producer

VERSION = "conversation_preparer_v17"
BASE_VERSION = previous.VERSION


def prepare_query(message, history=None, summary=None, *, version=VERSION) -> PreparedQuery:
    if version != VERSION:
        raise ValueError("Unsupported frozen query preparation version")
    result = previous.prepare_query(message, history, summary, version=BASE_VERSION).model_dump()
    return PreparedQuery(**{**result, "preparation_version": VERSION})


def describe_requirements(original, prepared, history=None):
    if prepared.get("preparation_version") != VERSION:
        raise ValueError("Unsupported frozen query preparation dependency")
    baseline = previous.describe_requirements(
        original, {**prepared, "preparation_version": BASE_VERSION}, history
    )
    result = requirement_producer.describe_requirements(
        original, prepared, history, baseline=baseline
    )
    return {
        **result,
        "preparation_dependency": {
            **baseline["preparation_dependency"],
            "version": "query_v17_requirement_dependency_v1",
            "frozen_preparation_version": VERSION,
            "restatement_preparation_version": BASE_VERSION,
            "requirements_version": requirement_producer.VERSION,
        },
    }
