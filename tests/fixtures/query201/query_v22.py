"""Frozen V21 preparation with bounded leading preference presentation."""

from __future__ import annotations

from contracts.models import PreparedQuery
from . import query_v21 as previous
from .requirements_v8 import (
    VERSION as REQUIREMENT_VERSION,
    separate_leading_example_preference,
)

VERSION = "conversation_preparer_v22"
BASE_VERSION = previous.VERSION


def prepare_query(message, history=None, summary=None, *, version=VERSION) -> PreparedQuery:
    if version != VERSION:
        raise ValueError("Unsupported frozen query preparation version")
    result = previous.prepare_query(message, history, summary).model_dump()
    result["preparation_version"] = VERSION
    return PreparedQuery(**result)


def describe_requirements(original, prepared, history=None):
    if prepared.get("preparation_version") != VERSION:
        raise ValueError("Unsupported frozen query preparation dependency")
    result = separate_leading_example_preference(
        previous.describe_requirements(
            original, {**prepared, "preparation_version": BASE_VERSION}, history
        )
    )
    return {
        **result,
        "preparation_dependency": {
            **result["preparation_dependency"],
            "version": "query_v22_requirement_dependency_v1",
            "frozen_preparation_version": VERSION,
            "requirements_version": REQUIREMENT_VERSION,
            "current_reference_base_version": BASE_VERSION,
        },
    }
