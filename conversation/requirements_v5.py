"""Keep bounded presentation requests outside scientific knowledge requirements.

Syntax extraction is not semantic sufficiency. The complete original question,
scientific conditions and unsupported grammar remain available to the checker.
Frozen V3/V4 requirement producers are unchanged.
"""

from __future__ import annotations

import re

from .requirements import INTENTS, NUMBER
from .requirements_v4 import describe_requirements as previous
from .understanding import comparison_targets, requirement_terms

VERSION = "question_requirements_v5"
_ACTION = r"(?:why|how|what|explain|describe|give|compare|calculate|determine|identify)\b"
_WHICH = (
    r"which\s+(?:[\w'-]+\s+){1,12}"
    r"(?:is|are|was|were|does|do|did|has|have|can|could|must|should|will|would|"
    r"change|changes|affect|affects|determine|determines)\b"
)
_WHEN_WHERE = r"(?:when|where)\s+(?:is|are|was|were|does|do|did|can|could|should|will|would)\b"
_NEXT = rf"(?:{_ACTION}|{_WHICH}|{_WHEN_WHERE})"
_BOUNDARY = re.compile(
    rf"[?;]\s*|[.!]\s+(?=(?:also\s+|then\s+)?{_NEXT}|"
    r"(?:please\s+)?(?:present|list|state|use|answer|keep)\b)|"
    rf"\s+and\s+(?={_NEXT})",
    re.I,
)
_COMPARISON_PRESENTATION = re.compile(
    r"^(?:please\s+)?(?:explain|describe|present|list|state)\s+each\s+"
    r"(?:difference|similarity)\s+separately(?:\s+please)?$",
    re.I,
)
_STYLE_PREFIX = re.compile(
    r"^(?:in\s+(?:plain|simple)\s+language|briefly|in\s+bullet\s+points)\s*[,;:]\s*",
    re.I,
)
_AXIS_COMPARISON = re.compile(
    r"^(?:please\s+)?compare\s+(.+?)\s+(?:and|with|versus)\s+(.+?)\s+"
    r"(?:in\s+(?:their|the)|in\s+terms\s+of|with\s+respect\s+to)\s+(.+)$",
    re.I,
)
_UNITS = (
    r"(?:kPa|MPa|Pa|mL|mmol|kmol|mol|kg|mg|cm|mm|km|ms|atm|torr|bar|"
    r"Hz|kJ|J|N|W|V|A|K|L|m|g|s|%|\u00b0[CFK])"
)
_EXPONENT = r"(?:\^?\s*[\u2212\u2013-]\s*\d+|\^[+]?[0-9]+|[\u2070\u00b9\u00b2\u00b3\u2074-\u2079\u207b\u207a]+)?"
_UNIT_ATOM = rf"{_UNITS}{_EXPONENT}(?![\w])"
_QUANTITY = re.compile(
    rf"(?<![\w])[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?"
    rf"(?:\s*{_UNIT_ATOM}(?:(?:\s*[\u00b7*/]\s*|\s+){_UNIT_ATOM})*)?"
)


def _clauses(query):
    cursor, rows = 0, []
    for boundary in list(_BOUNDARY.finditer(query)) + [None]:
        end = boundary.start() if boundary else len(query)
        raw = query[cursor:end]
        text = raw.strip(" ?.!;\t\r\n")
        if text:
            start = cursor + raw.index(text)
            rows.append((text, start, start + len(text)))
        cursor = boundary.end() if boundary else len(query)
    return rows


def _quantities(original):
    # Unknown units keep the older exact span. Only a bounded physical grammar
    # combines unit factors and exponents; these are not dimensional proofs.
    matches = list(_QUANTITY.finditer(original))
    for old in NUMBER.finditer(original):
        for index, current in enumerate(matches):
            if current.start() == old.start() and old.end() > current.end():
                matches[index] = old
                break
    result = []
    for match in sorted(matches, key=lambda value: (value.start(), -value.end())):
        if result and match.start() < result[-1]["end"]:
            continue
        result.append({"text": match.group(), "start": match.start(), "end": match.end()})
    return result


def _comparison(clause):
    match = _AXIS_COMPARISON.fullmatch(clause)
    if not match:
        return comparison_targets(clause), []
    left, right, axes = match.groups()
    return [left.strip(), right.strip()], [
        value.strip() for value in re.split(r",\s*|\s+and\s+", axes) if value.strip()
    ]


def _span(start, end):
    return {"coordinate_space": "requirement_source_text", "start": start, "end": end}


def describe_requirements(original, prepared, history=None, *, baseline=None):
    if baseline is None:
        baseline = previous(
            original, {**prepared, "preparation_version": "conversation_preparer_v13"}, history
        )
    result = {**baseline, "version": VERSION}
    if baseline.get("reader_reference_resolution", {}).get("status") == "source_bound":
        return {
            **result,
            "requirement_source_text": baseline.get("standalone_query") or original,
            "presentation_requests": [],
        }
    query = baseline.get("standalone_query") or original
    constraints = {
        **baseline["preserved_constraints"],
        "quantities_and_units": _quantities(original),
    }
    points, presentations = [], []
    for clause, start, end in _clauses(query):
        if (
            _COMPARISON_PRESENTATION.fullmatch(clause)
            and points
            and points[-1]["intent"] == "comparison"
            and len(points[-1]["objects"]) == 2
        ):
            presentations.append(
                {
                    "id": f"presentation_{len(presentations) + 1:02d}",
                    "request": clause,
                    "kind": "separate_comparison_items",
                    "applies_to_requirement_ids": [points[-1]["id"]],
                    "request_span": _span(start, end),
                }
            )
            continue
        prefix = _STYLE_PREFIX.match(clause)
        factual_clause = clause[prefix.end() :] if prefix else clause
        if not requirement_terms(factual_clause):
            factual_clause, prefix = clause, None
        intent = next(
            (name for name, pattern in INTENTS if re.search(pattern, factual_clause, re.I)),
            "explanation",
        )
        objects, axes = _comparison(factual_clause) if intent == "comparison" else ([], [])
        point = {
            "id": f"requirement_{len(points) + 1:02d}",
            "request": factual_clause,
            "verbatim_request": clause,
            "terms": requirement_terms(factual_clause),
            "intent": intent,
            "objects": objects,
            "relation": "compare_both_objects_on_requested_axes"
            if intent == "comparison"
            else intent,
            "conditions": [value["text"] for rows in constraints.values() for value in rows],
            "origin": "verbatim_question_structure_v5",
            "request_span": _span(start, end),
        }
        if axes:
            point["requested_axes"] = axes
        points.append(point)
        if prefix:
            presentations.append(
                {
                    "id": f"presentation_{len(presentations) + 1:02d}",
                    "request": prefix.group().strip(" ,;:"),
                    "kind": "response_style",
                    "applies_to_requirement_ids": [point["id"]],
                    "request_span": _span(start, start + len(prefix.group().strip(" ,;:"))),
                }
            )
    if len(points) > 8:
        overflow = points[7:]
        points = points[:7] + [
            {
                **overflow[0],
                "request": "; ".join(point["request"] for point in overflow),
                "verbatim_request": query[
                    overflow[0]["request_span"]["start"] : overflow[-1]["request_span"]["end"]
                ],
                "terms": list(dict.fromkeys(term for point in overflow for term in point["terms"])),
                "intent": "multiple_requests",
                "objects": [],
                "relation": "retain_all_overflow_requests",
                "request_span": _span(
                    overflow[0]["request_span"]["start"], overflow[-1]["request_span"]["end"]
                ),
                "retained_subrequests": overflow,
            }
        ]
        for presentation in presentations:
            presentation["applies_to_requirement_ids"] = list(
                dict.fromkeys(
                    identity if int(identity.rsplit("_", 1)[1]) < 8 else "requirement_08"
                    for identity in presentation["applies_to_requirement_ids"]
                )
            )
    for point in points:
        point["presentation_request_ids"] = [
            value["id"]
            for value in presentations
            if point["id"] in value["applies_to_requirement_ids"]
        ]
    return {
        **result,
        # Consumers may enrich standalone_query for retrieval. These coordinates
        # remain bound to the immutable text actually parsed for requirements.
        "requirement_source_text": query,
        "required_knowledge": points,
        "requested_facets": points,
        "semantic_intents": [point["intent"] for point in points],
        "presentation_requests": presentations,
        "preserved_constraints": constraints,
        "requirement_structure": {
            "version": "bounded_request_and_presentation_v1",
            "coordinate_space": "requirement_source_text",
            "semantic_equivalence": None,
            "semantic_sufficiency": None,
            "human_rating": None,
        },
    }
