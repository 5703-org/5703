"""Exact public-source regression and authored boundary controls; no model calls."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from retrieval.source_spans import text_hash
from retrieval.source_spans_v2 import map_fragments
from retrieval.complementary_spans import select_context


def fixture(article="a", closing="\u201d"):
    raw = (
        "FIGURE 1.1 The caption describes a quoted result." + closing + "\n"
        f"Testing {article} Device\n"
        "A device responds only if the switch is open.\n"
        "The comparison device has no switch manipulation.\n"
        "The observed difference is due to the manipulation."
    )
    text = " ".join(raw.split())
    start = text.index(f"Testing {article} Device")
    passage = text[start:]
    unit = dict(
        id="unit",
        page=3,
        raw_text=raw,
        raw_text_hash=text_hash(raw),
        cleaned_text=text,
        text_hash=text_hash(text),
    )
    item = dict(
        evidence_id="ev_001",
        chunk_id="chunk",
        processing_id="processing",
        asset_id="asset",
        text=passage,
        text_hash=text_hash(passage),
    )
    mapping = {
        "chunk": dict(
            chunk_text=passage,
            chunk_hash=text_hash(passage),
            processing_id="processing",
            asset_id="asset",
            document_version_id="version",
            units=[unit],
            spans=[
                dict(
                    unit_id="unit",
                    page=3,
                    start=start,
                    end=len(text),
                    chunk_start=0,
                    chunk_end=len(passage),
                )
            ],
        )
    }
    return [item], mapping


@pytest.mark.parametrize("article", ["a", "an"])
@pytest.mark.parametrize("closing", ["\u201d", "\u2019", '"', ")"])
def test_quoted_sentence_and_article_heading_preserve_exact_prose(article, closing):
    evidence, mapping = fixture(article, closing)
    before = deepcopy((evidence, mapping))
    fragments, issues = map_fragments(evidence, mapping)
    assert fragments and all(f["complete_block"] and f["block_kind"] == "prose" for f in fragments)
    selected, ranges, excluded, _ = select_context(
        evidence, fragments, "Explain the device comparison.", source_map=mapping
    )
    assert not excluded and len(selected) == 1
    assert "only if" in selected[0]["text"] and "no switch manipulation" in selected[0]["text"]
    a, b = ranges["chunk"]["submitted_start"], ranges["chunk"]["submitted_end"]
    assert selected[0]["text"] == evidence[0]["text"][a:b]
    assert (evidence, mapping) == before


@pytest.mark.parametrize("defect", ["no_terminal", "no_body", "explicit_atomic", "no_raw"])
def test_uncorroborated_heading_or_atomic_authority_is_not_relaxed(defect):
    evidence, mapping = fixture()
    unit = mapping["chunk"]["units"][0]
    if defect == "no_terminal":
        unit["raw_text"] = unit["raw_text"].replace("result.\u201d", "result\u201d")
    elif defect == "no_body":
        unit["raw_text"] = unit["raw_text"].replace("A device responds", "device responds")
    elif defect == "explicit_atomic":
        unit["block_kind"] = "caption"
    else:
        unit.pop("raw_text")
        unit.pop("raw_text_hash")
    if "raw_text" in unit:
        unit["raw_text_hash"] = text_hash(unit["raw_text"])
    fragments, _ = map_fragments(evidence, mapping)
    assert not any(f["complete_block"] for f in fragments)
    assert not select_context(evidence, fragments, "Explain the device.", source_map=mapping)[0]


def test_wrong_raw_hash_remains_a_hard_failure():
    evidence, mapping = fixture()
    mapping["chunk"]["units"][0]["raw_text_hash"] = "0" * 64
    with pytest.raises(ValueError, match="RAW_TEXT_HASH_MISMATCH"):
        map_fragments(evidence, mapping)


def test_saved_public_control_group_source_survives_mapping_and_context_selection():
    data = json.loads(
        (Path(__file__).parents[1] / "fixtures/public_control_context_20261021.json").read_text(
            encoding="utf-8"
        )
    )
    before = deepcopy(data)
    fragments, issues = map_fragments(data["evidence"], data["source_map"])
    selected, ranges, excluded, _ = select_context(
        data["evidence"], fragments, data["question"], data["understanding"], data["source_map"]
    )
    assert len(selected) == 2 and not excluded
    control = next(x for x in selected if x["chunk_id"] == "dea996246155b0b5f5dfded24e839c504d0d")
    assert "The control group contains every feature" in control["text"]
    assert "rather than some outside factor" in control["text"]
    for item in selected:
        source = next(x for x in data["evidence"] if x["chunk_id"] == item["chunk_id"])
        a, b = (
            ranges[item["chunk_id"]]["submitted_start"],
            ranges[item["chunk_id"]]["submitted_end"],
        )
        assert item["text"] == source["text"][a:b]
        assert item["text_hash"] == text_hash(item["text"])
    assert any(x["reason"] == "clipped_source_sentence" for x in issues)
    assert data == before
