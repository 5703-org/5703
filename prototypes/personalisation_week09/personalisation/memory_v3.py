"""Opt-in, pinned local semantic supplementation of typed memory selection.

The v2 engine remains executable unchanged. Semantic scores only resolve topic
scope; they never establish truth, mastery, ownership or an instruction's priority.
"""

import copy
import json
import math
import re
import time
from dataclasses import dataclass
from typing import Any

from . import memory_v2 as rules

SELECTOR_VERSION = "query_conditioned_memory_v3"
POLICY_VERSION = "local_scope_supplement_v2"
LEGACY_POLICY_VERSION = "local_scope_supplement_v1"
RULE_SCOPE_VERSION = "specific_scope_phrase_with_anaphora_v2"
REVISION = "ffb93f3bd4047442299a41ebb6fa998a38507c52"
EMBEDDING: dict[str, Any] = {
    "embedding_provider": "e5",
    "embedding_model": "intfloat/e5-small-v2",
    "embedding_revision": REVISION,
    "tokenizer_revision": REVISION,
    "embedding_device": "cpu",
    "embedding_preprocessing_revision": "prefix_v1",
    "dimension": 384,
    "embedding_cache_folder": "artifacts/huggingface",
}
MAX_SCOPES = 24
BROAD_SCOPES = {
    "biology",
    "chemistry",
    "anatomy",
    "physiology",
    "genetics",
    "acid base",
    "cellular energy",
}
ANAPHORA = re.compile(r"\b(?:it|that|this|more|again)\b", re.I)


def freeze_policy(*, enabled=False, threshold=None, calibration_id=None):
    """No empirical threshold or semantic activation is silently assumed."""
    if type(enabled) is not bool:
        raise ValueError("Memory semantic enabled must be a boolean")
    if enabled and (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not math.isfinite(threshold)
        or not 0 <= threshold <= 1
        or not isinstance(calibration_id, str)
        or not re.fullmatch(r"[a-f0-9]{64}", calibration_id)
    ):
        raise ValueError("An explicit threshold and frozen calibration SHA256 are required")
    return {
        "version": POLICY_VERSION,
        "enabled": enabled,
        "threshold": float(threshold) if enabled else None,
        "calibration_id": calibration_id if enabled else None,
        "embedding": dict(EMBEDDING),
        "max_scopes": MAX_SCOPES,
        "source_policy": "owned_exact_quote_conditional_scope_v1",
        "rule_scope_version": RULE_SCOPE_VERSION,
    }


def validate_policy(value):
    if value is None:
        return freeze_policy()
    if not isinstance(value, dict):
        raise ValueError("Memory semantic policy must be an object")
    expected = freeze_policy(
        enabled=value.get("enabled"),
        threshold=value.get("threshold"),
        calibration_id=value.get("calibration_id"),
    )
    if value.get("version") == LEGACY_POLICY_VERSION:
        expected["version"] = LEGACY_POLICY_VERSION
        expected.pop("rule_scope_version")
    if value != expected:
        raise ValueError("Memory semantic policy identity changed")
    return expected


def _rules_only_candidates(entries, question, context):
    """Apply a specific saved scope only when the actual concept is named.

    A discipline-level preference still covers the discipline. A short
    anaphoric follow-up can use the latest owned user topic, while an explicit
    new topic in the current message is never replaced by older conversation.
    """
    query_words = rules.words(question)
    if not rules.topics(question) and len(query_words) <= 10 and ANAPHORA.search(question):
        messages = (context or {}).get("recent_messages", (context or {}).get("messages", []))
        recent = next(
            (
                message.get("content", "")
                for message in reversed(messages[-6:])
                if message.get("role") == "user"
            ),
            "",
        )
        query_words |= rules.words(recent)
    prepared = copy.deepcopy(entries)
    for entry in prepared:
        scope = rules.scope_name(entry["scope"])
        if scope == "global" or scope in BROAD_SCOPES:
            continue
        phrase_match = rules.words(scope) <= query_words
        entry["_v3_relevance"] = phrase_match
        if not phrase_match:
            entry["_v3_reason"] = "specific_scope_not_named"
    return prepared


def scope_scores(question, scopes):
    """Real normalized CPU E5 query/passage vectors; model instance cache only."""
    from huggingface_hub import snapshot_download
    from retrieval.embedding import make_embedding

    snapshot_download(
        EMBEDDING["embedding_model"],
        revision=REVISION,
        cache_dir=EMBEDDING["embedding_cache_folder"],
        local_files_only=True,
    )
    model = make_embedding(EMBEDDING, runtime_device="cpu")
    query = model.encode([question], kind="query")[0]
    passages = model.encode(scopes, kind="passage")
    return [sum(q * p for q, p in zip(query, vector, strict=True)) for vector in passages]


CONDITIONAL = re.compile(r"\b(?:for|when|unless|except|only if|outside)\b", re.I)
COMPLEX_CONDITION = re.compile(r"\b(?:unless|except|only if|not when|but not|outside)\b", re.I)
SCOPE = re.compile(
    r"\b(?:for|when (?:studying|learning|discussing))\s+"
    r"([a-z][a-z0-9 /&-]{1,100}?)(?=\s*,|\s*[.!?;]|\s+I\b|$)",
    re.I,
)


def conditional_scope(entry, source_reader):
    """Reread the owned source, retaining simple explicit topic conditions only."""
    quote = (entry.get("provenance") or {}).get("source_quote") or entry.get("content") or ""
    if not CONDITIONAL.search(quote):
        return entry["scope"], None
    if source_reader is None:
        return None, "conditional_source_unavailable"
    try:
        source = source_reader(entry)
    except Exception:
        return None, "conditional_source_unavailable"
    if (
        not source
        or source.get("owned") is not True
        or source.get("memory_id") != entry["id"]
        or source.get("memory_version") != entry["version"]
        or source.get("source_message_id") != entry.get("source_message_id")
        or not quote
        or quote not in source.get("content", "")
        or source.get("source_hash") != rules.digest(source.get("content", ""))
    ):
        return None, "conditional_source_invalid"
    saved_hash = (entry.get("provenance") or {}).get("source_hash")
    if saved_hash and saved_hash != source["source_hash"]:
        return None, "conditional_source_changed"
    if COMPLEX_CONDITION.search(quote):
        return None, "conditional_scope_requires_clarification"
    matches = SCOPE.findall(quote)
    if len(matches) != 1:
        return None, "conditional_scope_requires_clarification"
    scope = rules.scope_name(matches[0])
    if scope in {"example", "examples", "me", "my studies", "learning"}:
        return None, "conditional_scope_requires_clarification"
    return scope, "owned_source_reread"


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
    scorer=None,
    current_message_id=None,
    counter=None,
):
    policy = validate_policy(policy)
    started = time.perf_counter()
    trace = {
        "version": policy["version"],
        "policy_hash": rules.digest(policy),
        "calibration_id": policy["calibration_id"],
        "status": "disabled_rules_only",
        "device": "cpu" if policy["enabled"] else None,
        "embedding_revision": REVISION,
        "candidates": [],
        "source_rereads": [],
        "fallback_reason": None,
    }
    if not policy["enabled"]:
        if policy["version"] == LEGACY_POLICY_VERSION:
            state = rules.learner_state(
                entries,
                question,
                profile,
                context,
                current_message_id=current_message_id,
                counter=counter,
            )
        else:
            state = _assemble_state(
                _rules_only_candidates(entries, question, context),
                question,
                profile,
                context,
                current_message_id=current_message_id,
                counter=counter,
            )
        state["version"] = SELECTOR_VERSION
        trace["rule_scope_version"] = policy.get("rule_scope_version")
        trace["selected_ids"] = [x["id"] for x in state["entries"]]
        trace["elapsed_ms"] = (time.perf_counter() - started) * 1000
        return Selection(state, trace)
    prepared: list[dict] = []
    unresolved: list[dict] = []
    wanted = set(rules.query_topics(question, context))
    current_fields = {
        item["field_key"] for item in rules.deterministic_operations(question, current_turn=True)
    }
    for original in entries:
        entry = copy.deepcopy(original)
        # Field/verification/override checks precede any optional model computation.
        eligible = (
            entry.get("status", "active") == "active"
            and entry.get("field_key")
            and entry["field_key"] not in current_fields
            and entry["category"] != "confirmed_observation"
            and entry.get("verification")
            not in {"unsupported", "recorded_unconfirmed", "legacy_unverified"}
        )
        if eligible:
            scope, reason = conditional_scope(entry, source_reader)
            if reason:
                trace["source_rereads"].append({"id": entry["id"], "reason": reason})
            if scope is None:
                entry["_v3_relevance"] = False
                entry["_v3_reason"] = reason
                prepared.append(entry)
                continue
            entry["scope"] = scope
            if reason == "owned_source_reread":
                entry["scope_topics"] = rules.topics(scope)
            relevant = (
                scope == "global"
                or bool(set(entry.get("scope_topics") or rules.topics(scope)) & wanted)
                or bool(rules.words(scope) & rules.words(question))
            )
            if not relevant:
                if entry.get("match_policy") == "rules_only":
                    entry["_v3_relevance"] = False
                    entry["_v3_reason"] = "semantic_match_declined"
                elif len(unresolved) < policy["max_scopes"]:
                    unresolved.append(entry)
                else:
                    entry["_v3_relevance"] = False
                    entry["_v3_reason"] = "semantic_candidate_budget"
        prepared.append(entry)
    trace["status"] = "rules_sufficient"
    if unresolved:
        try:
            # Short anaphoric turns retain the nearest owned user topic verbatim.
            semantic_question = question
            if not rules.topics(question) and re.search(
                r"\b(?:it|that|this|more|again)\b", question, re.I
            ):
                messages = (context or {}).get(
                    "recent_messages", (context or {}).get("messages", [])
                )
                recent = next(
                    (
                        m.get("content", "")
                        for m in reversed(messages[-6:])
                        if m.get("role") == "user"
                    ),
                    "",
                )
                semantic_question = recent + " " + question
            scores = (scorer or scope_scores)(semantic_question, [x["scope"] for x in unresolved])
            if len(scores) != len(unresolved) or any(
                not math.isfinite(x) or not -1 <= x <= 1 for x in scores
            ):
                raise ValueError("Invalid semantic scope scores")
            for entry, score in zip(unresolved, scores, strict=True):
                selected = score >= policy["threshold"]
                entry["_v3_relevance"] = selected
                entry["_v3_reason"] = "semantic_scope_below_threshold"
                trace["candidates"].append(
                    {"id": entry["id"], "score": score, "accepted": selected}
                )
            trace["status"] = "semantic_supplement"
        except Exception as exc:
            # No guessed vectors and no silent semantic activation after a failure.
            trace["status"] = "semantic_unavailable_rules_fallback"
            trace["fallback_reason"] = type(exc).__name__
    state = _assemble_state(
        prepared, question, profile, context, current_message_id=current_message_id, counter=counter
    )
    trace["selected_ids"] = [x["id"] for x in state["entries"]]
    trace["elapsed_ms"] = (time.perf_counter() - started) * 1000
    return Selection(state, trace)


# Keep the old selector executable: this version independently pins its chooser.
from .memory_v2 import (
    query_topics,
    words,
    deterministic_operations,
    scope_name,
    topics,
    digest,
    TOPIC_VERSION,
    WRITER_VERSION,
    MEMORY_TOKEN_LIMIT,
    MemoryPreparationUnavailable,
)


def _assemble_state(
    entries,
    question,
    profile=None,
    context=None,
    *,
    conditioned=True,
    current_message_id=None,
    character_limit=4800,
    counter=None,
):
    """Frozen v2 precedence/budget with explicit v3 relevance decisions."""
    wanted_topics = query_topics(question, context)
    query_words = words(question)
    overlay = list(
        {
            item["field_key"]: item
            for item in deterministic_operations(question, current_turn=True)
        }.values()
    )
    current_fields = {x["field_key"] for x in overlay}
    winners: dict = {}
    excluded: list[dict] = []
    profile_value = (profile or {}).get("profile") or {}
    for entry in entries:
        if entry.get("status", "active") != "active":
            excluded.append({"id": entry["id"], "reason": "memory_inactive"})
            continue
        field = entry.get("field_key")
        if not field:
            # The v1 path remains intact; V2 asks for confirmation before interpreting
            # a free-form historical key as a typed current learner fact.
            excluded.append({"id": entry["id"], "reason": "legacy_requires_confirmation"})
            continue
        scope = scope_name(entry["scope"])
        relevant = (
            scope == "global"
            or bool(set(entry.get("scope_topics") or topics(scope)) & set(wanted_topics))
            or bool(words(scope) & query_words)
        )
        relevant = entry.get("_v3_relevance", relevant)
        if conditioned and not relevant:
            excluded.append(
                {"id": entry["id"], "reason": entry.get("_v3_reason", "scope_not_relevant")}
            )
            continue
        if field in current_fields:
            excluded.append({"id": entry["id"], "reason": "current_instruction"})
            continue
        if entry["category"] == "confirmed_observation" or entry.get("verification") in {
            "unsupported",
            "recorded_unconfirmed",
            "legacy_unverified",
        }:
            excluded.append({"id": entry["id"], "reason": "evidence_unverified"})
            continue
        if scope == "global" and field == "detail_level" and profile_value.get("style"):
            excluded.append({"id": entry["id"], "reason": "saved_profile_default"})
            continue
        # M3 retains the same conflict rules; its candidate view lacks query filtering.
        key = field if relevant else field + ":" + scope
        if entry["category"] == "assessment_performance":
            key = field + ":" + entry["id"]
        priority = (
            1 if scope != "global" else 0,
            entry.get("source_event_sequence") or 0,
            entry.get("version", 0),
            entry["id"],
        )
        if key not in winners or priority > winners[key][0]:
            if key in winners:
                excluded.append({"id": winners[key][1]["id"], "reason": "field_superseded"})
            winners[key] = (priority, entry)
        else:
            excluded.append({"id": entry["id"], "reason": "field_superseded"})
    selected: list[dict] = []
    used = 0
    for _, entry in sorted(winners.values(), key=lambda pair: pair[0], reverse=True):
        size = len(json.dumps(entry, ensure_ascii=False))
        if used + size > character_limit or len(selected) >= 10:
            excluded.append({"id": entry["id"], "reason": "memory_budget"})
            continue
        selected.append(entry)
        used += size
    # Prompt snapshots contain exact selected values and source references, not
    # full assessment rubrics, source messages or revision bodies.
    selected = [
        {
            k: e[k]
            for k in (
                "id",
                "version",
                "category",
                "content",
                "scope",
                "field_key",
                "verification",
                "source_message_id",
                "expires_at",
            )
            if k in e
        }
        for e in selected
    ]
    fields = [
        {
            "field_key": e.get("field_key") or "legacy",
            "scope": e["scope"],
            "verification": e.get("verification", "legacy_unverified"),
            "source": {"memory_id": e["id"], "version": e["version"]},
        }
        for e in selected
    ]
    for operation in overlay:
        fields.append(
            {
                "field_key": operation["field_key"],
                "content": operation["content"],
                "scope": operation["scope"],
                "verification": "current_user_instruction",
                "source": {"message_id": current_message_id},
                "operation": operation["operation"],
            }
        )
    payload = {
        "version": SELECTOR_VERSION if conditioned else WRITER_VERSION,
        "entries": selected,
        "fields": fields,
        "query_topics": wanted_topics,
        "query_hash": digest(question),
        "topic_policy": TOPIC_VERSION,
        "excluded": excluded[:20],
        "excluded_count": len(excluded),
        "saved_profile_defaults": {
            k: profile_value[k] for k in ("level", "style") if k in profile_value
        },
        "precedence": [
            "current_instruction",
            "relevant_scoped_preference",
            "saved_profile_default",
            "global_preference",
            "evidence_gated_observation",
        ],
    }
    count = counter.count if counter is not None else lambda value: len(value.encode("utf-8"))
    payload["token_counting"] = (
        "configured_tokenizer" if counter is not None else "utf8_byte_upper_bound"
    )
    payload["token_limit"] = MEMORY_TOKEN_LIMIT
    # Decisions remain attributable in source events; only a bounded diagnostic
    # sample belongs in the generation context.
    try:
        # Leave room for the snapshot identity and read-time revocation metadata.
        while count(json.dumps(payload, ensure_ascii=False)) > MEMORY_TOKEN_LIMIT - 96:
            if payload["excluded"]:
                payload["excluded"].pop()
            elif payload["entries"]:
                removed = payload["entries"].pop()
                payload["fields"] = [
                    f for f in payload["fields"] if f["source"].get("memory_id") != removed["id"]
                ]
                payload["excluded_count"] += 1
            elif any("content" in field for field in payload["fields"]):
                # The current question is already a first-class model input.
                # Preserve the overriding field/source identity if its duplicate
                # quotation cannot fit this optional context budget.
                for field in payload["fields"]:
                    field.pop("content", None)
            else:
                raise MemoryPreparationUnavailable("MEMORY_CONTEXT_BUDGET_EXCEEDED")
        payload["token_count"] = count(json.dumps(payload, ensure_ascii=False))
    except MemoryPreparationUnavailable:
        raise
    except Exception as exc:
        raise MemoryPreparationUnavailable() from exc
    return payload
