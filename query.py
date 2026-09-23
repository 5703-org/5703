"""Small deterministic preparation for obvious referents with explicit ambiguity."""

from __future__ import annotations
import re
from typing import Any
from contracts.models import PreparedQuery
from .understanding import understand

VERSION = "conversation_preparer_v11"
DECLARATIVE_VERSION = "conversation_preparer_v10"
FACET_VERSION = "conversation_preparer_v9"
LOCAL_QUESTION_VERSION = "conversation_preparer_v8"
PREVIOUS_VERSION = "conversation_preparer_v7"
LEGACY_VERSION = "conversation_preparer_v6"
DEPENDENT = re.compile(r"\b(it|its|that|this|they|them|those|these|again)\b", re.I)
REEXPLAIN = re.compile(
    r"\b(simpler|simplify|more simply|rephrase|again|example|analogy|more detail|shorter|summari[sz]e)\b",
    re.I,
)
EXPANSION = re.compile(
    r"\b(examples?|analog(?:y|ies)|applications?|apply|more detail|elaborate|deeper|why|how|compare|difference|what else|tell me more)\b",
    re.I,
)


def evidence_strategy(message: str, prepared: dict | None) -> str:
    """Reuse only a resolved restatement/source request; new knowledge needs retrieval."""
    if not prepared:
        return "retrieve"
    if prepared.get("needs_clarification") or prepared.get("intent") == "social":
        return "none"
    resolved = prepared.get("topic_relation") == "same_topic" and prepared.get(
        "referenced_message_ids"
    )
    if not resolved:
        return "retrieve"
    if prepared.get("intent") == "source_request":
        return "reuse_only"
    if EXPANSION.search(message):
        return "retrieve_and_reuse"
    if prepared.get("intent") == "reexplain":
        return "reuse_only"
    return "retrieve_and_reuse"


def has_local_referent(
    message: str,
    *,
    multi_question: bool = True,
    discourse_topic: bool = False,
    declarative_problem: bool = False,
) -> bool:
    """Keep an explicit subject before a later clause; do not import an old topic.

    This bounded syntax rule does not resolve arbitrary English coreference. It
    only recognizes a named subject before the first pronoun and a subsequent
    coordinating/subordinate clause, leaving the complete question unchanged.
    """
    first = DEPENDENT.search(message)
    if not first:
        return False
    prefix = message[: first.start()]
    boundaries = list(re.finditer(r"\b(and|when|while|because|if|where|although)\b", prefix, re.I))
    topic_clause = prefix[: boundaries[-1].start()] if boundaries else prefix
    # Question grammar and generic referents cannot establish a named subject.
    grammar = set(
        "what why how who which is are was were does do did can could would should will happens happen happening to of a an the in on for with from at by explain describe tell me please about thing things something anything everything process concept topic question answer change changes result results give example examples analogy another uses use produces produce makes make contains contain has have".split()
    )
    if multi_question:
        # A complete earlier question in this same message supplies its own
        # named subject. Do not import older conversation topics merely because
        # the next question uses 'it' or 'this topic'. A prior pronoun would have
        # been the first dependent match and cannot establish this boundary.
        earlier = re.split(r"[?.!](?:\s+|$)", prefix)
        if len(earlier) > 1:
            clauses = [clause.strip() for clause in earlier[:-1] if clause.strip()]
            explicit = [
                clause
                for clause in clauses
                if re.match(
                    r"^(?:what|how|why|when|where|which|explain|describe|define|compare)\b",
                    clause,
                    re.I,
                )
                and set(re.findall(r"[a-z][a-z-]*", clause.casefold())) - grammar
            ]
            if declarative_problem and len(clauses) == 1 and not explicit:
                # One complete declarative problem can introduce the referent.
                # Keep the entire original message; never substitute a guessed noun.
                introduced = re.match(
                    r"^(?:a|an|the|one)\s+([a-z][a-z -]{0,90}?)\s+(?:has|have|is|are|was|were|occupies|contains|uses|moves|travels|grows|starts|measures|weighs|extends|contracts|absorbs|releases|experiences)\b",
                    clauses[0],
                    re.I,
                )
                if introduced and not re.search(
                    r"\b(and|or|versus|vs)\b", introduced.group(1), re.I
                ):
                    # A named demonstrative must repeat a supplied subject word.
                    demonstrative = re.match(
                        r"(?:this|that)\s+([a-z][a-z-]*)", message[first.start() :], re.I
                    )
                    subject_words = set(re.findall(r"[a-z][a-z-]*", introduced.group(1).casefold()))
                    if not demonstrative or demonstrative.group(1).casefold() in subject_words:
                        return True
            whole_topic = discourse_topic and re.match(
                r"(?:this|that)\s+(?:topic|comparison|question|discussion)\b",
                message[first.start() :],
                re.I,
            )
            return len(explicit) == 1 and (
                bool(whole_topic)
                or not re.search(
                    r"\b(compare|comparison|difference between|versus)\b", explicit[0], re.I
                )
            )
    if discourse_topic:
        # A named subject immediately performing an explicit predicate can
        # establish a possessive referent inside a complete current problem.
        # Question auxiliaries alone ('What does it...') do not name a subject.
        predicate = re.search(r"\b([a-z][a-z-]*s)\s+$", prefix, re.I)
        if predicate:
            subject_prefix = re.split(r"[:;?!]|\.(?:\s+|$)", prefix[: predicate.start()])[-1]
            subject_words = (
                set(re.findall(r"[a-z][a-z-]*", subject_prefix.casefold()))
                - grammar
                - set(
                    "hint hints solution solving only first step steps answer explanation".split()
                )
            )
            if subject_words and predicate.group(1).casefold() not in {"is", "was", "does"}:
                return True
    named = bool(set(re.findall(r"[a-z][a-z-]*", topic_clause.casefold())) - grammar)
    return named and bool(
        boundaries or re.search(r"\b(uses?|produces?|makes?|contains?|has|have)\b", prefix, re.I)
    )


def local_reference_v11(message: str) -> bool:
    """Recognize bounded current-message antecedents without rewriting the question.

    A possessive inside a comparison clause is different from an ambiguous bare
    pronoun after a completed comparison. No prior assistant text is consulted.
    """
    first = DEPENDENT.search(message)
    if not first:
        return False
    prefix, suffix = message[: first.start()], message[first.start() :]
    clauses = [part.strip() for part in re.split(r"[.!?](?:\s+|$)", prefix) if part.strip()]
    if len(clauses) > 1 and re.fullmatch(
        r"(?:calculate|determine|find|what is|what are)", clauses[-1], re.I
    ):
        clauses.pop()
    if len(clauses) != 1:
        return False
    clause = clauses[0]
    if re.match(r"(?:this|that)\s+(?:asks|question|problem)\b", suffix, re.I):
        return bool(
            re.search(r"\b(?:calculate|determine|find|explain|describe)\b.+\w", clause, re.I)
        )
    if first.group().casefold() != "its":
        return False
    # In-clause possessive: 'radius of a neutral atom ... its common cation'.
    if not re.search(r"[.!?]\s*$", prefix) and re.search(
        r"\b(?:a|an|the)\s+(?:[a-z][a-z-]*\s+){0,4}[a-z][a-z-]*\s+with\b", clause, re.I
    ):
        return not bool(re.search(r"\b(?:and|or|versus|vs)\b", clause, re.I))
    # A complete numerical/declarative problem may have a leading condition.
    introduced = re.search(
        r"\b(?:a|an|the|one)\s+([a-z][a-z -]{0,90}?)\s+(?:has|is|occupies|contains|measures|weighs|travels|grows)\b",
        clause,
        re.I,
    )
    return bool(
        introduced
        and re.search(r"\d", clause)
        and not re.search(r"\b(?:and|or|versus|vs)\b", introduced.group(1), re.I)
        and not re.search(r"\b(?:compare|comparison|versus)\b", clause, re.I)
    )


def subject_from(message: str, *, reject_interrogative: bool = False) -> str | None:
    text = message.strip().rstrip("?.!")
    correction = re.search(
        r"(?:i meant|i mean|actually[,]?\s*(?:i mean)?)\s+(.+?)(?:,?\s+not\s+.+)?$", text, re.I
    )
    if correction:
        return correction.group(1).strip()
    explicit = re.search(
        r"\b(?:example|analogy|sources?|citations?)\s+(?:of|for|about|on)\s+(.+)", text, re.I
    )
    if explicit:
        text = explicit.group(1).strip()
    text = re.sub(
        r"^(?:what (?:is|are)|explain|describe|tell me about|can you explain|how does|why does)\s+",
        "",
        text,
        flags=re.I,
    )
    # Isolate an explicitly named subject before presentation requests and
    # subordinate questions; the full learner question remains unchanged.
    text = re.split(
        r"\s+(?:in detail|in simple terms|in simpler terms|more simply|briefly|including|with an example)\b|,\s*(?:and|including|with|using)\b",
        text,
        maxsplit=1,
        flags=re.I,
    )[0].strip()
    text = re.sub(
        r"\s+(?:work|works|happen|happens|need|needs|use|uses|require|requires|occur|occurs)\b.*$",
        "",
        text,
        flags=re.I,
    )
    text = re.sub(r"\s+(?:in simple terms|in detail|briefly|please)$", "", text, flags=re.I)
    text = re.sub(r"\s+(?:more simply|again|in simpler terms)$", "", text, flags=re.I)
    if reject_interrogative and re.fullmatch(r"(?:what|why|how|when|where|who|which)", text, re.I):
        return None
    if not text or DEPENDENT.search(text) or REEXPLAIN.search(text) or len(text) > 180:
        return None
    return text


def prepare_query(
    message: str,
    history: list[dict] | None = None,
    summary: str | None = None,
    *,
    version: str = VERSION,
) -> PreparedQuery:
    if version not in (
        VERSION,
        DECLARATIVE_VERSION,
        FACET_VERSION,
        LOCAL_QUESTION_VERSION,
        PREVIOUS_VERSION,
        LEGACY_VERSION,
    ):
        raise ValueError("Unsupported frozen query preparation version")
    history = history or []
    original = message.strip()
    if not original:
        raise ValueError("A nonblank current message is required")
    fields: dict[str, Any] = dict(
        original_message=original,
        standalone_query=original,
        intent="factual",
        topic_relation="new_topic",
        referenced_message_ids=[],
        needs_clarification=False,
        preparation_version=version,
        fallback_reason=None,
    )
    if not re.search(r"\w", original):
        return PreparedQuery(
            **{
                **fields,
                "standalone_query": None,
                "intent": "clarification",
                "topic_relation": "unclear",
                "needs_clarification": True,
                "fallback_reason": "missing_question",
            }
        )
    if re.fullmatch(r"(?:hi|hello|hey|thanks|thank you|okay|ok|great|bye)[!. ]*", original, re.I):
        return PreparedQuery(
            **{
                **fields,
                "standalone_query": None,
                "intent": "social",
                "topic_relation": "same_topic",
            }
        )
    understood = understand(original, history, version=version)
    if understood.get("needs_clarification") or understood.get("fallback_reason"):
        return PreparedQuery(**{**fields, **understood})
    fields.update(understood)
    first_referent = DEPENDENT.search(original)
    facet_semantics = version in (VERSION, DECLARATIVE_VERSION, FACET_VERSION)
    local_questions = version in (
        VERSION,
        DECLARATIVE_VERSION,
        FACET_VERSION,
        LOCAL_QUESTION_VERSION,
    )
    local_referent = has_local_referent(
        original,
        multi_question=local_questions,
        discourse_topic=facet_semantics,
        declarative_problem=version in (VERSION, DECLARATIVE_VERSION),
    )
    if version == VERSION and local_reference_v11(original):
        local_referent = True
    if local_questions and first_referent:
        clauses = [
            clause.strip()
            for clause in re.split(r"[?.!](?:\s+|$)", original[: first_referent.start()])[:-1]
            if re.match(
                r"^(?:what|how|why|when|where|which|explain|describe|define|compare)\b",
                clause.strip(),
                re.I,
            )
        ]
        if not local_referent and (
            len(clauses) > 1
            or any(
                re.search(r"\b(compare|comparison|difference between|versus)\b", clause, re.I)
                for clause in clauses
            )
        ):
            return PreparedQuery(
                **{
                    **fields,
                    "standalone_query": None,
                    "intent": "clarification",
                    "topic_relation": "unclear",
                    "needs_clarification": True,
                    "fallback_reason": "multiple_subjects_in_current_message",
                }
            )
    source_request = bool(
        re.search(r"\b(source|sources|citation|citations|where did .*come from)\b", original, re.I)
    )
    reexplain = bool(REEXPLAIN.search(original))
    dependent = (
        (bool(DEPENDENT.search(original)) and not local_referent)
        or reexplain
        or source_request
        or bool(re.fullmatch(r"(?:why|how|tell me more|continue|go on)[?.! ]*", original, re.I))
    )
    explicit_example = re.search(r"\b(?:example|analogy)\s+(?:of|for|about)\s+(.+)", original, re.I)
    if explicit_example and not DEPENDENT.search(explicit_example.group(1)):
        return PreparedQuery(**{**fields, "intent": "reexplain"})
    explicit_source = re.search(
        r"\b(?:sources?|citations?)\s+(?:of|for|about|on)\s+(.+)", original, re.I
    )
    if explicit_source and not DEPENDENT.search(explicit_source.group(1)):
        return PreparedQuery(**{**fields, "intent": "source_request"})
    if reexplain and re.match(
        r"^(?:explain|describe|summari[sz]e|simplify|rephrase|what is|what are|how does|why does)\s+",
        original,
        re.I,
    ):
        explicit_topic = subject_from(original, reject_interrogative=facet_semantics)
        if explicit_topic:
            return PreparedQuery(**{**fields, "intent": "reexplain"})
    antecedent, ref = None, None
    full_prior_question = None
    for prior in reversed(history):
        if prior.get("role") != "user":
            continue
        if (
            re.search(
                r"\b(compare|comparison|difference between)\b", prior.get("content", ""), re.I
            )
            and dependent
        ):
            fields["fallback_reason"] = "ambiguous_referent_after_comparison"
            break
        old_question = prior.get("content", "")
        possible = subject_from(old_question, reject_interrogative=facet_semantics)
        if facet_semantics and not possible and dependent and not DEPENDENT.search(old_question):
            # A grammar-only extracted 'What' is not a topic. Preserve the whole
            # explicit learner question, including its action and conditions,
            # rather than inventing a noun or dropping the conditional clause.
            unsafe = subject_from(old_question)
            if unsafe and re.fullmatch(r"(?:what|why|how|when|where|who|which)", unsafe, re.I):
                possible = old_question
                full_prior_question = old_question
        if possible:
            antecedent = possible
            ref = str(prior.get("message_id", prior.get("id", "")))
            break
    if not antecedent and not fields["fallback_reason"] and summary:
        pointers = [
            (mid, subject_from(content, reject_interrogative=facet_semantics))
            for mid, content in re.findall(r"^\[([^\]]+)\] (.+)$", summary, re.M)
        ]
        pointers = [(mid, subject) for mid, subject in pointers if subject]
        if len({subject.casefold() for _, subject in pointers if subject is not None}) == 1:
            ref, antecedent = pointers[-1]
    if dependent and not antecedent:
        return PreparedQuery(
            **{
                **fields,
                "standalone_query": None,
                "intent": "clarification",
                "topic_relation": "unclear",
                "needs_clarification": True,
                "fallback_reason": fields["fallback_reason"] or "missing_referent",
            }
        )
    if dependent:
        assert antecedent is not None  # The missing-antecedent branch above returns.
        if full_prior_question:
            rewritten = original + " Prior learner question: " + full_prior_question
        elif local_referent:
            rewritten = original
        else:
            rewritten = re.sub(
                r"\b(it|that|this|they|them|those|these)\b",
                lambda _: antecedent,
                original,
                flags=re.I,
            )
            rewritten = re.sub(r"\bits\b", lambda _: antecedent + "'s", rewritten, flags=re.I)
        if antecedent.casefold() not in rewritten.casefold():
            rewritten += " Topic: " + antecedent + "."
        if reexplain or source_request:
            # A restatement/source request points to the immediately preceding
            # completed exchange even when its user question was itself dependent.
            latest_user = next((m for m in reversed(history) if m.get("role") == "user"), None)
            if latest_user:
                ref = str(latest_user.get("message_id", latest_user.get("id", "")))
        fields.update(
            standalone_query=rewritten,
            topic_relation="same_topic",
            referenced_message_ids=[ref] if ref else [],
            intent="source_request"
            if source_request
            else "reexplain"
            if reexplain
            else "comparison"
            if re.search(r"compar|difference|versus", original, re.I)
            else "follow_up",
        )
    elif re.search(r"compar|difference|versus", original, re.I):
        fields["intent"] = "comparison"
    elif antecedent and antecedent.casefold() in original.casefold():
        fields["topic_relation"] = "same_topic"
    if not fields["needs_clarification"] and fields["standalone_query"]:
        resolved = understand(fields["standalone_query"], history, version=version)
        fields.update(resolved)
    return PreparedQuery(**fields)
