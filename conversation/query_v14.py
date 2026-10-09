"""Opt-in current-message anchors after a verified V13 missing-referent result.

The wrapper preserves frozen prior preparers and never substitutes a guessed
subject. It permits retrieval of the whole self-contained question, leaving
semantic interpretation to the ordinary answering/checking contract.
"""

from __future__ import annotations

import re

from contracts.models import PreparedQuery

from . import query as previous
from . import requirements_v4 as requirement_producer
from .understanding import GRAMMAR

VERSION = "conversation_preparer_v14"
BASE_VERSION = "conversation_preparer_v13"

POSSESSOR = re.compile(
    r"\b(?:a|an|the)\s+"
    r"((?!(?:a|an|the)\b)[a-z][a-z-]*"
    r"(?:\s+(?!(?:a|an|the)\b)[a-z][a-z-]*){0,3})['’]s\b",
    re.I,
)
ALL_POSSESSORS = re.compile(r"\b[a-z][a-z-]*['’]s\b", re.I)
REQUEST_START = re.compile(
    r"^(?:what|why|how|when|where|which|does|do|can|could|will|would|should|"
    r"explain|describe|define|compare|follow|distinguish|trace|identify|determine|calculate)\b",
    re.I,
)
SOURCE = re.compile(r"\bsources?\b", re.I)
SOURCE_PRESENTATION = re.compile(
    r"\b(?:cite|cited|citation|citations)\b|"
    r"\b(?:show|give|list|provide|find|open|display|share|verify|check)\b"
    r"[^.;?!]{0,60}\b(?:sources?|citations?)\b|"
    r"\bwhere\b[^.;?!]*\b(?:source|sources|come from|read|find|look)\b|"
    r"\bhow\b[^.;?!]*\b(?:verify|cite|source|sources)\b",
    re.I,
)
ANCHOR_GRAMMAR = GRAMMAR | set(
    "does do can could will would should follow distinguish trace identify determine calculate "
    "sequence form forms type types kind kinds question questions answer answers concept concepts "
    "topic topics source sources process processes thing things something anything everything "
    "not without never only if unless except provided then detail details storage described through ".split()
)


def _parallel_possessive_anchor(message):
    referents = list(previous.DEPENDENT.finditer(message))
    if len(referents) != 1 or referents[0].group().casefold() != "its":
        return False
    first = referents[0]
    prefix, suffix = message[: first.start()], message[first.end() :]
    # One explicit owner inside the question supplies parallel possessive
    # operands. Neither an old actor nor a second current owner can substitute.
    if len(ALL_POSSESSORS.findall(prefix)) != 1 or re.search(r"[.!?;:]", prefix):
        return False
    if not re.match(r"^(?:does|do|can|could|will|would|should)\b", prefix, re.I):
        return False
    owners = list(POSSESSOR.finditer(prefix))
    if len(owners) != 1 or not re.search(r"\b(?:and|or)\s+(?:only\s+)?$", prefix, re.I):
        return False
    owner = owners[0]
    if not set(re.findall(r"[a-z][a-z-]*", owner.group(1).casefold())) - ANCHOR_GRAMMAR:
        return False
    owned_operand = prefix[owner.end() :]
    if not set(re.findall(r"[a-z][a-z-]*", owned_operand.casefold())) - ANCHOR_GRAMMAR:
        return False
    return bool(re.match(r"\s+[a-z][a-z-]*", suffix, re.I))


def _content_source_anchor(message):
    if previous.DEPENDENT.search(message) or previous.REEXPLAIN.search(message):
        return False
    if not REQUEST_START.match(message) or SOURCE_PRESENTATION.search(message):
        return False
    first = SOURCE.search(message)
    if first is None:
        return False
    # A content-bearing earlier clause names what is being studied before
    # source/storage/destination terminology. "Explain the source" or a
    # grammar-only sequence does not establish that subject.
    words = set(re.findall(r"[a-z][a-z-]*", message[: first.start()].casefold()))
    return bool(words - ANCHOR_GRAMMAR)


def prepare_query(message, history=None, summary=None, *, version=VERSION) -> PreparedQuery:
    if version != VERSION:
        raise ValueError("Unsupported frozen query preparation version")
    original = previous.prepare_query(message, history, summary, version=BASE_VERSION)
    result = original.model_dump()
    result["preparation_version"] = VERSION
    if original.needs_clarification and original.fallback_reason == "missing_referent":
        possessive = _parallel_possessive_anchor(original.original_message)
        content_source = _content_source_anchor(original.original_message)
        if possessive or content_source:
            text = original.original_message
            result.update(
                standalone_query=text,
                intent="comparison"
                if re.search(
                    r"\b(?:compare|comparison|difference|distinguish|distinction|versus)\b",
                    text,
                    re.I,
                )
                else "factual",
                topic_relation="new_topic",
                referenced_message_ids=[],
                needs_clarification=False,
                fallback_reason="current_parallel_possessive_anchor_v14"
                if possessive
                else "current_named_content_source_v14",
            )
    return PreparedQuery(**result)


def describe_requirements(original, prepared, history=None):
    """Reuse the pinned current syntax without changing the V14 request identity.

    V14 adds local eligibility only; the prior requirement producer still needs
    its V13 metadata to recognize sentence/facet boundaries. Actual original
    text, the prepared query, reading context and source requirements are intact.
    """
    if prepared.get("preparation_version") != VERSION:
        raise ValueError("Unsupported frozen query preparation dependency")
    syntax_input = {**prepared, "preparation_version": BASE_VERSION}
    result = requirement_producer.describe_requirements(original, syntax_input, history)
    return {
        **result,
        "preparation_dependency": {
            "version": "query_v14_requirement_dependency_v1",
            "frozen_preparation_version": VERSION,
            "syntax_preparation_version": BASE_VERSION,
            "requirements_version": requirement_producer.VERSION,
        },
    }
