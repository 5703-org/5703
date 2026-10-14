"""Carve one exact final help sentence from a frozen scientific literal span.

The original source/query and scientific identity/conditions remain intact.
This syntactic distinction supplies no source support or teaching acceptance.
"""

from __future__ import annotations

from copy import deepcopy
import re

from .requirements_v5 import _comparison
from .requirements_v6 import _HELP_DEPTH
from .understanding import requirement_terms

VERSION = "question_requirements_v7"
BASE_VERSION = "question_requirements_v6"
POLICY_VERSION = "trailing_literal_help_presentation_v2"
_TRAILING = re.compile(
    r"[.!?](?P<space>\s+)(?P<help>(?:please\s+)?give\s+me\s+(?:one|a)\s+hint"
    r"(?:\s+for\s+this\s+step)?)$",
    re.I,
)
_SCIENTIFIC_PREFIX = re.compile(
    r"^(?:please\s+)?(?:why|how|what|explain|describe|give|compare|calculate|determine|identify|which|when|where)\b",
    re.I,
)
_HELP_PREFIX = re.compile(
    r"^(?:please\s+)?(?:give|show|provide|offer)(?:\s+me)?\s+(?:one|a|another|the|some|two)\s+hints?\b",
    re.I,
)


def separate_embedded_help_depth(baseline):
    """Keep ambiguous, malformed, help-only and same-sentence points strict."""
    if baseline.get("version") != BASE_VERSION:
        raise ValueError("Unsupported frozen requirement producer")
    result = deepcopy(baseline)
    source = result.get("requirement_source_text")
    points = result.get("required_knowledge", [])
    separated = None
    if isinstance(source, str) and result.get("needs_clarification") is False:
        for point in points:
            span = point.get("request_span") or {}
            start, end = span.get("start"), span.get("end")
            literal = point.get("verbatim_request")
            if not (
                point.get("origin") == "verbatim_question_structure_v5"
                and span.get("coordinate_space") == "requirement_source_text"
                and type(start) is int
                and type(end) is int
                and 0 <= start < end <= len(source)
                and isinstance(literal, str)
                and source[start:end] == literal == point.get("request")
                and (not source[:start].rstrip() or source[:start].rstrip()[-1] in ".?!;")
                and not source[end:].strip(" \t\r\n.!?")
            ):
                continue
            match = _TRAILING.search(literal)
            if match is None:
                continue
            scientific = literal[: match.start()].rstrip()
            if (
                not scientific
                or scientific[-1] in ".?!;"
                or not _SCIENTIFIC_PREFIX.match(scientific)
                or _HELP_PREFIX.match(scientific)
                or _HELP_DEPTH.fullmatch(scientific)
                or not requirement_terms(scientific)
            ):
                continue
            scientific_end = start + len(scientific)
            help_start, help_end = start + match.start("help"), start + match.end("help")
            presentations = result["presentation_requests"]
            existing = {row["id"] for row in presentations}
            number = len(presentations) + 1
            while f"presentation_{number:02d}" in existing:
                number += 1
            identity = f"presentation_{number:02d}"
            old_span = deepcopy(span)
            point.update(
                request=scientific,
                verbatim_request=scientific,
                terms=requirement_terms(scientific),
                request_span={**span, "end": scientific_end},
            )
            if point["intent"] == "comparison":
                objects, axes = _comparison(scientific)
                point["objects"] = objects
                if axes:
                    point["requested_axes"] = axes
                else:
                    point.pop("requested_axes", None)
            scientific_ids = [row["id"] for row in points]
            presentations.append(
                {
                    "id": identity,
                    "request": source[help_start:help_end],
                    "kind": "help_depth",
                    "applies_to_requirement_ids": scientific_ids,
                    "request_span": {
                        "coordinate_space": "requirement_source_text",
                        "start": help_start,
                        "end": help_end,
                    },
                    "original_requirement_id": point["id"],
                    "policy_version": POLICY_VERSION,
                }
            )
            for row in points:
                row["presentation_request_ids"] = [
                    p["id"] for p in presentations if row["id"] in p["applies_to_requirement_ids"]
                ]
            separated = {
                "version": POLICY_VERSION,
                "retained_scientific_requirement_id": point["id"],
                "original_request_span": old_span,
                "scientific_request_span": deepcopy(point["request_span"]),
                "presentation_request_id": identity,
                "presentation_request_span": deepcopy(presentations[-1]["request_span"]),
                "coordinate_space": "requirement_source_text",
            }
            break
    if separated:
        result["requested_facets"] = deepcopy(points)
        result["semantic_intents"] = [point["intent"] for point in points]
        result["embedded_help_depth_separation"] = separated
    result["version"] = VERSION
    result["requirement_structure"] = {
        **result["requirement_structure"],
        "version": "bounded_request_and_presentation_v3",
        "base_help_depth_policy": result["requirement_structure"].get("help_depth_policy"),
        "help_depth_policy": POLICY_VERSION,
    }
    return result
