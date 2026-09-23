"""Versioned interactive relevance screening, separate from formal E0/E1."""

import math
from conversation.understanding import ALIASES, missing_explicit_terms, term_pattern

MODEL = "cross-encoder/ms-marco-MiniLM-L6-v2"
REVISION = "233902d25c440f23af6f7d6e94d2946bac0bee0a"
VERSION = "interactive_relevance_v1"
SELECTION_VERSION = "interactive_evidence_union_v1"
FACET_VERSION = "interactive_facet_fallback_v1"


def freeze_facet_fallback(retrieval_policy):
    relevance = freeze_policy(retrieval_policy)
    if not retrieval_policy or relevance["minimum_logit"] is None:
        return None
    return {
        "version": FACET_VERSION,
        "understanding_version": "question_understanding_v2",
        "trigger": "whole_query_zero_accepted",
        "max_facets": 2,
        "candidate_slots": min(20, retrieval_policy["candidate_count"]),
        "final_candidate_limit": 20,
        "reranker_model": relevance["reranker_model"],
        "reranker_revision": relevance["reranker_revision"],
        "ordering": "facet_round_robin_no_cross_query_score_comparison",
    }


def facet_fallback(
    understanding,
    whole_rows,
    whole_accepted,
    policy,
    retrieval_policy,
    relevance_policy,
    *,
    retrieve_facet,
    rerank_facet,
    checkpoint,
):
    """Bounded local query expansion; callbacks retain the frozen release/device.

    The original screen is separate: at most 20 additional candidate slots are
    scored across two explicit facets. Duplicate appearances still consume a
    scoring slot; final candidate and accepted counts use unique chunk IDs.
    This never changes the learner question or asserts semantic support.
    """
    expected = freeze_facet_fallback(retrieval_policy)
    if policy is not None and policy != expected:
        raise ValueError("Unsupported frozen facet fallback policy")
    trace = {
        "policy": policy,
        "policy_version": policy["version"] if policy else None,
        "triggered": False,
        "reason": "policy_unavailable",
        "whole_query_candidate_count": len(whole_rows),
        "whole_query_accepted_count": len(whole_accepted),
        "attempted_facets": [],
        "accepted_chunk_ids": [row["chunk_id"] for row in whole_accepted],
        "scope": "bounded facet relevance; original whole-query screen is additional work; no entailment guarantee",
    }

    def final(rows, accepted, source):
        return (
            accepted,
            trace,
            {
                "candidate_count": len({row["chunk_id"] for row in rows}),
                "accepted_count": len({row["chunk_id"] for row in accepted}),
                "candidate_chunk_ids": list(dict.fromkeys(row["chunk_id"] for row in rows)),
                "accepted_chunk_ids": list(dict.fromkeys(row["chunk_id"] for row in accepted)),
                "source": source,
            },
        )

    if whole_accepted:
        trace["reason"] = "whole_query_accepted"
        return final(whole_rows, whole_accepted, "whole_query")
    if not policy or relevance_policy != freeze_policy(retrieval_policy):
        return final(whole_rows, whole_accepted, "whole_query")
    if (
        not understanding
        or understanding.get("version") != policy["understanding_version"]
        or understanding.get("facet_origin") != "explicit_clauses"
        or understanding.get("explicit_clause_count", 0) < 2
    ):
        trace["reason"] = "insufficient_explicit_facets"
        return final(whole_rows, whole_accepted, "whole_query")
    generic = set(
        "one another process concept thing something anything everything explanation question answer topic conditions limits limit happen happens happening".split()
    )
    facets = [
        part
        for part in understanding.get("requested_facets", [])
        if isinstance(part, dict)
        and part.get("request")
        and any(
            isinstance(term, str) and term.isalpha() and term.casefold() not in generic
            for term in part.get("terms", [])
        )
    ]
    if len(facets) < 2:
        trace["reason"] = "no_meaningful_facets"
        return final(whole_rows, whole_accepted, "whole_query")
    selected = facets[: min(policy["max_facets"], policy["candidate_slots"])]
    trace.update(triggered=True, reason="fallback_started")
    candidate_by_id, groups = {}, []
    slots_left = policy["candidate_slots"]
    for index, facet in enumerate(selected):
        limit = slots_left // (len(selected) - index)
        checkpoint("retrieving", trace)
        rows = retrieve_facet(facet["request"], limit)
        if len(rows) > limit or len({row["chunk_id"] for row in rows}) != len(rows):
            raise ValueError("Facet retrieval exceeded its frozen candidate allocation")
        slots_left -= len(rows)
        attempt = {
            "facet_id": facet["id"],
            "query": facet["request"],
            "candidate_limit": limit,
            "candidate_count": len(rows),
            "candidate_chunk_ids": [row["chunk_id"] for row in rows],
            "accepted_count": 0,
            "accepted_chunk_ids": [],
            "excluded": [],
            "model": policy["reranker_model"],
            "revision": policy["reranker_revision"],
        }
        trace["attempted_facets"].append(attempt)
        checkpoint("reranking", trace)
        ranked = rerank_facet(facet["request"], rows)
        if len(ranked) != len(rows) or {row["chunk_id"] for row in ranked} != {
            row["chunk_id"] for row in rows
        }:
            raise ValueError("Facet reranking changed candidate membership")
        accepted, screened = screen(facet["request"], ranked, relevance_policy)
        attempt.update(
            accepted_count=len(accepted),
            accepted_chunk_ids=screened["accepted_chunk_ids"],
            excluded=screened["excluded"],
        )
        for row in ranked:
            previous = candidate_by_id.get(row["chunk_id"])
            if previous and any(
                previous.get(key) != row.get(key)
                for key in ("text", "text_hash", "asset_id", "processing_id")
            ):
                raise ValueError("Facet retrieval changed immutable source identity")
            candidate_by_id.setdefault(row["chunk_id"], row)
        groups.append(accepted)
    admitted, seen = [], set()
    for index in range(max(map(len, groups), default=0)):
        for group in groups:
            if index < len(group) and group[index]["chunk_id"] not in seen:
                admitted.append(group[index])
                seen.add(group[index]["chunk_id"])
    admitted = admitted[: policy["final_candidate_limit"]]
    trace.update(
        reason="fallback_completed",
        accepted_chunk_ids=[row["chunk_id"] for row in admitted],
        candidate_slots_used=sum(row["candidate_count"] for row in trace["attempted_facets"]),
    )
    checkpoint("completed", trace)
    return final(list(candidate_by_id.values()), admitted, "facet_fallback")


def freeze_selection(retrieval_policy):
    return {
        "version": SELECTION_VERSION,
        "candidate_limit": retrieval_policy["candidate_count"] if retrieval_policy else 20,
        "inherited_limit": 5,
        "membership": "frozen_release_current_visibility_exact_text",
        "ordering": "fresh_and_inherited_interleaved_then_current_query_rerank",
        "scoring": "cross_encoder" if retrieval_policy else "bm25",
    }


def merge_candidates(fresh, inherited, policy):
    """Reserve complementary prior candidates within the same finite rerank cap.

    Rank scores from an earlier question are never compared to current scores.
    Fresh metadata wins duplicates, retaining attributable inheritance. The caller
    validates current release membership before passing inherited candidates.
    """
    limit = policy.get("candidate_limit")
    expected = freeze_selection(
        {"candidate_count": limit} if policy.get("scoring") == "cross_encoder" else None
    )
    if type(limit) is not int or not 1 <= limit <= 20 or policy != expected:
        raise ValueError("Unsupported frozen evidence selection policy")
    prior = {row["chunk_id"]: row for row in inherited}
    fresh_by_id = {row["chunk_id"]: row for row in fresh}
    ordered = []
    for index in range(max(len(fresh), min(len(inherited), policy["inherited_limit"]))):
        if index < len(fresh):
            row = dict(fresh[index])
            if row["chunk_id"] in prior:
                row["inherited_from"] = prior[row["chunk_id"]].get("inherited_from")
            ordered.append(row)
        if index < min(len(inherited), policy["inherited_limit"]):
            row = inherited[index]
            if row["chunk_id"] not in fresh_by_id:
                ordered.append(dict(row))
    unique, seen, excluded = [], set(), []
    for row in ordered:
        if row["chunk_id"] in seen:
            continue
        seen.add(row["chunk_id"])
        if len(unique) < limit:
            unique.append(row)
        else:
            excluded.append({"chunk_id": row["chunk_id"], "reason": "candidate_limit"})
    for row in inherited[policy["inherited_limit"] :]:
        if row["chunk_id"] not in seen:
            excluded.append({"chunk_id": row["chunk_id"], "reason": "inherited_limit"})
    return unique, {
        "policy": policy,
        "fresh_count": len(fresh),
        "eligible_inherited_count": len(inherited),
        "merged_chunk_ids": [row["chunk_id"] for row in unique],
        "inherited_chunk_ids": [row["chunk_id"] for row in unique if row.get("inherited_from")],
        "excluded": excluded,
        "scope": "bounded candidate admission; all admitted rows need current-question scoring",
    }


def freeze_policy(retrieval_policy):
    calibrated = bool(
        retrieval_policy
        and retrieval_policy["reranker_model"] == MODEL
        and retrieval_policy["reranker_revision"] == REVISION
    )
    return {
        "version": VERSION,
        "exact_expanded_terms": True,
        "minimum_logit": -4.0 if calibrated else None,
        "reranker_model": MODEL if calibrated else None,
        "reranker_revision": REVISION if calibrated else None,
        "calibration": "20260916-openstax-development-provisional" if calibrated else None,
        "fallback": "strict_grounded",
    }


def screen(query, rows, policy):
    if policy != freeze_policy(
        {
            "reranker_model": policy.get("reranker_model"),
            "reranker_revision": policy.get("reranker_revision"),
        }
    ):
        raise ValueError("Unsupported frozen relevance policy")
    accepted, excluded = [], []
    for row in rows:
        reason = None
        missing = missing_explicit_terms(query, row.get("text", "") + " " + row.get("section", ""))
        required = [
            name for name, expansion in ALIASES.items() if term_pattern(expansion).search(query)
        ]
        # A multi-concept question can require complementary passages. A chunk
        # need only cover one explicit concept; generation still checks coverage.
        if required and len(missing) == len(required):
            reason = "expanded_concept_absent"
        threshold = policy["minimum_logit"]
        if threshold is not None:
            if (
                row.get("score_type") != "cross_encoder"
                or row.get("reranker_model") != MODEL
                or row.get("reranker_revision") != REVISION
            ):
                raise ValueError("Relevance threshold requires its pinned learned reranker")
            if not math.isfinite(row["score"]):
                raise ValueError("Nonfinite relevance score")
            if row["score"] < threshold:
                reason = reason or "below_relevance_threshold"
        if reason:
            excluded.append(
                {
                    "chunk_id": row["chunk_id"],
                    "reason": reason,
                    "missing_terms": missing,
                    "score": row.get("score"),
                }
            )
        else:
            accepted.append(row)
    return accepted, {
        "policy": policy,
        "candidate_count": len(rows),
        "accepted_count": len(accepted),
        "accepted_chunk_ids": [row["chunk_id"] for row in accepted],
        "excluded": excluded,
        "scope": "topic relevance screening; raw logits are not probabilities or claim entailment",
    }
