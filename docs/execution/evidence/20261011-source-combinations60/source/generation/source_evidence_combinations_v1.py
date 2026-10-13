"""Bounded source-composition proposals; lexical coverage never proves support."""

from __future__ import annotations

import hashlib
import json

from .source_relations_v2 import scoped_syntactic_units, syntactic_units

VERSION = "source_evidence_combinations_v1"
MAX_NEW_PER_UNIT = 4
MAX_NEW_FRAGMENTS = 12
MAX_NEW_SOURCE_CHARS = 6000
MAX_PROPOSALS = 12
MAX_HINT_ROWS = 64
MAX_OUTPUT_BYTES = 18 * 1024
_COARSE_QUALITIES = {
    "coarse_partial_block", "conservative_whole_block", "conservative_sentence_block",
}
_SOURCE_REF_KEYS = (
    "fragment_id", "evidence_id", "document_version_id", "processing_id", "chunk_id",
    "source_unit_id", "start", "end", "chunk_start", "chunk_end", "page", "text_hash",
    "block_kind", "mapping_quality", "offset_basis",
)


def _result():
    return {
        "version": VERSION,
        "candidate_only": True,
        "source_entailment_certified": False,
        "publication_override": False,
        "candidate_fragment_ids": [],
        "proposals": [],
        "limits": {
            "max_new_per_unit": MAX_NEW_PER_UNIT,
            "max_new_fragments": MAX_NEW_FRAGMENTS,
            "max_new_source_chars": MAX_NEW_SOURCE_CHARS,
            "max_proposals": MAX_PROPOSALS,
            "max_hint_rows_per_proposal": MAX_HINT_ROWS,
            "max_output_utf8_bytes": MAX_OUTPUT_BYTES,
            "new_fragment_count": 0,
            "new_source_chars": 0,
            "omitted_proposal_count": 0,
            "metadata_capacity_blocked": False,
        },
    }


def _blocked(result, reason):
    result["blocked_reason"] = reason
    return result


def _unique(rows, key):
    identities = [row[key] for row in rows]
    if any(not isinstance(identity, str) or not identity for identity in identities):
        raise ValueError("COMPOSITION_IDENTITY_INVALID")
    if len(identities) != len(set(identities)):
        raise ValueError("COMPOSITION_IDENTITY_DUPLICATE")
    return {row[key]: row for row in rows}


def _eligible(fragment):
    return (
        fragment.get("complete_block") is True
        and isinstance(fragment.get("exact_text"), str)
        and bool(fragment["exact_text"])
        and fragment.get("block_kind") != "unresolved_atomic"
        and fragment.get("mapping_quality") not in _COARSE_QUALITIES
        and not str(fragment.get("mapping_quality", "")).startswith("coarse")
    )


def _source_ref(fragment):
    reference = {key: fragment[key] for key in _SOURCE_REF_KEYS if key in fragment}
    reference["text_hash"] = hashlib.sha256(fragment["exact_text"].encode("utf-8")).hexdigest()
    return reference


def _encoded_size(result):
    # The ordinary repair transport uses spaced JSON; compact JSON is smaller.
    return len(json.dumps(
        result, ensure_ascii=False, sort_keys=True,
    ).encode("utf-8"))


def _recount(result, available):
    identities = list(dict.fromkeys(
        identity for proposal in result["proposals"]
        for identity in proposal["supplement_fragment_ids"]
    ))
    result["candidate_fragment_ids"] = identities
    result["limits"]["new_fragment_count"] = len(identities)
    result["limits"]["new_source_chars"] = sum(
        len(available[identity]["exact_text"]) for identity in identities
    )


def _finalize(result, available):
    """Remove entire proposal records instead of cutting source or claim text."""
    _recount(result, available)
    while _encoded_size(result) > MAX_OUTPUT_BYTES and result["proposals"]:
        result["proposals"].pop()
        result["limits"]["omitted_proposal_count"] += 1
        result["limits"]["metadata_capacity_blocked"] = True
        _recount(result, available)
    while _encoded_size(result) > MAX_OUTPUT_BYTES and result.get("excluded_units"):
        result["excluded_units"].pop()
        result["limits"]["omitted_exclusion_record_count"] = (
            result["limits"].get("omitted_exclusion_record_count", 0) + 1
        )
        result["limits"]["metadata_capacity_blocked"] = True
    return result


def _parent(fragment):
    """An original source location permits navigation, not entailment joining."""
    identity = tuple(fragment.get(key) for key in (
        "document_version_id", "processing_id", "source_unit_id",
    ))
    start, end = fragment.get("start"), fragment.get("end")
    if (
        not all(isinstance(value, str) and value for value in identity)
        or type(start) is not int or type(end) is not int or not 0 <= start < end
    ):
        return None
    return (fragment["evidence_id"], *identity)


def _distance(candidate, selected, available):
    parent = _parent(candidate)
    distances = []
    if parent is not None:
        for identity in selected:
            other = available[identity]
            if _parent(other) == parent:
                distances.append(min(
                    abs(candidate["start"] - other["end"]),
                    abs(other["start"] - candidate["end"]),
                ))
    return min(distances) if distances else None


def _validate(claims, bindings, fragments, assessment):
    by_claim = _unique(claims, "claim_id")
    by_binding = _unique(bindings, "claim_id")
    available = _unique(fragments, "fragment_id")
    checked = _unique(assessment["claims"], "claim_id")
    if set(by_claim) != set(by_binding) or not set(checked) <= set(by_claim):
        raise ValueError("COMPOSITION_CLAIM_SCOPE_INVALID")
    for fragment in fragments:
        text = fragment.get("exact_text")
        recorded_hash = fragment.get("text_hash")
        if isinstance(text, str) and recorded_hash is not None and recorded_hash != (
            hashlib.sha256(text.encode("utf-8")).hexdigest()
        ):
            raise ValueError("COMPOSITION_SOURCE_TEXT_HASH_INVALID")
    for claim_id, binding in by_binding.items():
        citations = _unique(binding["citations"], "evidence_id")
        declared = by_claim[claim_id].get("evidence_ids")
        if declared is not None and (
            len(declared) != len(set(declared)) or set(declared) != set(citations)
        ):
            raise ValueError("COMPOSITION_EVIDENCE_SCOPE_INVALID")
        for evidence_id, citation in citations.items():
            identities = citation["allowed_fragment_ids"]
            if len(identities) != len(set(identities)):
                raise ValueError("COMPOSITION_ALLOWED_ID_DUPLICATE")
            for identity in identities:
                fragment = available.get(identity)
                if fragment is None or fragment["evidence_id"] != evidence_id:
                    raise ValueError("COMPOSITION_ALLOWED_SOURCE_INVALID")
    original_units = {row["claim_id"]: row for row in syntactic_units(claims)}
    for claim_id, row in checked.items():
        returned = _unique(row["obligations"], "unit_id")
        expected = _unique(original_units[claim_id]["units"], "unit_id")
        if set(returned) != set(expected):
            raise ValueError("COMPOSITION_UNIT_SCOPE_INVALID")
    return available, checked


def plan_source_combinations(claims, bindings, fragments, assessment):
    """Suggest complete scoped blocks once for already validated negative units.

    The proposal preserves the original negative judgment and lossless partition.
    All original publication checks and the caller's finite repair/recheck budget
    remain required. No proposal certifies semantic absence or predicate ownership.
    """
    result = _result()
    if not isinstance(assessment, dict) or assessment.get("contract_issue_codes") != []:
        return _blocked(result, "source_relation_contract_not_validated")
    try:
        available, checked = _validate(claims, bindings, fragments, assessment)
        negative_claim_ids = {
            claim_id for claim_id, row in checked.items()
            if any(
                unit["status"] != "supported"
                or unit["relation_preserved"] is not True
                or unit["conditions_preserved"] is not True
                for unit in row["obligations"]
            )
        }
        if not negative_claim_ids:
            return result
        scoped = scoped_syntactic_units(
            [row for row in claims if row["claim_id"] in negative_claim_ids],
            [row for row in bindings if row["claim_id"] in negative_claim_ids],
            fragments,
        )
        global_ids = set()
        for entry in scoped:
            assessed = checked.get(entry["claim_id"])
            if assessed is None:
                continue
            original = _unique(entry["units"], "unit_id")
            returned = _unique(assessed["obligations"], "unit_id")
            if set(original) != set(returned):
                raise ValueError("COMPOSITION_UNIT_SCOPE_INVALID")
            allowed_ids = {
                identity
                for citation in entry["actual_citation_scope"]
                for identity in citation["allowed_fragment_ids"]
            }
            eligible = {
                identity for identity in allowed_ids if _eligible(available[identity])
            }
            index = entry["source_context_candidates"]["rows"]
            hits = {
                identity: {
                    number for number, row in enumerate(index)
                    if any(hit[1] == identity for hit in row[3])
                }
                for identity in eligible
            }
            for unit_id, unit in returned.items():
                if (
                    unit["status"] == "supported"
                    and unit["relation_preserved"] is True
                    and unit["conditions_preserved"] is True
                ):
                    continue
                if unit["status"] not in {"supported", "partial", "unsupported"}:
                    raise ValueError("COMPOSITION_UNIT_STATUS_INVALID")
                selected = unit["fragment_ids"]
                if len(selected) != len(set(selected)) or not set(selected) <= allowed_ids:
                    raise ValueError("COMPOSITION_UNIT_SELECTION_INVALID")
                if any(not _eligible(available[identity]) for identity in selected):
                    result["limits"]["excluded_unit_count"] = (
                        result["limits"].get("excluded_unit_count", 0) + 1
                    )
                    exclusions = result.setdefault("excluded_units", [])
                    if len(exclusions) < MAX_PROPOSALS:
                        exclusions.append({
                            "claim_id": entry["claim_id"], "unit_id": unit_id,
                            "reason": "selected_source_not_a_complete_precise_block",
                        })
                    else:
                        result["limits"]["omitted_exclusion_record_count"] = (
                            result["limits"].get("omitted_exclusion_record_count", 0) + 1
                        )
                    continue
                if len(result["proposals"]) >= MAX_PROPOSALS:
                    result["limits"]["omitted_proposal_count"] += 1
                    result["limits"]["proposal_count_blocked"] = True
                    continue
                covered = set().union(*(hits[identity] for identity in selected))
                selected_coverage = sorted(covered)
                candidates = eligible - set(selected)
                unselected_count = len(candidates)
                own_anchors = {
                    number for number, row in enumerate(index)
                    if any(occurrence[0] == unit_id for occurrence in row[2])
                }
                hint_indices = sorted(own_anchors) + sorted(
                    set(range(len(index))) - own_anchors
                )
                hint_indices = hint_indices[:MAX_HINT_ROWS]
                hint_set = set(hint_indices)
                supplement, limit_reasons = [], []
                # Greedy lexical coverage ranks proposals only, never a verdict.
                while candidates and len(supplement) < MAX_NEW_PER_UNIT:
                    ranked = sorted(candidates, key=lambda identity: (
                        -len((hits[identity] - covered) & own_anchors),
                        -len(hits[identity] - covered),
                        _distance(available[identity], selected, available) is None,
                        _distance(available[identity], selected, available) or 0,
                        identity,
                    ))
                    fitting = []
                    for identity in ranked:
                        if not hits[identity] - covered:
                            continue
                        fresh = identity not in global_ids
                        if fresh and len(global_ids) >= MAX_NEW_FRAGMENTS:
                            limit_reasons.append("global_new_fragment_limit")
                            continue
                        added_chars = len(available[identity]["exact_text"]) if fresh else 0
                        if result["limits"]["new_source_chars"] + added_chars > MAX_NEW_SOURCE_CHARS:
                            limit_reasons.append("global_whole_block_character_limit")
                            continue
                        fitting.append(identity)
                    if not fitting:
                        break
                    identity = fitting[0]
                    supplement.append(identity)
                    candidates.remove(identity)
                    covered.update(hits[identity])
                    if identity not in global_ids:
                        global_ids.add(identity)
                        result["candidate_fragment_ids"].append(identity)
                        result["limits"]["new_source_chars"] += len(
                            available[identity]["exact_text"]
                        )
                if len(supplement) == MAX_NEW_PER_UNIT and any(
                    hits[identity] - covered for identity in candidates
                ):
                    limit_reasons.append("per_unit_new_fragment_limit")
                state = (
                    "empty_scoped_candidate_bank" if not eligible else
                    "allowed_unselected_candidates" if unselected_count else
                    "selection_still_insufficient"
                )
                context = original[unit_id]
                result["proposals"].append({
                    "claim_id": entry["claim_id"], "unit_id": unit_id,
                    "candidate_only": True,
                    "source_entailment_certified": False,
                    "publication_override": False,
                    "checker_status": unit["status"],
                    "checker_relation_preserved": unit["relation_preserved"],
                    "checker_conditions_preserved": unit["conditions_preserved"],
                    "selected_fragment_ids": list(selected),
                    "supplement_fragment_ids": supplement,
                    "diagnostic": {
                        "scoped_candidate_state": state,
                        "eligible_scoped_fragment_count": len(eligible),
                        "unselected_scoped_fragment_count": unselected_count,
                        "semantic_absence_certified": False,
                        "predicate_ownership_certified": False,
                        "syntactic_partition_only": True,
                        "same_source_order_is_semantic_continuation": False,
                    },
                    "claim_context_ref": "original_claims:" + entry["claim_id"],
                    "full_claim_hash": hashlib.sha256(
                        entry["full_claim"].encode("utf-8")
                    ).hexdigest(),
                    "full_claim_chars": len(entry["full_claim"]),
                    "unit_context": {key: context[key] for key in (
                        "start", "end", "text_hash",
                    )},
                    "indexed_term_coverage": {
                        "anchor_rows": [index[number][:3] for number in hint_indices],
                        "anchor_row_indices": hint_indices,
                        "anchor_count": len(index),
                        "index_truncated": len(hint_indices) < len(index),
                        "unit_anchor_indices": sorted(own_anchors & hint_set),
                        "selected_anchor_indices": sorted(set(selected_coverage) & hint_set),
                        "combined_anchor_indices": sorted(covered & hint_set),
                        "missing_anchor_indices": sorted(hint_set - covered),
                        "missing_indexed_anchor_count": len(set(range(len(index))) - covered),
                        "source_entailment_certified": False,
                    },
                    "source_refs": [
                        _source_ref(available[identity])
                        for identity in [*selected, *supplement]
                    ],
                    "limit_reasons": sorted(set(limit_reasons)),
                })
        return _finalize(result, available)
    except (KeyError, TypeError, ValueError, AttributeError):
        return _blocked(_result(), "invalid_source_composition_input")
