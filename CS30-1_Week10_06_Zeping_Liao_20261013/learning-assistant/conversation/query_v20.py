"""Frozen V19 query behavior with V6 help-depth requirement separation."""

from __future__ import annotations

from contracts.models import PreparedQuery
from . import query_v19 as previous
from .requirements_v6 import VERSION as REQUIREMENT_VERSION, separate_help_depth

VERSION = "conversation_preparer_v20"
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
    result = separate_help_depth(
        previous.describe_requirements(
            original, {**prepared, "preparation_version": BASE_VERSION}, history
        )
    )
    return {
        **result,
        "preparation_dependency": {
            **result["preparation_dependency"],
            "version": "query_v20_requirement_dependency_v1",
            "frozen_preparation_version": VERSION,
            "requirements_version": REQUIREMENT_VERSION,
            "current_reference_base_version": BASE_VERSION,
        },
    }
