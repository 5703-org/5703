"""Separate bounded leading example preferences from literal science requests.

This syntactic transformation establishes no evidence support or teaching quality.
V7 and every saved predecessor remain unchanged.
"""

from __future__ import annotations

from copy import deepcopy
import re

from .understanding import term_pattern

VERSION = "question_requirements_v8"
BASE_VERSION = "question_requirements_v7"
POLICY_VERSION = "leading_example_preference_presentation_v1"

# Exact names only. This catalogue bounds declaration recognition; no broad
# discipline inference, synonym expansion or scientific support is performed.
TOPIC_PHRASES = frozenset(
    {
        "photosynthesis",
        "diffusion",
        "osmosis",
        "cellular respiration",
        "calvin cycle",
        "mitosis",
        "meiosis",
        "dna",
        "rna",
        "atp",
        "pcr",
        "ideal gas law",
        "activation energy",
    }
)
_DECLARATION = re.compile(
    r"I\s+prefer\s+examples\s+for\s+(?P<topic>[A-Za-z]+(?:\s+[A-Za-z]+)*)", re.I
)
_SCIENCE_ACTION = re.compile(
    r"^(?:please\s+)?(?:explain|describe|what|why|how|compare|calculate|"
    r"determine|identify|which|when|where)\b",
    re.I,
)
_DELIMITER = re.compile(r"\.\s+")
_IDENTITY = re.compile(r"requirement_0[1-8]")


def _literal(point, source):
    if not isinstance(point, dict):
        return None
    span = point.get("request_span") or {}
    if not isinstance(span, dict):
        return None
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
    ):
        return None
    return start, end, literal


def separate_leading_example_preference(baseline):
    """Move only one attributable, topic-bound period-ended preference clause.

    Unknown, negative, conditional, mixed and unowned declarations remain strict.
    V5 copies global constraints onto every point; retained science constraints
    therefore remain exact regardless of conditions on the original declaration.
    """
    if baseline.get("version") != BASE_VERSION:
        raise ValueError("Unsupported frozen requirement producer")
    result = deepcopy(baseline)
    result["version"] = VERSION
    source = result.get("requirement_source_text")
    points = result.get("required_knowledge", [])
    if not (
        isinstance(source, str)
        and isinstance(points, list)
        and all(isinstance(point, dict) for point in points)
        and len(points) >= 2
        and result.get("needs_clarification") is False
        and (result.get("reader_reference_resolution") or {}).get("status") != "source_bound"
        and isinstance(result.get("presentation_requests"), list)
        and result.get("requested_facets") == points
    ):
        return result
    identities = [point.get("id") for point in points]
    if (
        any(not isinstance(value, str) or not _IDENTITY.fullmatch(value) for value in identities)
        or len(set(identities)) != len(identities)
        or any(not isinstance(point.get("intent"), str) for point in points)
    ):
        return result
    verified = [_literal(point, source) for point in points]
    if any(value is None for value in verified):
        return result
    if any(left[1] > right[0] for left, right in zip(verified, verified[1:])):
        return result
    start, end, literal = verified[0]
    if source[:start].strip():
        return result
    match = _DECLARATION.fullmatch(literal)
    if match is None:
        return result
    topic = " ".join(match.group("topic").casefold().split())
    if topic not in TOPIC_PHRASES:
        return result
    next_start, _, next_literal = verified[1]
    if not (
        _DELIMITER.fullmatch(source[end:next_start])
        and _SCIENCE_ACTION.match(next_literal)
        and term_pattern(topic).search(next_literal)
    ):
        return result
    owner_ids = [
        point["id"]
        for point, (_, _, owner_literal) in zip(points[1:], verified[1:])
        if _SCIENCE_ACTION.match(owner_literal) and term_pattern(topic).search(owner_literal)
    ]
    removed_id = points[0]["id"]
    presentation_owners = []
    for row in result["presentation_requests"]:
        if not isinstance(row, dict) or not isinstance(row.get("applies_to_requirement_ids"), list):
            return result
        retained_owners = [
            identity for identity in row["applies_to_requirement_ids"] if identity != removed_id
        ]
        if not retained_owners:
            return result
        presentation_owners.append(retained_owners)
    existing = {row.get("id") for row in result["presentation_requests"]}
    number = len(existing) + 1
    while f"presentation_{number:02d}" in existing:
        number += 1
    presentation_id = f"presentation_{number:02d}"
    presentation = {
        "id": presentation_id,
        "request": literal,
        "kind": "response_style",
        "style": "examples",
        "topic": topic,
        "applies_to_requirement_ids": owner_ids,
        "original_requirement_id": removed_id,
        "request_span": deepcopy(points[0]["request_span"]),
    }
    retained = points[1:]
    for point in retained:
        if point["id"] in owner_ids:
            point["presentation_request_ids"] = list(
                dict.fromkeys(point.get("presentation_request_ids", []) + [presentation_id])
            )
    result["required_knowledge"] = retained
    result["requested_facets"] = retained
    result["semantic_intents"] = [point["intent"] for point in retained]
    for row, retained_owners in zip(result["presentation_requests"], presentation_owners):
        row["applies_to_requirement_ids"] = retained_owners
    result["presentation_requests"].append(presentation)
    result["preference_separation"] = {
        "version": POLICY_VERSION,
        "method": "verified_literal_declaration_and_explicit_topic_owner",
        "original_requirement_id": removed_id,
        "presentation_request_id": presentation_id,
        "semantic_applicability": None,
        "semantic_sufficiency": None,
        "human_rating": None,
    }
    return result
