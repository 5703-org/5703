"""Versioned question requirements with verbatim conditions and rewrite auditing."""

from __future__ import annotations

import hashlib
import re

from .understanding import comparison_targets, describe_question, requirement_terms

VERSION = "question_requirements_v3"
NEGATION = re.compile(r"\b(?:not|never|without|except|unless|cannot|can't|don't|doesn't)\b", re.I)
NUMBER = re.compile(r"(?<!\w)[+-]?\d+(?:\.\d+)?(?:\s*(?:%|°[CFK]|[a-zA-Z]+(?:/[a-zA-Z]+)?))?")
CONDITION = re.compile(
    r"\b(?:if|when|unless|provided that|assuming|at|under|during|before|after|only)\b[^?;!]*(?:$|(?=[?;!]))",
    re.I,
)
INTENTS = (
    ("comparison", r"\b(?:compare|comparison|difference|versus|vs)\b"),
    ("calculation", r"\b(?:calculate|compute|determine|how much|how many)\b"),
    ("causal_explanation", r"\b(?:why|cause|causes|reason)\b"),
    ("example", r"\b(?:example|illustrate|application|apply)\b"),
    ("correction", r"\b(?:correct|mistake|wrong|misconception)\b"),
    ("definition", r"\b(?:what is|what are|define|definition)\b"),
    ("explanation", r"\b(?:explain|describe|how)\b"),
)


def _spans(pattern, text):
    return [{"text": m.group(), "start": m.start(), "end": m.end()} for m in pattern.finditer(text)]


def describe_requirements(original, prepared, history=None):
    """Retain exact semantics for a checker; syntax extraction is not an entailment claim."""
    result = describe_question(original, prepared, history)
    query = prepared.get("standalone_query") or original
    constraints = {
        "negation": _spans(NEGATION, original),
        "quantities_and_units": _spans(NUMBER, original),
        "conditions_and_time": _spans(CONDITION, original),
    }
    # A correction intentionally removes an old operand. Its new message remains
    # verbatim in the model input; the prior task and replacement are recorded.
    correction = result.get("correction")
    missing = []
    if not correction:
        query_words = set(requirement_terms(query))
        for category, spans in constraints.items():
            for span in spans:
                if not set(requirement_terms(span["text"])) <= query_words:
                    missing.append({"kind": category, **span})
        if missing:
            query = original
    targets = comparison_targets(query)
    clauses = re.split(
        r"[?;]\s*|[.!]\s+(?=(?:also|then|why|how|what|explain|describe|give|compare|calculate)\b)|\s+and\s+(?=(?:why|how|what|explain|describe)\b)",
        query,
        flags=re.I,
    )
    clauses = [part.strip(" ?.!;") for part in clauses if part.strip(" ?.!;")]
    if len(clauses) > 8:
        clauses = clauses[:7] + ["; ".join(clauses[7:])]
    points = []
    for index, clause in enumerate(clauses or [query], 1):
        intent = next(
            (name for name, pattern in INTENTS if re.search(pattern, clause, re.I)), "explanation"
        )
        points.append(
            {
                "id": f"requirement_{index:02d}",
                "request": clause,
                "terms": requirement_terms(clause),
                "intent": intent,
                "objects": comparison_targets(clause),
                "relation": "compare_both_objects_on_requested_axes"
                if intent == "comparison"
                else intent,
                "conditions": [v["text"] for rows in constraints.values() for v in rows],
                "origin": "verbatim_question_structure_v3",
            }
        )
    return {
        **result,
        "version": VERSION,
        "standalone_query": query,
        "requested_facets": points,
        "required_knowledge": points,
        "comparison_targets": targets,
        "semantic_intents": [p["intent"] for p in points],
        "preserved_constraints": constraints,
        "original_question_hash": hashlib.sha256(original.encode()).hexdigest(),
        "rewrite_audit": {
            "version": "critical_condition_preservation_v1",
            "missing": missing,
            "fallback_to_original": bool(missing),
            "semantic_equivalence": None,
        },
        "limitations": [
            "Deterministic intent and condition extraction; semantic coverage is assessed separately against submitted sources."
        ],
    }
