"""Resolve one explicitly named axis of the latest owned comparison question."""

from __future__ import annotations

import hashlib
import re

from contracts.models import PreparedQuery

from . import query_v17 as previous
from .query import DEPENDENT
from .understanding import GRAMMAR, requirement_terms

VERSION = "conversation_preparer_v18"
BASE_VERSION = previous.VERSION
RESOLUTION_VERSION = "owned_explicit_comparison_axis_v1"
_REQUEST = re.compile(
    r"^(?:please\s+)?(?:explain|describe|rephrase|clarify|simplify)\s+"
    r"(?:the\s+)?(?P<axis>[a-z][a-z -]{0,80}?)\s+"
    r"(?:differences|difference|comparison)(?P<tail>.*?)[.!?]*$",
    re.I,
)
_TAIL = re.compile(
    r"(?:(?:in\s+(?:simpler|simple|plain)\s+(?:language|terms)|more\s+simply|"
    r"with\s+simpler\s+words|briefly|separately)"
    r"(?:\s*,?\s+(?:if|when|unless|at|under|without|assuming|provided\s+that)\s+.+)?"
    r"|(?:if|when|unless|at|under|without|assuming|provided\s+that)\s+.+)",
    re.I,
)
_COORDINATOR = re.compile(r"\b(?:and|or|versus|vs|former|latter)\b", re.I)
_NEW_ACTION = re.compile(
    r"\b(?:and|also|then)\s+(?:explain|describe|compare|calculate|determine|identify|"
    r"give|provide|show|derive|discuss|summari[sz]e|what|why|how)\b",
    re.I,
)
_SECOND_SENTENCE = re.compile(r"[.!?]\s*[a-z]|[\r\n]", re.I)
_AXIS_CONDITION = re.compile(
    r"\b(?:if|when|unless|at|under|without|assuming|provided|only)\b", re.I
)
_UNAVAILABLE = {
    "failed",
    "error",
    "cancelled",
    "queued",
    "pending",
    "processing",
    "running",
    "partial",
}
_PLACEHOLDER_WORDS = {
    "the",
    "a",
    "an",
    "first",
    "second",
    "one",
    "other",
    "either",
    "both",
    "this",
    "that",
    "these",
    "those",
}


def _fold_word(word):
    word = word.casefold()
    # A bounded regular plural match leaves gas, mass, basis and focus intact.
    if len(word) > 3 and word.endswith("s") and not word.endswith(("ss", "us", "is", "as")):
        return word[:-1]
    return word


def _axis_words(axis):
    axis = _AXIS_CONDITION.split(axis, maxsplit=1)[0]
    return [_fold_word(word) for word in re.findall(r"[a-z][a-z-]*", axis, re.I)]


def _resolution(original, history):
    match = _REQUEST.fullmatch(original.strip())
    if match is None or DEPENDENT.search(original):
        return None
    requested = match["axis"].strip()
    tail = match["tail"].strip()
    if (
        _COORDINATOR.search(requested)
        or tail
        and (not _TAIL.fullmatch(tail) or _NEW_ACTION.search(tail) or _SECOND_SENTENCE.search(tail))
    ):
        return None
    if len(history or []) < 2:
        return None
    user, assistant = history[-2:]
    if (
        user.get("role") != "user"
        or assistant.get("role") != "assistant"
        or assistant.get("latest_exchange_available") is not True
        or not assistant.get("answer_id")
        or assistant.get("answer_response_type") not in {"answer", "refusal"}
        or user.get("state") in _UNAVAILABLE
        or assistant.get("state") in _UNAVAILABLE
        or not user.get("message_id")
        or not assistant.get("message_id")
        or not isinstance(user.get("content"), str)
        or not user["content"].strip()
    ):
        return None
    prior = user["content"]
    prior_prepared = previous.prepare_query(prior).model_dump()
    if prior_prepared["needs_clarification"]:
        return None
    # Axis coordinates belong to the literal prior question, before expansions.
    prior_requirements = previous.describe_requirements(
        prior, {**prior_prepared, "standalone_query": prior}, []
    )
    points = prior_requirements["required_knowledge"]
    if len(points) != 1 or points[0]["intent"] != "comparison":
        return None
    point = points[0]
    objects = point.get("objects", [])
    if (
        len(objects) != 2
        or objects[0].casefold() == objects[1].casefold()
        or any(DEPENDENT.search(value) or _COORDINATOR.search(value) for value in objects)
        or any(
            not set(re.findall(r"[a-z][a-z-]*", value.casefold())) - GRAMMAR for value in objects
        )
        or any(
            set(re.findall(r"[a-z][a-z-]*", value.casefold())) <= _PLACEHOLDER_WORDS
            for value in objects
        )
    ):
        return None
    words = _axis_words(requested)
    if not words:
        return None
    matches = [
        axis
        for axis in point.get("requested_axes", [])
        if _axis_words(axis) == words
        or len(words) == 1
        and _axis_words(axis)
        and _axis_words(axis)[-1] == words[0]
    ]
    if len(matches) != 1:
        return None
    axis = matches[0]
    # Duplicate literal occurrences have no unique location to register.
    locations = list(re.finditer(re.escape(axis), prior, re.I))
    if len(locations) != 1:
        return None
    axis_location = locations[0]
    leading_space = len(original) - len(original.lstrip())
    inherited = {
        category: [{**span, "coordinate_space": "prior_source_text"} for span in spans]
        for category, spans in prior_requirements["preserved_constraints"].items()
    }
    return {
        "version": RESOLUTION_VERSION,
        "user_message_id": user["message_id"],
        "assistant_message_id": assistant["message_id"],
        "prior_source_text": prior,
        "prior_source_sha256": hashlib.sha256(prior.encode()).hexdigest(),
        "objects": objects,
        "requested_axis": axis,
        "current_axis_span": {
            "coordinate_space": "original_message",
            "start": leading_space + match.start("axis"),
            "end": leading_space + match.end("axis"),
            "text": match["axis"],
        },
        "prior_axis_span": {
            "coordinate_space": "prior_source_text",
            "start": axis_location.start(),
            "end": axis_location.end(),
            "text": axis_location.group(),
        },
        "inherited_constraints": inherited,
        "semantic_equivalence": None,
        "semantic_sufficiency": None,
        "human_rating": None,
    }


def _query_from_resolution(original, resolution):
    return (
        original
        + "\nComparison objects: "
        + " and ".join(resolution["objects"])
        + "\nRequested comparison axis: "
        + resolution["requested_axis"]
        + "\nPrior learner context (verbatim): "
        + resolution["prior_source_text"]
        + "\nCurrent requested axis: "
        + resolution["requested_axis"]
    )


def prepare_query(message, history=None, summary=None, *, version=VERSION) -> PreparedQuery:
    if version != VERSION:
        raise ValueError("Unsupported frozen query preparation version")
    result = previous.prepare_query(message, history, summary).model_dump()
    result["preparation_version"] = VERSION
    unresolved = not result["referenced_message_ids"] and not result["needs_clarification"]
    ambiguous_axis = (
        result["needs_clarification"]
        and result["fallback_reason"] == "ambiguous_referent_after_comparison"
    )
    if not (unresolved or ambiguous_axis):
        return PreparedQuery(**result)
    resolution = _resolution(result["original_message"], history or [])
    if resolution is None:
        return PreparedQuery(**result)
    result.update(
        standalone_query=_query_from_resolution(result["original_message"], resolution),
        intent="comparison",
        topic_relation="same_topic",
        referenced_message_ids=[resolution["user_message_id"]],
        needs_clarification=False,
        fallback_reason=RESOLUTION_VERSION,
    )
    return PreparedQuery(**result)


def describe_requirements(original, prepared, history=None):
    if prepared.get("preparation_version") != VERSION:
        raise ValueError("Unsupported frozen query preparation dependency")
    syntax_input = {**prepared, "preparation_version": BASE_VERSION}
    if prepared.get("fallback_reason") == RESOLUTION_VERSION:
        resolution = _resolution(original, history or [])
        if (
            resolution is None
            or prepared["original_message"] != original.strip()
            or prepared["referenced_message_ids"] != [resolution["user_message_id"]]
            or prepared["standalone_query"] != _query_from_resolution(original.strip(), resolution)
        ):
            raise ValueError("The frozen comparison-axis reference is unavailable")
        # Retrieval enrichment is not a second set of scientific obligations.
        result = previous.describe_requirements(
            original, {**syntax_input, "standalone_query": original}, history
        )
        resolution["current_axis_span"]["coordinate_space"] = "requirement_source_text"
        points = []
        inherited_conditions = [
            span["text"] for spans in resolution["inherited_constraints"].values() for span in spans
        ]
        for point in result["required_knowledge"]:
            points.append(
                {
                    **point,
                    "objects": resolution["objects"],
                    "requested_axes": [resolution["requested_axis"]],
                    "relation": "compare_both_objects_on_requested_axes",
                    "terms": list(
                        dict.fromkeys(
                            [
                                *requirement_terms(" ".join(resolution["objects"])),
                                *requirement_terms(resolution["requested_axis"]),
                            ]
                        )
                    ),
                    "conditions": list(
                        dict.fromkeys([*point["conditions"], *inherited_conditions])
                    ),
                    "origin": RESOLUTION_VERSION,
                }
            )
        result = {
            **result,
            "standalone_query": prepared["standalone_query"],
            "required_knowledge": points,
            "requested_facets": points,
            "comparison_targets": resolution["objects"],
            "comparison_axis_resolution": resolution,
        }
    else:
        result = previous.describe_requirements(original, syntax_input, history)
    return {
        **result,
        "preparation_dependency": {
            **result["preparation_dependency"],
            "version": "query_v18_requirement_dependency_v1",
            "frozen_preparation_version": VERSION,
            "axis_preparation_version": BASE_VERSION,
        },
    }
