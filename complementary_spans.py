"""Versioned contiguous context selection; never an entailment judgment."""

from generation.evidence_budget import requested_facets, terms
from .source_spans import text_hash

VERSION = "complementary_context_v2"


def select_context(evidence, fragments, question, understanding=None, source_map=None):
    """Keep complementary complete blocks and nearby qualifications within a chunk.

    A single contiguous substring retains exact existing provenance. It cannot
    increase the input text beyond the already budgeted chunk, reconstruct a
    missing formula, or certify that lexical coverage is semantic coverage.
    Highlight selection remains a separate, subsequently checked operation.
    """
    facets = requested_facets(question, understanding)
    selected, ranges, excluded, decisions = [], {}, [], []
    for item in evidence:
        blocks = sorted(
            (
                f
                for f in fragments
                if f["evidence_id"] == item["evidence_id"] and f["complete_block"]
            ),
            key=lambda f: (f["chunk_start"], f["chunk_end"]),
        )
        if not blocks:
            excluded.append({"chunk_id": item["chunk_id"], "reason": "no_complete_source_block"})
            continue
        anchors = set()
        for facet in facets:
            requested = set(facet["terms"])
            ranked = sorted(
                range(len(blocks)),
                key=lambda i: (-len(requested & terms(blocks[i]["exact_text"])), i),
            )
            if ranked and requested & terms(blocks[ranked[0]]["exact_text"]):
                anchors.add(ranked[0])
        if not anchors:
            anchors.add(0)
        wanted = set().union(*(set(facet["terms"]) for facet in facets))
        covered = set().union(*(terms(blocks[i]["exact_text"]) for i in anchors))
        # A single facet can still request a cause and an outcome. Add a small
        # number of complementary anchors, instead of repeatedly rewarding the
        # definition's shared nouns. This remains a lexical heuristic.
        for _ in range(2):
            remaining = [i for i in range(len(blocks)) if i not in anchors]
            if not remaining:
                break
            best = max(
                remaining,
                key=lambda i: (len((terms(blocks[i]["exact_text"]) & wanted) - covered), -i),
            )
            additions = (terms(blocks[best]["exact_text"]) & wanted) - covered
            if not additions:
                break
            anchors.add(best)
            covered |= terms(blocks[best]["exact_text"])
        indices = set(anchors)
        # Adjacent context is especially material for mechanisms and exceptions;
        # selecting the bounding range avoids deleting connecting qualifications.
        for anchor in sorted(anchors):
            indices.update(range(max(0, anchor - 1), min(len(blocks), anchor + 4)))
        first, last = min(indices), max(indices)
        start, end = blocks[first]["chunk_start"], blocks[last]["chunk_end"]
        # Only recorded provenance may establish an excerpt's original offset.
        first_text = blocks[first]["exact_text"]
        offset = (source_map or {}).get(item["chunk_id"], {}).get("submitted_start", 0)
        a, b = start - offset, end - offset
        if not 0 <= a < b <= len(item["text"]):
            raise ValueError("CONTEXT_SELECTION_RANGE_MISMATCH")
        text = item["text"][a:b]
        if not text.startswith(first_text) or not text.endswith(blocks[last]["exact_text"]):
            raise ValueError("CONTEXT_SELECTION_TEXT_MISMATCH")
        selected.append({**item, "text": text, "text_hash": text_hash(text)})
        ranges[item["chunk_id"]] = {"submitted_start": start, "submitted_end": end}
        decisions.append(
            {
                "evidence_id": item["evidence_id"],
                "anchor_fragment_ids": [blocks[i]["fragment_id"] for i in sorted(anchors)],
                "context_fragment_ids": [f["fragment_id"] for f in blocks[first : last + 1]],
                "chunk_start": start,
                "chunk_end": end,
                "reason": "facet_anchors_and_contiguous_neighbor_context",
                "semantic_sufficiency": None,
            }
        )
    return (
        selected,
        ranges,
        excluded,
        {
            "version": VERSION,
            "decisions": decisions,
            "scope": "Generation context only; final highlights and support require separate checks.",
        },
    )
