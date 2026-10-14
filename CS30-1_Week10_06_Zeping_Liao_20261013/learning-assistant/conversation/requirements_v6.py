"""Separate a complete help-depth clause from scientific knowledge points.

The frozen V5 producer supplies every point and immutable coordinate. This
wrapper changes no scientific request, source, support judgment or help gate.
"""

from __future__ import annotations

from copy import deepcopy
import re

VERSION = "question_requirements_v6"
BASE_VERSION = "question_requirements_v5"
POLICY_VERSION = "standalone_hint_presentation_v1"
_HELP_DEPTH = re.compile(
    r"(?:please\s+)?give\s+me\s+(?:one|a)\s+hint(?:\s+for\s+this\s+step)?",
    re.I,
)


def separate_help_depth(baseline):
    """Move only an exact standalone clause when factual points remain."""
    if baseline.get("version") != BASE_VERSION:
        raise ValueError("Unsupported frozen requirement producer")
    result = deepcopy(baseline)
    points = result["required_knowledge"]
    source = result.get("requirement_source_text")
    moved = []
    for point in points:
        span = point.get("request_span") or {}
        start, end = span.get("start"), span.get("end")
        if (
            isinstance(source, str)
            and point.get("origin") == "verbatim_question_structure_v5"
            and span.get("coordinate_space") == "requirement_source_text"
            and type(start) is int
            and type(end) is int
            and 0 <= start < end <= len(source)
            and (not source[:start].rstrip() or source[:start].rstrip()[-1] in ".?!;")
            and (not source[end:].lstrip() or source[end:].lstrip()[0] in ".?!;")
            and source[start:end] == point.get("verbatim_request") == point.get("request")
            and _HELP_DEPTH.fullmatch(point["request"])
        ):
            moved.append(point)
    factual = [point for point in points if point not in moved]
    if moved and factual:
        presentations = result["presentation_requests"]
        existing = {row["id"] for row in presentations}
        factual_ids = [point["id"] for point in factual]
        for point in moved:
            number = len(presentations) + 1
            while f"presentation_{number:02d}" in existing:
                number += 1
            identity = f"presentation_{number:02d}"
            existing.add(identity)
            presentations.append(
                {
                    "id": identity,
                    "request": point["verbatim_request"],
                    "kind": "help_depth",
                    "applies_to_requirement_ids": factual_ids[:],
                    "request_span": deepcopy(point["request_span"]),
                    "original_requirement_id": point["id"],
                    "policy_version": POLICY_VERSION,
                }
            )
        result["required_knowledge"] = factual
        result["requested_facets"] = deepcopy(factual)
        result["semantic_intents"] = [point["intent"] for point in factual]
        result["help_depth_separation"] = {
            "version": POLICY_VERSION,
            "moved_requirement_ids": [point["id"] for point in moved],
            "retained_requirement_ids": factual_ids,
            "coordinate_space": "requirement_source_text",
        }
    result["version"] = VERSION
    result["requirement_structure"] = {
        **result["requirement_structure"],
        "version": "bounded_request_and_presentation_v2",
        "help_depth_policy": POLICY_VERSION,
    }
    return result
