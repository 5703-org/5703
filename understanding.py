"""Bounded English term resolution; learner statements establish the topic."""

import re

# This explicit catalogue is deliberately small. Unknown terms are preserved;
# it is not a general-purpose abbreviation classifier or a spelling corrector.
ALIASES = {
    "DNA": "deoxyribonucleic acid",
    "RNA": "ribonucleic acid",
    "ATP": "adenosine triphosphate",
    "PCR": "polymerase chain reaction",
    "RAG": "retrieval-augmented generation",
    "API": "application programming interface",
    "LLM": "large language model",
}
AI_CONTEXT = re.compile(
    r"\b(artificial intelligence|machine learning|language models?|LLMs?|chatbots?|AI|retrieval[ -]augmented generation)\b",
    re.I,
)
BIO_RAG = re.compile(r"\b(recombination[ -]activating|RAG[ -]?[12]|ragweed)\b", re.I)
CORRECTION = re.compile(r"^(?:no[, ]+)?(?:i mean|i meant|actually[, ]+i mean)\s+(.+?)[.!?]*$", re.I)


def term_pattern(term):
    words = re.findall(r"[a-z0-9]+", term.casefold())
    return re.compile(r"(?<!\w)" + r"[\s\-\u2010-\u2015]+".join(words) + r"(?!\w)", re.I)


def _understand_v6(message, history):
    """Return preparation overrides, preserving explicit non-AI uses of RAG."""
    user_turns = [row for row in history if row.get("role") == "user"]
    correction = CORRECTION.fullmatch(message.strip())
    target = correction.group(1).strip() if correction else message
    rag = bool(re.search(r"\brag\b", target, re.I))
    prior = user_turns[-1] if user_turns else {}
    # Only a short/elliptical acronym question inherits a prior domain. A named
    # current domain always wins; assistant guesses never disambiguate a term.
    simple_rag = bool(
        re.fullmatch(
            r"(?:do you know (?:what is|what)|what is|explain|define|tell me about)?\s*rag[?.! ]*",
            target,
            re.I,
        )
    )
    ai = bool(AI_CONTEXT.search(target)) or (
        simple_rag and bool(AI_CONTEXT.search(prior.get("content", "")))
    )
    if rag and not ai and not BIO_RAG.search(target):
        return {
            "standalone_query": None,
            "intent": "clarification",
            "topic_relation": "unclear",
            "needs_clarification": True,
            "fallback_reason": "ambiguous_abbreviation:RAG",
        }
    rewritten = target
    for acronym, expansion in ALIASES.items():
        if acronym == "RAG" and (not ai or BIO_RAG.search(target)):
            continue
        if term_pattern(expansion).search(rewritten):
            if not re.search(rf"\b{acronym}\b", rewritten, re.I):
                rewritten += f" ({acronym})"
        else:
            rewritten = re.sub(rf"\b{acronym}\b", f"{expansion} ({acronym})", rewritten, flags=re.I)
    if correction:
        # Restore a prior definition request only. Complex comparisons need the
        # learner's full question rather than an invented comparison target.
        if prior and re.match(
            r"^(?:what (?:is|are)|do you know what|explain|define|tell me about)\b",
            prior.get("content", ""),
            re.I,
        ):
            rewritten = f"What is {rewritten.rstrip('?.!')}?"
        else:
            rewritten = f"Explain {rewritten.rstrip('?.!')}."
        ref = str(prior.get("message_id", prior.get("id", "")))
        return {
            "standalone_query": rewritten,
            "intent": "factual",
            "topic_relation": "new_topic",
            "referenced_message_ids": [ref] if ref else [],
            "fallback_reason": "explicit_topic_correction",
        }
    return {"standalone_query": rewritten} if rewritten != message else {}


COMPARISON = re.compile(r"\b(compare|comparison|difference(?:s)? between|versus|vs\.?)\b", re.I)
CORRECTED = re.compile(r"^(.*?)(?:,?\s+(?:not|rather than)\s+)(.+)$", re.I)
UNDERSTANDING_VERSION = "question_understanding_v2"
LEGACY_UNDERSTANDING_VERSION = "question_understanding_v1"
GRAMMAR = set(
    "a an the what which who why how is are was were do does did can could would should "
    "will please explain describe tell me about give compare comparison difference differences "
    "between versus vs and or of to in on for from with by as it its this that these those "
    "they them be been being more simpler simple briefly detail detailed example examples "
    "then also topic".split()
)


def comparison_targets(message):
    """Extract only explicit binary comparison syntax, retaining whole operands."""
    match = re.search(
        r"(?:compare|differences? between|comparison (?:of|between))\s+(.+?)\s+"
        r"(?:and|with|to|versus|vs\.?)\s+(.+?)(?:[?.!;]|$)",
        message,
        re.I,
    ) or re.search(r"(.+?)\s+(?:versus|vs\.?)\s+(.+?)(?:[?.!;]|$)", message, re.I)
    return [part.strip() for part in match.groups()] if match else []


def understand(message, history, *, version="conversation_preparer_v7"):
    if version == "conversation_preparer_v6":
        return _understand_v6(message, history)
    correction = CORRECTION.fullmatch(message.strip())
    if not correction:
        return _understand_v6(message, history)
    prior = next((row for row in reversed(history) if row.get("role") == "user"), {})
    old = prior.get("content", "")
    target = correction.group(1).strip()
    parts = CORRECTED.fullmatch(target)
    replacement, excluded = parts.groups() if parts else (target, None)
    rewritten = None
    reason = None
    if excluded:
        pattern = term_pattern(excluded)
        if old and len(pattern.findall(old)) == 1:
            rewritten = pattern.sub(lambda _: replacement, old)
            operands = comparison_targets(rewritten)
            if COMPARISON.search(old) and (
                len(operands) != 2 or operands[0].casefold() == operands[1].casefold()
            ):
                reason = "ambiguous_comparison_correction"
        elif old:
            reason = "correction_target_not_unique"
        else:
            rewritten = f"Explain {replacement}."
    elif (
        old
        and not COMPARISON.search(old)
        and len(re.findall(r"\b(it|its|that|this|they|them|those|these)\b", old, re.I)) == 1
    ):
        rewritten = re.sub(
            r"\b(it|its|that|this|they|them|those|these)\b",
            lambda match: replacement + ("'s" if match.group().casefold() == "its" else ""),
            old,
            flags=re.I,
        )
    elif old and (
        COMPARISON.search(old)
        or re.search(
            r"\b(?:not|never|without|except|unless|if|when|under|at|why|how|including)\b|\d",
            old,
            re.I,
        )
        or not re.match(
            r"^(?:what (?:is|are)|do you know what|explain|define|tell me about)\b", old, re.I
        )
    ):
        reason = "correction_requires_complete_question"
    if reason:
        return {
            "standalone_query": None,
            "intent": "clarification",
            "topic_relation": "unclear",
            "needs_clarification": True,
            "fallback_reason": reason,
        }
    if rewritten:
        expanded = _understand_v6(rewritten, history)
        ref = str(prior.get("message_id", prior.get("id", "")))
        return {
            "standalone_query": expanded.get("standalone_query", rewritten),
            "intent": "comparison" if COMPARISON.search(rewritten) else "factual",
            "topic_relation": "new_topic",
            "referenced_message_ids": [ref] if ref else [],
            "fallback_reason": "explicit_topic_correction",
            **(
                {
                    "needs_clarification": True,
                    "intent": "clarification",
                    "topic_relation": "unclear",
                }
                if expanded.get("needs_clarification")
                else {}
            ),
        }
    return _understand_v6(message, history)


def requirement_terms(text):
    """Lexical signals only; negations, digits and unknown domain words survive."""
    return list(
        dict.fromkeys(
            token.casefold()
            for token in re.findall(r"\d+(?:\.\d+)?|[\w]+(?:[-'][\w]+)*", text)
            if token.casefold() not in GRAMMAR
        )
    )


def describe_question(original, prepared, history=None):
    """Inspectable requirements, not a semantic entailment or intent classifier."""
    query = prepared.get("standalone_query") or original
    targets = comparison_targets(query)
    # Split only explicit question/clause boundaries, never every 'and' inside
    # a named concept. Keep the whole standalone question alongside all facets.
    current = prepared.get("preparation_version") in {
        "conversation_preparer_v9",
        "conversation_preparer_v10",
        "conversation_preparer_v11",
    }
    boundary = r"[?;]\s*|\s+and\s+(?=(?:why|how|what|which|when|where|explain|describe)\b)"
    if current:
        # Only explicit second requests split at a sentence period. Decimal
        # points and ordinary declarative context remain within their clause.
        boundary += r"|[.!]\s+(?=(?:also|additionally|then|why|how|what|which|when|where|explain|describe|give|compare|list|show|calculate|define|write)\b)"
    parts = [
        p.strip(" ?.!")
        for p in re.split(
            boundary,
            query,
            flags=re.I,
        )
        if p.strip(" ?.!")
    ]
    explicit_clause_count = len(parts)
    comparison_only = len(parts) == 1 and len(targets) == 2
    if comparison_only:
        parts = [f"Comparison subject: {target}" for target in targets]
    overflow = len(parts) > 8
    # Never discard requirements silently: the last facet retains the remainder.
    if overflow:
        parts = parts[:7] + ["; ".join(parts[7:])]
    correction_match = CORRECTION.fullmatch(original.strip())
    correction = None
    if correction_match:
        target = correction_match.group(1).strip()
        pair = CORRECTED.fullmatch(target)
        replacement, excluded = pair.groups() if pair else (target, None)
        prior = next(
            (r.get("content", "") for r in reversed(history or []) if r.get("role") == "user"), None
        )
        correction = {"replacement": replacement, "excluded": excluded, "prior_question": prior}
    return {
        "version": UNDERSTANDING_VERSION if current else LEGACY_UNDERSTANDING_VERSION,
        **(
            {
                "explicit_clause_count": explicit_clause_count,
                "facet_origin": "comparison_operands" if comparison_only else "explicit_clauses",
            }
            if current
            else {}
        ),
        "method": "bounded_deterministic",
        "original_message": original,
        "standalone_query": prepared.get("standalone_query"),
        "intent": prepared["intent"],
        "topic_relation": prepared["topic_relation"],
        "needs_clarification": prepared["needs_clarification"],
        "clarification_reason": prepared.get("fallback_reason")
        if prepared["needs_clarification"]
        else None,
        "requested_facets": [
            {
                "id": f"part_{i}",
                "request": part,
                "terms": requirement_terms(part.replace("Comparison subject: ", "")),
            }
            for i, part in enumerate(parts, 1)
        ],
        "comparison_targets": targets,
        "constraints": {
            "negation": re.findall(
                r"\b(?:not|never|without|except|unless|cannot|can't|don't|doesn't)\b", query, re.I
            ),
            "numbers": re.findall(
                r"(?<!\w)[+-]?\d+(?:\.\d+)?(?:\s*(?:%|°[CFK]|[a-zA-Z]+))?", query
            ),
            "conditions": re.findall(
                r"\b(?:if|when|unless|provided that|at|under)\s+[^?.!;]+", query, re.I
            ),
        },
        "correction": correction,
        "referenced_message_ids": prepared.get("referenced_message_ids", []),
        "limitations": [
            "Lexical clause decomposition; no semantic truth or support guarantee.",
            "Unknown expressions remain verbatim; no optional LLM understanding call.",
        ]
        + (
            ["More than eight clauses: remaining clauses grouped in final facet."]
            if overflow
            else []
        ),
    }


def missing_explicit_terms(query, evidence):
    """Protect expanded named concepts from prefix/substring substitutions."""
    missing = []
    for acronym, expansion in ALIASES.items():
        if not term_pattern(expansion).search(query):
            continue
        full = term_pattern(expansion).search(evidence)
        short = re.search(rf"\b{acronym}\b", evidence, re.I)
        if acronym == "RAG":
            short = short and AI_CONTEXT.search(evidence) and not BIO_RAG.search(evidence)
        if not full and not short:
            missing.append(acronym)
    return missing
