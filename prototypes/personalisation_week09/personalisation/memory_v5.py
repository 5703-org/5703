"""Versioned owned-source conditions for saved learning preferences.

Historical V2/V3 engines remain separate. This engine uses their fixed priority
and bounded context assembly; uncertain source conditions are withheld.
"""

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import re
import time

from . import memory_v2 as rules, memory_v3 as legacy

SELECTOR_VERSION = "query_conditioned_memory_v5"
POLICY_VERSION = "owned_preference_conditions_v2"
MAX_SOURCE_BYTES = 64 * 1024
MAX_CORRECTION_REVISIONS = 64
SPECIFIC_PHRASES = {
    "cellular respiration",
    "calvin cycle",
    "ideal gas law",
    "activation energy",
}
KNOWN_SCOPES = (
    set(legacy.BROAD_SCOPES)
    | SPECIFIC_PHRASES
    | {
        rules.scope_name(term)
        for terms in rules.TOPICS.values()
        for term in terms
        if len(rules.scope_name(term)) > 1
    }
)
GLOBAL_TERMS = {"all subjects", "all topics", "all questions", "any subject"}
CUES = re.compile(
    r"\b(?:for|in|about|when|during|unless|except|outside|only if|at exam time)\b", re.I
)
COMPLEX = re.compile(
    r"\b(?:unless|except|outside|only if|not when|not for|but not|rather than|at exam time|whether)\b",
    re.I,
)
EXAMPLE = re.compile(r"\bfor examples?\b|\be\s*\.\s*g\s*\.|\bi\s*\.\s*e\s*\.", re.I)
SCOPE = re.compile(
    r"\b(?:for|in|about|when (?:studying|learning|discussing))\s+(?:questions about\s+)?(.+?)[.!?]*$",
    re.I,
)
ATTRIBUTABLE = re.compile(
    r"^(?:(?:actually|from now on|remember(?: that)?|please remember)[,:]?\s+)*"
    r"(?:i prefer|i learn best|i no longer prefer|always (?:use|give|explain))\b",
    re.I,
)
CONFIRMED_ACTION = re.compile(r"^(?:remember to\s+)?(?:use|give|explain|show|prefer)\b", re.I)
OWNED_PREAMBLE = re.compile(
    r"(?:(?:actually|from now on|remember(?: that)?|please remember)[,:]?\s*)+", re.I
)
EXPLICIT_ERASURE = re.compile(
    r"^(?:please\s+)?(?:forget|delete|erase|remove)\s+(?:my|that|saved)\b", re.I
)
INDEPENDENT = re.compile(
    r"^(?:please\s+)?(?:explain|show|tell|describe|compare|calculate|give|what|why|how|can|could|would|when (?:does|do|is|are))\b",
    re.I,
)
LEADING_SCOPE = re.compile(
    r"^(?:(?:actually|from now on|remember(?: that)?|please remember)[,:]?\s+)*"
    r"(?:for|in|about|when (?:studying|learning|discussing))\s+"
    r"(?P<scope>[a-z0-9]+(?:[ -][a-z0-9]+){0,5}?)"
    r"(?:\s+questions?)?\s*,\s*(?P<preference>.+)$",
    re.I,
)
COMPOUND_PREFERENCE = re.compile(r"\b(?:and|or|but|if|provided|either|both)\b", re.I)
ATTACHED = re.compile(
    r"^(?:only\s+)?(?:for|in|about|when|during|unless|except|outside|and|or|but|if|provided)\b|^(?:i mean|that applies|only then|rather than|such as)\b",
    re.I,
)


def freeze_policy():
    return {
        "version": POLICY_VERSION,
        "selector_version": SELECTOR_VERSION,
        "enabled": False,
        "source_policy": "owned_unique_preference_clause_v2",
        "rule_scope_version": "quoted_leading_or_trailing_condition_phrase_v2",
        "topic_policy": rules.TOPIC_VERSION,
        "max_source_bytes": MAX_SOURCE_BYTES,
        "max_correction_revisions": MAX_CORRECTION_REVISIONS,
        "writer_version": "typed_memory_v5",
        "unknown_condition": "require_confirmation",
    }


def validate_policy(value):
    expected = freeze_policy()
    if value is None:
        return expected
    if not isinstance(value, dict) or value != expected:
        raise ValueError("Memory condition policy identity changed")
    return expected


def condition(quote, source, *, confirmed=False, erasure=False, confirmed_scope=None):
    """Return an attributable finite topic condition or a confirmation reason."""
    if not isinstance(source, str) or len(source.encode("utf-8")) > MAX_SOURCE_BYTES:
        return None, "memory_source_unavailable", None
    if not isinstance(quote, str) or not quote.strip():
        return None, "memory_source_quote_invalid", None
    matches = list(re.finditer(re.escape(quote), source))
    if len(matches) != 1:
        return None, "memory_source_quote_ambiguous", None
    match = matches[0]
    span = [match.start(), match.end()]
    if match.start() and source[match.start() - 1] not in " \t\r\n.!?;":
        return None, "memory_source_clause_unattributed", span
    clause_start = max(source.rfind(mark, 0, match.start()) for mark in ".!?;\n") + 1
    preamble = source[clause_start : match.start()].strip()
    if preamble and not OWNED_PREAMBLE.fullmatch(preamble):
        return None, "memory_source_clause_unattributed", span
    leading = LEADING_SCOPE.fullmatch(quote.strip())
    attributed = quote if leading is None else leading.group("preference")
    if not (
        ATTRIBUTABLE.search(attributed)
        or (confirmed and CONFIRMED_ACTION.search(attributed))
        or (erasure and EXPLICIT_ERASURE.search(quote) and rules.DELETE.search(quote))
    ) or any(c in quote for c in ('"', "\u201c", "\u201d")):
        return None, "memory_source_clause_unattributed", span
    following = source[match.end() :].lstrip()
    if re.search(r"\b[ei]\.$", quote, re.I) and re.match(r"[ge]\.", following, re.I):
        return None, "memory_source_clause_truncated", span
    if (
        following
        and ATTACHED.search(following)
        and not (
            INDEPENDENT.search(following) or rules.TEMPORARY.search(following.split(".", 1)[0])
        )
    ):
        return None, "memory_scope_requires_confirmation", span
    if EXAMPLE.search(quote) or COMPLEX.search(quote):
        return None, "memory_scope_requires_confirmation", span
    if leading is not None:
        remainder = source[match.end() :]
        if (
            remainder.strip()
            and not quote.rstrip().endswith((".", "!", "?", ";"))
            and remainder[0] not in ".!?;\n"
        ):
            return None, "memory_source_clause_truncated", span
        scope = rules.scope_name(leading.group("scope"))
        if (
            scope not in KNOWN_SCOPES
            or CUES.search(attributed)
            or COMPOUND_PREFERENCE.search(attributed)
            or re.search(r"[.!?;\n].*\S", attributed)
        ):
            return None, "memory_scope_requires_confirmation", span
        return scope, "exact_leading_topic_condition", span
    if not CUES.search(quote):
        return "global", "exact_unconditional_preference", span
    scopes = list(SCOPE.finditer(quote))
    if len(scopes) != 1:
        return None, "memory_scope_requires_confirmation", span
    scope = rules.scope_name(scopes[0].group(1))
    if scope in GLOBAL_TERMS:
        return "global", "explicit_universal_scope", span
    if scope not in KNOWN_SCOPES:
        if (
            confirmed
            and confirmed_scope == scope
            and re.fullmatch(r"[a-z0-9]+(?: [a-z0-9]+)*", scope)
            and not re.search(
                r"\b(?:and|or|not|but|if|except|unless|for|in|about|when|during|outside|only|rather|provided)\b",
                scope,
            )
        ):
            return scope, "exact_confirmed_literal_scope", span
        return None, "memory_scope_requires_confirmation", span
    return scope, "exact_topic_condition", span


def correction_source(entry, owner_id, revisions, events, canonical_key):
    """Validate authored UI revisions and controls without inventing chat excerpts."""
    provenance = entry.get("provenance") or {}
    if (
        entry.get("status") != "active"
        or provenance.get("kind") != "user_correction"
        or provenance.get("recorded_by") != owner_id
        or entry.get("verification") != "user_corrected"
        or rules.FIELDS.get(entry.get("field_key")) != entry.get("category")
        or canonical_key != rules.canonical(entry["category"], entry["field_key"], entry["scope"])
        or not isinstance(entry.get("content"), str)
        or len(entry["content"].encode("utf-8")) > MAX_SOURCE_BYTES
        or not 1 <= len(revisions) <= MAX_CORRECTION_REVISIONS
    ):
        return None
    expected_version = entry["version"]
    previous_sequence = None
    for revision in revisions:
        detail = revision.get("details") or {}
        sequence = detail.get("source_event_sequence")
        event = events.get(sequence)
        action = revision.get("action")
        operation = "UPDATE" if action == "user_correction" else "CONTROLS"
        if (
            revision.get("entry_id") != entry["id"]
            or revision.get("entry_version") != expected_version
            or revision.get("content") != entry["content"]
            or revision.get("source_message_id") != entry.get("source_message_id")
            or action not in {"user_correction", "applicability_controls"}
            or not isinstance(sequence, int)
            or not event
            or event.get("owner_id") != owner_id
            or event.get("status") != "applied"
            or event.get("sequence") != sequence
            or event.get("operations")
            != [
                {
                    "operation": operation,
                    "memory_id": entry["id"],
                    "version": expected_version,
                    **({"reason": "user_correction"} if operation == "UPDATE" else {}),
                }
            ]
            or (previous_sequence is not None and sequence >= previous_sequence)
            or (
                expected_version == entry["version"]
                and sequence != entry.get("source_event_sequence")
            )
        ):
            return None
        if action == "user_correction":
            if (
                event.get("id") != provenance.get("event_id")
                or detail.get("scope") != entry["scope"]
                or detail.get("verification") != "user_corrected"
                or provenance.get("previous_source_message_id") != entry.get("source_message_id")
                or revision is not revisions[-1]
            ):
                return None
            return {
                "owned": True,
                "memory_id": entry["id"],
                "memory_version": entry["version"],
                "source_message_id": entry.get("source_message_id"),
                "source_hash": rules.digest(entry["content"]),
                "content": entry["content"],
                "source_kind": "user_correction",
                "recorded_by": owner_id,
                "revision_id": revision["id"],
                "revision_version": expected_version,
                "revision_event_id": event["id"],
                "verified_scope": entry["scope"],
            }
        if detail.get("status") != "active" and expected_version == entry["version"]:
            return None
        previous_sequence = sequence
        expected_version -= 1
    return None


def _source(entry, reader):
    try:
        source = reader(entry) if reader else None
    except Exception:
        return None, "conditional_source_unavailable"
    if not isinstance(source, dict) or source.get("owned") is not True:
        return None, "conditional_source_unavailable"
    content = source.get("content")
    if not isinstance(content, str) or len(content.encode("utf-8")) > MAX_SOURCE_BYTES:
        return None, "conditional_source_invalid"
    quote = (entry.get("provenance") or {}).get("source_quote") or entry.get("content")
    provenance = entry.get("provenance") or {}
    corrected = provenance.get("kind") == "user_correction"
    if (
        source.get("memory_id") != entry["id"]
        or source.get("memory_version") != entry["version"]
        or source.get("source_message_id") != entry.get("source_message_id")
        or not quote
        or quote not in content
        or source.get("source_hash") != rules.digest(content)
        or (not corrected and provenance.get("source_hash") != source["source_hash"])
        or (
            corrected
            and (
                source.get("source_kind") != "user_correction"
                or entry.get("verification") != "user_corrected"
                or source.get("recorded_by") != provenance.get("recorded_by")
                or not source.get("revision_id")
                or source.get("revision_event_id") != provenance.get("event_id")
                or not isinstance(source.get("revision_version"), int)
                or not 1 <= source["revision_version"] <= entry["version"]
                or source.get("verified_scope") != entry["scope"]
                or content != entry["content"]
            )
        )
    ):
        return None, "conditional_source_invalid"
    return source, None


@dataclass
class Selection:
    state: dict
    trace: dict


def select(
    entries,
    question,
    profile=None,
    context=None,
    *,
    policy=None,
    source_reader=None,
    current_message_id=None,
    counter=None,
):
    policy = validate_policy(policy)
    start = time.perf_counter()
    prepared = deepcopy(entries)
    decisions, blocked = [], {}
    now = datetime.now(timezone.utc)
    for entry in prepared:
        if entry.get("status", "active") != "active" or entry.get("category") != "preference":
            continue
        if entry.get("expires_at"):
            try:
                expiry = datetime.fromisoformat(entry["expires_at"].replace("Z", "+00:00"))
                expiry = expiry if expiry.tzinfo else expiry.replace(tzinfo=timezone.utc)
                if expiry <= now:
                    blocked[entry["id"]] = "memory_expired"
                    continue
            except (TypeError, ValueError):
                blocked[entry["id"]] = "memory_expiry_invalid"
                continue
        source, reason = _source(entry, source_reader)
        stored_scope = entry["scope"]
        if source is None:
            blocked[entry["id"]] = reason
            decisions.append({"id": entry["id"], "stored_scope": stored_scope, "reason": reason})
            continue
        quote = (entry.get("provenance") or {}).get("source_quote") or entry["content"]
        corrected = source.get("source_kind") == "user_correction"
        explicit_confirmed = corrected or (
            source.get("source_kind") == "user_confirmed_statement"
            and (entry.get("provenance") or {}).get("kind") == "user_confirmed_statement"
            and source.get("recorded_by") == (entry.get("provenance") or {}).get("recorded_by")
        )
        confirmed = explicit_confirmed or (
            entry.get("writer_version") == "typed_memory_v5"
            and (entry.get("provenance") or {}).get("writer_version") == "typed_memory_v5"
            and CONFIRMED_ACTION.search(quote)
            and rules.DURABLE.search(quote)
        )
        scope, reason, span = condition(
            quote,
            source["content"],
            confirmed=confirmed,
            confirmed_scope=entry["scope"] if explicit_confirmed else None,
        )
        if (
            explicit_confirmed
            and scope not in {None, "global", entry["scope"]}
            and entry["scope"] != "global"
        ):
            scope, reason = None, "memory_scope_requires_confirmation"
        if corrected and scope is not None:
            if scope != "global" and scope != entry["scope"]:
                scope, reason = None, "memory_scope_requires_confirmation"
            else:
                scope, reason = entry["scope"], "exact_user_corrected_scope"
        decisions.append(
            {
                "id": entry["id"],
                "stored_scope": stored_scope,
                "effective_scope": scope,
                "reason": reason,
                "source_quote_range": span,
                "source_hash": source["source_hash"],
            }
        )
        if scope is None:
            blocked[entry["id"]] = reason
        elif scope != "global":
            entry["scope"] = scope
            entry["scope_topics"] = rules.topics(scope)
    prepared = legacy._rules_only_candidates(prepared, question, context)
    for entry in prepared:
        if entry["id"] in blocked:
            entry["_v3_relevance"] = False
            entry["_v3_reason"] = blocked[entry["id"]]
    state = legacy._assemble_state(
        prepared,
        question,
        profile,
        context,
        current_message_id=current_message_id,
        counter=counter,
    )
    state["version"] = SELECTOR_VERSION
    return Selection(
        state,
        {
            "version": policy["version"],
            "policy_hash": rules.digest(policy),
            "status": "owned_condition_rules_only",
            "candidates": [],
            "source_rereads": decisions,
            "selected_ids": [entry["id"] for entry in state["entries"]],
            "elapsed_ms": (time.perf_counter() - start) * 1000,
        },
    )
