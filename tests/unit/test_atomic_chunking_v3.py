"""Whole qualified source units, immutable offsets and unchanged hard budgets."""

from copy import deepcopy

import pytest
from generation.evidence_budget import pack_evidence, requested_facets
from pipelines.chunk import chunks
from retrieval.complementary_spans import select_context
from retrieval.source_spans import map_fragments, text_hash


def unit(identity, text, sequence, *, raw=None, quality="ready", section="Science"):
    return {
        "id": identity,
        "sequence": sequence,
        "page": sequence,
        "section": section,
        "raw_text": raw if raw is not None else text,
        "cleaned_text": text,
        "quality": quality,
    }


def mapped(chunk, source):
    evidence = [
        {
            "evidence_id": "ev_001",
            "chunk_id": chunk["id"],
            "text": chunk["text"],
            "text_hash": chunk["text_hash"],
            "asset_id": "book",
            "processing_id": "new-run",
        }
    ]
    mapping = {
        chunk["id"]: {
            "document_version_id": "public-version",
            "asset_id": "book",
            "processing_id": "new-run",
            "chunk_text": chunk["text"],
            "chunk_hash": chunk["text_hash"],
            "spans": chunk["spans"],
            "units": [
                {
                    **u,
                    "text_hash": text_hash(u["cleaned_text"]),
                    "raw_text_hash": text_hash(u["raw_text"]),
                }
                for u in source
            ],
        }
    }
    return evidence, mapping


@pytest.mark.parametrize(
    "title,units,values",
    [
        ("Density at 20 degrees", "kg/m3", "Alpha 1200 Beta 800"),
        ("Respiration at one bar", "mL/min", "Gamma 5.2 Delta 2.1"),
        ("Concentration at 298 K", "mol/L", "Epsilon 0.03 Zeta 0.04"),
    ],
)
def test_complete_table_unit_can_use_existing_cap_without_target_clipping(title, units, values):
    table = f"TABLE 2.1 {title} Substance Value ({units}) {values}"
    sources = [
        unit("before", "Introduction describes several distinct source properties. " * 3, 1),
        unit("table", table, 2),
        unit("after", "A separate explanatory section follows.", 3),
    ]
    before = deepcopy(sources)
    count = lambda value: len(value.split())
    size = count(table)
    result = chunks(
        sources,
        "new-run",
        target=size - 1,
        cap=size + 2,
        overlap=0,
        strategy="structure_atomic",
        tokenizer=count,
    )
    preserved = next(c for c in result if c["text"] == table)
    assert preserved["tokens"] > size - 1 and preserved["tokens"] <= size + 2
    assert preserved["spans"] == [
        {
            "unit_id": "table",
            "start": 0,
            "end": len(table),
            "chunk_start": 0,
            "chunk_end": len(table),
            "page": 2,
        }
    ]
    assert sources == before
    evidence, mapping = mapped(preserved, sources)
    fragments, issues = map_fragments(evidence, mapping)
    assert not issues and fragments[0]["complete_block"]
    selected, _, excluded, _ = select_context(evidence, fragments, title, source_map=mapping)
    assert not excluded and selected[0]["text"] == table
    packed, excluded, _ = pack_evidence(selected, requested_facets(title), count, ceiling=size - 1)
    assert packed == [] and excluded[0]["reason"] == "evidence_ceiling"


@pytest.mark.parametrize("limit", ["body", "combined_window"])
def test_oversized_table_remains_clipped_and_ineligible_not_silently_promoted(limit):
    table = "TABLE 4.1 Values (mg/L) " + ("Substance 1.25 " * 20).strip()
    sources = [unit("table", table, 1)]
    count = lambda value: len(value.split())
    cap = 15 if limit == "body" else 100
    window = 512 if limit == "body" else 20
    result = chunks(
        sources,
        "new-run",
        target=12,
        cap=cap,
        overlap=0,
        strategy="structure_atomic",
        tokenizer=count,
        model_window=window,
    )
    assert result and all(c["tokens"] <= cap for c in result)
    for c in result:
        assert count("passage: Science\n" + c["text"]) <= window
        evidence, mapping = mapped(c, sources)
        fragments, issues = map_fragments(evidence, mapping)
        assert issues and all(not f["complete_block"] for f in fragments)
        selected, _, excluded, _ = select_context(evidence, fragments, "Values", source_map=mapping)
        assert selected == [] and excluded[0]["reason"] == "no_complete_source_block"


def test_numbered_marker_in_raw_keeps_flattened_title_units_notes_together():
    raw = "Values at 300 K\nSpecimen Density (g/mL)\nAlpha 2.1\nBeta 1.2\nTABLE 8.3\nOnly dry samples are included."
    text = " ".join(raw.split())
    sources = [unit("table", text, 1, raw=raw)]
    count = lambda value: len(value.split())
    result = chunks(
        sources,
        "new-run",
        target=10,
        cap=40,
        overlap=0,
        strategy="structure_atomic",
        tokenizer=count,
    )
    assert len(result) == 1 and result[0]["text"] == text
    assert "Only dry samples" in result[0]["text"]


@pytest.mark.parametrize("quality", ["blocked", "excluded", "supplemented"])
def test_table_marker_cannot_override_source_quality(quality):
    sources = [unit("bad", "TABLE 1.1 Alpha 1.0", 1, quality=quality)]
    assert chunks(sources, "new-run", strategy="structure_atomic") == []


def test_table_boundary_does_not_merge_with_adjacent_units_or_across_exclusion():
    sources = [
        unit("a", "A short source.", 1),
        unit("t", "TABLE 1.1 Alpha 1.0", 2),
        unit("bad", "Excluded data", 3, quality="excluded"),
        unit("b", "Another source.", 4),
    ]
    result = chunks(sources, "new-run", strategy="structure_atomic")
    assert [c["spans"][0]["unit_id"] for c in result] == ["a", "t", "b"]
    assert all(len(c["spans"]) == 1 for c in result)


def test_plain_prose_keeps_legacy_boundaries_and_source_bytes():
    sources = [
        unit("a", "A normal paragraph. " * 20, 1),
        unit("b", "A continuation paragraph. " * 10, 2),
    ]
    baseline = chunks(sources, "new-run", target=30, cap=40, overlap=4)
    candidate = chunks(
        sources, "new-run", target=30, cap=40, overlap=4, strategy="structure_atomic"
    )
    assert [{k: v for k, v in c.items() if k != "id"} for c in baseline] == [
        {k: v for k, v in c.items() if k != "id"} for c in candidate
    ]
    assert not {c["id"] for c in baseline} & {c["id"] for c in candidate}


def test_new_strategy_is_explicit_versioned_and_does_not_change_default():
    from app.core.exceptions import AppError
    from app.modules.knowledge.service import corpus_config, digest

    default = corpus_config()
    candidate = corpus_config({"strategy": "structure_atomic"})
    assert default["strategy"] == "structure" and default["chunker_revision"] == "token_spans_v2"
    assert candidate["chunker_revision"] == "token_spans_atomic_v3"
    assert (candidate["target"], candidate["cap"], candidate["overlap"]) == (320, 448, 48)
    assert digest(default) != digest(candidate)
    with pytest.raises(AppError):
        corpus_config({"strategy": "structure_atomic", "chunker_revision": "token_spans_v2"})


@pytest.mark.parametrize("strategy", ["structure", "fixed", "structure_atomic"])
def test_hard_limits_are_never_increased(strategy):
    with pytest.raises(ValueError):
        chunks([unit("t", "TABLE 1.1 Alpha 1.0", 1)], "new-run", strategy=strategy, cap=449)
