"""Opt-in ownership of one current modal statement and its event question.

This bounded syntax rule admits retrieval of the complete original question.
It neither substitutes a noun for a pronoun nor establishes semantic support.
Frozen V22 continues to own every unmatched preparation and requirement rule.
"""

from __future__ import annotations

import hashlib
import re

from contracts.models import PreparedQuery

from conversation import query_v22 as previous
from conversation.query import DEPENDENT
from conversation.query_v14 import ANCHOR_GRAMMAR

VERSION = "conversation_preparer_v23"
BASE_VERSION = previous.VERSION
RESOLUTION_VERSION = "current_named_modal_event_reference_v1"
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


def _current_resolution(message):
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
    if _current_resolution(result["original_message"]) is not None:
        result.update(
            standalone_query=result["original_message"],
            intent="factual",
            topic_relation="new_topic",
            referenced_message_ids=[],
            needs_clarification=False,
            fallback_reason=RESOLUTION_VERSION,
        )
    return PreparedQuery(**result)


def describe_requirements(original, prepared, history=None):
    if prepared.get("preparation_version") != VERSION:
        raise ValueError("Unsupported frozen query preparation dependency")
    resolution = None
    if prepared.get("fallback_reason") == RESOLUTION_VERSION:
        resolution = _current_resolution(prepared["original_message"])
        if (
            resolution is None
            or prepared["original_message"] != original.strip()
            or prepared != prepare_query(original, history).model_dump()
        ):
            raise ValueError("The frozen current modal event reference is unavailable")
    result = previous.describe_requirements(
        original, {**prepared, "preparation_version": BASE_VERSION}, history
    )
    if resolution is not None:
        result = {**result, "current_event_resolution": resolution}
    return {
        **result,
        "preparation_dependency": {
            **result["preparation_dependency"],
            "version": "query_v23_requirement_dependency_v1",
            "frozen_preparation_version": VERSION,
            "current_reference_base_version": BASE_VERSION,
        },
    }
