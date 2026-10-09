"""Keep a complete current observation and its explicit analytical request.

The bounded local rule admits retrieval of the original text. It does not
substitute a subject or establish scientific support or semantic equivalence.
Frozen V18 owns all earlier conversation and comparison-axis behavior.
"""

from __future__ import annotations

import hashlib
import re

from contracts.models import PreparedQuery
from . import query_v18 as previous
from .query import DEPENDENT
from .query_v14 import ANCHOR_GRAMMAR

VERSION = "conversation_preparer_v19"
BASE_VERSION = previous.VERSION
RESOLUTION_VERSION = "current_complete_observation_reference_v1"
_MESSAGE = re.compile(
    r"^(?P<observation>[^.!?\r\n]{15,500})\.\s+"
    r"(?P<request>What\s+does\s+this\s+(?:illustrate|show|demonstrate|reveal)\s+"
    r"about\s+(?P<topic>[^.!?\r\n]+)\?)"
    r"(?:\s+(?P<hint>(?:Please\s+)?give\s+me\s+(?:one|a)\s+hint"
    r"\s+for\s+this\s+step\.))?$",
    re.I,
)
_SUBJECT = re.compile(
    r"^(?:a|an|the|one)\s+(?P<subject>[a-z][a-z -]{0,90}?)\s+"
    r"(?:attacks|responds|absorbs|releases|moves|travels|grows|expands|contracts|"
    r"dissolves|falls|starts|measures|weighs|extends|contains|occupies|uses|"
    r"has|is|was|does\s+not\s+[a-z][a-z-]*)\b.+$",
    re.I,
)
_RELATIVE_OBJECT = re.compile(
    r"\b(?:a|an|the)\s+(?P<object>[a-z][a-z-]*(?:\s+[a-z][a-z-]*){0,4})\s+$",
    re.I,
)
_RELATIVE_PREDICATE = re.compile(
    r"^that\s+(?:does|do|is|are|was|were|can|could|will|would|has|have)\b",
    re.I,
)
_POINTER = re.compile(
    r"\b(?:previous|prior|earlier|above|below|aforementioned|mentioned|cited|"
    r"preceding|following|another|former|latter)\b",
    re.I,
)
_TOPIC_BOUNDARY = re.compile(
    r"[,;]|\b(?:and|or|between|with|from|to|under|after|before|when|if|unless|"
    r"without|assuming|provided)\b",
    re.I,
)
_GENERIC = ANCHOR_GRAMMAR | set(
    "observation observations event events situation situations mechanism mechanisms "
    "method methods phenomenon phenomena system systems example examples".split()
)


def _named_head(text):
    words = re.findall(r"[a-z][a-z-]*", text.casefold())
    return bool(words and words[-1] not in _GENERIC)


def _current_resolution(message):
    match = _MESSAGE.fullmatch(message)
    if match is None or _POINTER.search(message):
        return None
    observation = match["observation"]
    subject = _SUBJECT.fullmatch(observation)
    if subject is None or not _named_head(subject["subject"]):
        return None
    spans = []
    for ref in DEPENDENT.finditer(observation):
        owner = _RELATIVE_OBJECT.search(observation[: ref.start()])
        if (
            ref.group().casefold() != "that"
            or owner is None
            or not _named_head(owner["object"])
            or not _RELATIVE_PREDICATE.match(observation[ref.start() :])
        ):
            return None
        spans.append({"kind": "local_noun_relative_that", "start": ref.start(), "end": ref.end()})
    topic = match["topic"]
    refs = list(DEPENDENT.finditer(topic))
    if refs and (len(refs) != 1 or refs[0].group().casefold() != "its"):
        return None
    owned_topic = topic[: refs[0].start()] if refs else topic
    if refs and re.search(r"\b(?:and|or|versus|vs|between)\b", owned_topic, re.I):
        return None
    head = _TOPIC_BOUNDARY.split(owned_topic, maxsplit=1)[0].strip()
    if not _named_head(head):
        return None
    this = re.search(r"\bthis\b", match["request"], re.I)
    spans.append(
        {
            "kind": "complete_current_observation",
            "start": match.start("request") + this.start(),
            "end": match.start("request") + this.end(),
        }
    )
    if refs:
        spans.append(
            {
                "kind": "explicit_current_analytical_subject_possessive",
                "start": match.start("topic") + refs[0].start(),
                "end": match.start("topic") + refs[0].end(),
            }
        )
    if match["hint"]:
        ref = re.search(r"\bthis\b", match["hint"], re.I)
        spans.append(
            {
                "kind": "current_request_hint_step",
                "start": match.start("hint") + ref.start(),
                "end": match.start("hint") + ref.end(),
            }
        )
    return {
        "version": RESOLUTION_VERSION,
        "source_text": message,
        "source_sha256": hashlib.sha256(message.encode()).hexdigest(),
        "coordinate_space": "current_original_message",
        "referent_spans": spans,
        "semantic_equivalence": None,
        "semantic_sufficiency": None,
        "human_rating": None,
    }


def prepare_query(message, history=None, summary=None, *, version=VERSION) -> PreparedQuery:
    if version != VERSION:
        raise ValueError("Unsupported frozen query preparation version")
    result = previous.prepare_query(message, history, summary).model_dump()
    result["preparation_version"] = VERSION
    resolution = _current_resolution(result["original_message"])
    if resolution is not None:
        # The complete current observation owns this request, even if an older
        # comparison could otherwise attract the historical pronoun resolver.
        result.update(
            standalone_query=result["original_message"],
            intent="comparison"
            if re.search(
                r"\b(?:compare|compared|comparison|difference|versus|distinguish)\b",
                result["original_message"],
                re.I,
            )
            else "factual",
            topic_relation="new_topic",
            referenced_message_ids=[],
            needs_clarification=False,
            fallback_reason=RESOLUTION_VERSION,
        )
    return PreparedQuery(**result)


def describe_requirements(original, prepared, history=None):
    if prepared.get("preparation_version") != VERSION:
        raise ValueError("Unsupported frozen query preparation dependency")
    result = previous.describe_requirements(
        original, {**prepared, "preparation_version": BASE_VERSION}, history
    )
    if prepared.get("fallback_reason") == RESOLUTION_VERSION:
        resolution = _current_resolution(prepared["original_message"])
        if (
            resolution is None
            or prepared["original_message"] != original.strip()
            or prepared["standalone_query"] != prepared["original_message"]
            or prepared != prepare_query(original, history).model_dump()
        ):
            raise ValueError("The frozen current observation reference is unavailable")
        result = {**result, "current_message_resolution": resolution}
    return {
        **result,
        "preparation_dependency": {
            **result["preparation_dependency"],
            "version": "query_v19_requirement_dependency_v1",
            "frozen_preparation_version": VERSION,
            "current_reference_base_version": BASE_VERSION,
        },
    }
