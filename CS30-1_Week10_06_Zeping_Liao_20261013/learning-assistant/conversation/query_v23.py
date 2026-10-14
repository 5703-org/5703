"""Opt-in eligibility from a current statement or explicit assignments.

This bounded syntax rule admits retrieval of the complete original question.
It neither substitutes a noun for a pronoun nor establishes semantic support.
Frozen V22 continues to own every unmatched preparation and requirement rule.
"""

from __future__ import annotations

import hashlib
import re

from contracts.models import PreparedQuery

from conversation import query_v22 as previous
from conversation.query import DEPENDENT, REEXPLAIN
from conversation.query_v14 import ANCHOR_GRAMMAR, REQUEST_START, SOURCE_PRESENTATION
from conversation.requirements_v5 import _clauses
from conversation.understanding import COMPARISON

VERSION = "conversation_preparer_v23"
BASE_VERSION = previous.VERSION
RESOLUTION_VERSION = "current_named_modal_event_reference_v1"
ASSIGNMENT_RESOLUTION_VERSION = "current_explicit_assignment_set_reference_v1"
CURRENT_MESSAGE_ELIGIBILITY_VERSION = "fresh_current_context_retrieval_eligibility_v1"
_SETUP_START = re.compile(
    r"^(?:model|consider|assume|suppose|let|given|for|in|a|an|the|one)\b", re.I
)
_ASSIGNMENT_MESSAGE = re.compile(
    r"^(?P<statement>[^?!\r\n]{1,700})\.\s+"
    r"Are\s+(?P<referent>these|those)\s+(?:assignments|values)\s+correct\?"
    r"(?P<tail>(?:\s+(?:Give|Identify|Explain|Describe|What|Why|How|Which|State|"
    r"Calculate|Determine)\b[^?!\r\n]*[?!]?){0,2})$",
    re.I,
)
_ASSIGNMENT = re.compile(
    r"\b(?P<name>[a-z][a-z0-9_]*)\s*=\s*"
    r"(?P<value>[+-]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?)"
    r"(?=$|[\s,.;])",
    re.I,
)
_MESSAGE = re.compile(
    r"^(?P<statement>[^.!?\r\n]{10,500})\.\s+"
    r"(?P<request>Does\s+this\s+(?:require|need|use|consume|involve|change|"
    r"affect|cause|produce)\b[^?\r\n]{1,1000}\?)"
    r"(?P<tail>(?:\s+(?:Explain|Describe|What|Why|How|Which)\b"
    r"[^.!?\r\n]+[.!?]){0,2})$",
    re.I,
)
_STATEMENT = re.compile(
    r"^(?P<subject>[a-z][a-z-]*(?:\s+[a-z][a-z-]*){0,6}?)\s+"
    r"(?P<modal>can|cannot|could|will|would|may|might|must|should)\s+"
    r"(?:not\s+)?(?P<verb>[a-z][a-z-]*)(?:\s+[^.!?\r\n]+)?$",
    re.I,
)
_COMPETING = re.compile(r"[,;:]|\b(?:and|or|versus|vs|while|whereas|but|then)\b", re.I)
_POINTER = re.compile(
    r"\b(?:previous|prior|earlier|above|below|mentioned|cited|preceding|"
    r"following|another|former|latter|selected|attached|he|she|his|her|him)\b",
    re.I,
)
_MODAL = re.compile(r"\b(?:can|cannot|could|will|would|may|might|must|should)\b", re.I)
_GENERIC = ANCHOR_GRAMMAR | set(
    "observation observations event events situation situations mechanism mechanisms "
    "method methods phenomenon phenomena system systems example examples result results ".split()
)
_NON_VERB = set("a an the one to of for with from at by in on and or not".split())


def _current_message_eligibility(message, history=None, summary=None):
    """Admit one fresh current setup; never resolve or substitute its pronouns."""
    if history or summary and summary.strip():
        return None
    refs = list(DEPENDENT.finditer(message))
    if not refs or not _SETUP_START.match(message):
        return None
    if _POINTER.search(message) or REEXPLAIN.search(message) or SOURCE_PRESENTATION.search(message):
        return None
    prefix = message[: refs[0].start()]
    if COMPARISON.search(prefix) or re.search(r"\b(?:and|or|another)\b", prefix, re.I):
        return None
    setup_clauses = re.split(r"[.!?](?:\s+|$)", prefix)
    completed = [clause.strip() for clause in setup_clauses[:-1] if clause.strip()]
    remaining = setup_clauses[-1].strip()
    if len(completed) > 1 or completed and remaining and not REQUEST_START.match(remaining):
        return None
    words = set(re.findall(r"[a-z][a-z-]*", prefix.casefold()))
    setup_words = set(
        "model consider assume suppose let given setup context statement statements "
        "problem problems object objects item items".split()
    )
    if not words - _GENERIC - setup_words:
        return None
    if not any(REQUEST_START.match(clause) for clause, _, _ in _clauses(message)):
        return None
    return {
        "version": CURRENT_MESSAGE_ELIGIBILITY_VERSION,
        "source_text": message,
        "source_sha256": hashlib.sha256(message.encode()).hexdigest(),
        "coordinate_space": "current_original_message",
        "context_prefix_span": {"start": 0, "end": refs[0].start(), "text": prefix},
        "dependent_spans": [
            {"start": ref.start(), "end": ref.end(), "text": ref.group()} for ref in refs
        ],
        "coreference_resolution": None,
        "semantic_equivalence": None,
        "semantic_sufficiency": None,
        "human_rating": None,
    }


def _assignment_resolution(message):
    match = _ASSIGNMENT_MESSAGE.fullmatch(message)
    if match is None or _POINTER.search(message):
        return None
    statement = match["statement"]
    if re.search(r"[.!?](?:\s+|$)", statement):
        return None
    assignments = list(_ASSIGNMENT.finditer(statement))
    if not 2 <= len(assignments) <= 6 or len(
        {row["name"].casefold() for row in assignments}
    ) != len(assignments):
        return None
    refs = list(DEPENDENT.finditer(message))
    if len(refs) != 1 or refs[0].span() != match.span("referent"):
        return None
    return {
        "version": ASSIGNMENT_RESOLUTION_VERSION,
        "source_text": message,
        "source_sha256": hashlib.sha256(message.encode()).hexdigest(),
        "coordinate_space": "current_original_message",
        "antecedent_span": {"start": 0, "end": match.end("statement") + 1, "text": statement + "."},
        "referent_spans": [
            {
                "kind": "current_explicit_assignment_set",
                "start": refs[0].start(),
                "end": refs[0].end(),
            }
        ],
        "assignment_spans": [
            {
                "name_start": row.start("name"),
                "name_end": row.end("name"),
                "value_start": row.start("value"),
                "value_end": row.end("value"),
            }
            for row in assignments
        ],
        "semantic_equivalence": None,
        "semantic_sufficiency": None,
        "human_rating": None,
    }


def _current_resolution(message):
    assignment = _assignment_resolution(message)
    if assignment is not None:
        return assignment
    match = _MESSAGE.fullmatch(message)
    if match is None or _POINTER.search(message):
        return None
    statement = match["statement"]
    subject = _STATEMENT.fullmatch(statement)
    if subject is None or _COMPETING.search(statement):
        return None
    words = re.findall(r"[a-z][a-z-]*", subject["subject"].casefold())
    if not words or words[-1] in _GENERIC or subject["verb"].casefold() in _NON_VERB:
        return None
    if len(_MODAL.findall(statement)) != 1:
        return None
    refs = list(DEPENDENT.finditer(message))
    if len(refs) != 1 or refs[0].group().casefold() != "this":
        return None
    ref = refs[0]
    if not match.start("request") <= ref.start() < match.end("request"):
        return None
    return {
        "version": RESOLUTION_VERSION,
        "source_text": message,
        "source_sha256": hashlib.sha256(message.encode()).hexdigest(),
        "coordinate_space": "current_original_message",
        "antecedent_span": {
            "start": match.start("statement"),
            "end": match.end("statement") + 1,
            "text": statement + ".",
        },
        "referent_spans": [
            {"kind": "complete_current_modal_statement", "start": ref.start(), "end": ref.end()}
        ],
        "semantic_equivalence": None,
        "semantic_sufficiency": None,
        "human_rating": None,
    }


def prepare_query(message, history=None, summary=None, *, version=VERSION) -> PreparedQuery:
    if version != VERSION:
        raise ValueError("Unsupported frozen query preparation version")
    result = previous.prepare_query(message, history, summary).model_dump()
    result["preparation_version"] = VERSION
    if result["needs_clarification"] and result["fallback_reason"] not in {
        "missing_referent",
        "ambiguous_referent_after_comparison",
    }:
        return PreparedQuery(**result)
    resolution = _current_resolution(result["original_message"])
    eligibility = None
    if (
        resolution is None
        and result["needs_clarification"]
        and result["fallback_reason"] == "missing_referent"
    ):
        eligibility = _current_message_eligibility(result["original_message"], history, summary)
    if resolution is not None or eligibility is not None:
        result.update(
            standalone_query=result["original_message"],
            intent="factual",
            topic_relation="new_topic",
            referenced_message_ids=[],
            needs_clarification=False,
            fallback_reason=(resolution or eligibility)["version"],
        )
    return PreparedQuery(**result)


def describe_requirements(original, prepared, history=None):
    if prepared.get("preparation_version") != VERSION:
        raise ValueError("Unsupported frozen query preparation dependency")
    resolution = None
    eligibility = None
    if prepared.get("fallback_reason") in {RESOLUTION_VERSION, ASSIGNMENT_RESOLUTION_VERSION}:
        resolution = _current_resolution(prepared["original_message"])
        if (
            resolution is None
            or prepared["original_message"] != original.strip()
            or prepared != prepare_query(original, history).model_dump()
        ):
            raise ValueError("The frozen current reference is unavailable")
    if prepared.get("fallback_reason") == CURRENT_MESSAGE_ELIGIBILITY_VERSION:
        eligibility = _current_message_eligibility(prepared["original_message"], history)
        if (
            eligibility is None
            or prepared["original_message"] != original.strip()
            or prepared != prepare_query(original, history).model_dump()
        ):
            raise ValueError("The frozen current retrieval eligibility is unavailable")
    result = previous.describe_requirements(
        original, {**prepared, "preparation_version": BASE_VERSION}, history
    )
    if resolution is not None:
        result = {**result, "current_event_resolution": resolution}
    if eligibility is not None:
        result = {**result, "current_message_eligibility": eligibility}
    return {
        **result,
        "preparation_dependency": {
            **result["preparation_dependency"],
            "version": "query_v23_requirement_dependency_v1",
            "frozen_preparation_version": VERSION,
            "current_reference_base_version": BASE_VERSION,
        },
    }
