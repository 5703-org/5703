"""Authored lexical packing regressions; these are not answer-quality labels."""

from copy import deepcopy
import hashlib
import pytest

from retrieval.complementary_spans import (
    AXIS_ANCHOR_REVISION,
    _explicit_axis_terms,
    select_context,
)


def fixture(sentences):
    text = "\n".join(sentences)
    item = {
        "evidence_id": "ev_001",
        "chunk_id": "chunk_a",
        "text": text,
        "text_hash": hashlib.sha256(text.encode()).hexdigest(),
        "source_title": "Authored packing fixture",
    }
    blocks, cursor = [], 0
    for i, sentence in enumerate(sentences):
        blocks.append(
            {
                "evidence_id": "ev_001",
                "fragment_id": f"f_{i}",
                "complete_block": True,
                "chunk_start": cursor,
                "chunk_end": cursor + len(sentence),
                "exact_text": sentence,
            }
        )
        cursor += len(sentence) + 1
    return item, blocks


def understanding(
    question="Explain the pressure difference in simpler language",
    axis="pressures",
    objects=("Alpha", "Beta"),
):
    point = {
        "id": "requirement_01",
        "request": question,
        "verbatim_request": question,
        "terms": [*objects, axis],
        "intent": "comparison",
        "objects": list(objects),
        "relation": "compare_both_objects_on_requested_axes",
        "requested_axes": [axis],
        "request_span": {
            "coordinate_space": "requirement_source_text",
            "start": 0,
            "end": len(question),
        },
    }
    return {
        "version": "question_requirements_v5",
        "requirement_source_text": question,
        "required_knowledge": [point],
        "requested_facets": [deepcopy(point)],
    }


def run(sentences, data=None, offset=0):
    item, blocks = fixture(sentences)
    for block in blocks:
        block["chunk_start"] += offset
        block["chunk_end"] += offset
    return (
        item,
        blocks,
        select_context(
            [item],
            blocks,
            "Explain the difference",
            data,
            {"chunk_a": {"submitted_start": offset}},
        ),
    )


def test_axis_candidates_survive_object_name_dominance():
    sentences = [
        "The pressure is lower only if the boundary remains sealed.",
        "This condition must not be discarded.",
        *[f"Neutral connecting sentence number {i}." for i in range(8)],
        "Alpha and Beta share a pressure boundary.",
        "The final qualification remains recorded.",
    ]
    data = understanding()
    item, blocks, (selected, ranges, excluded, trace) = run(sentences, data)
    old = deepcopy(data)
    old.pop("version")
    _, _, (old_selected, old_ranges, _, old_trace) = run(sentences, old)
    assert sentences[0] not in old_selected[0]["text"]
    assert sentences[0] in selected[0]["text"]
    assert sentences[1] in selected[0]["text"]
    assert old_selected[0]["text"] in selected[0]["text"]
    assert (
        selected[0]["text"]
        == item["text"][ranges["chunk_a"]["submitted_start"] : ranges["chunk_a"]["submitted_end"]]
    )
    assert len(selected[0]["text"]) <= len(item["text"])
    assert selected[0]["text_hash"] == hashlib.sha256(selected[0]["text"].encode()).hexdigest()
    assert excluded == []
    assert trace["axis_anchor_revision"] == AXIS_ANCHOR_REVISION
    assert {"f_0", "f_10"} <= set(trace["decisions"][0]["axis_anchor_fragment_ids"])
    assert trace["decisions"][0]["semantic_sufficiency"] is None
    assert "axis_anchor_revision" not in old_trace
    assert ranges["chunk_a"]["submitted_start"] <= old_ranges["chunk_a"]["submitted_start"]
    assert ranges["chunk_a"]["submitted_end"] >= old_ranges["chunk_a"]["submitted_end"]


def test_real_complete_sugar_sentence_survives_same_noun_anchor():
    # Exact complete sentences from the newly authorized OpenStax page 110 input;
    # this checks retention, not the scientific accuracy of a generated answer.
    structural = "sugars is the presence of the hydroxyl group on the ribose's second carbon and hydrogen on the deoxyribose's second carbon."
    backbone = (
        "The sugar and phosphate lie on the outside of the helix, forming the DNA's backbone."
    )
    sentences = [
        structural,
        "The carbon atoms are numbered.",
        *[f"Intervening source block {i}." for i in range(8)],
        backbone,
        "Hydrogen bonds bind the pairs to each other.",
    ]
    data = understanding(
        "Explain the sugar difference in simpler language", "sugars", ("DNA", "RNA")
    )
    _, _, (selected, _, _, trace) = run(sentences, data)
    assert structural in selected[0]["text"]
    assert backbone in selected[0]["text"]
    assert "f_0" in trace["decisions"][0]["axis_anchor_fragment_ids"]


@pytest.mark.parametrize("axis", ["temperatures", "masses", "rates", "conductivities"])
def test_axis_selection_has_no_dna_lexicon(axis):
    sentences = [
        f"The {axis} change only under the stated condition.",
        *[f"Connection {i}." for i in range(8)],
        f"Alpha and Beta share {axis}.",
    ]
    _, _, (selected, _, _, _) = run(sentences, understanding(axis=axis))
    assert sentences[0] in selected[0]["text"]


def test_all_explicit_axes_and_conditional_negation_remain_contiguous():
    sentences = [
        "The pressure does not increase if the outlet is open.",
        *[f"Connection {i}." for i in range(7)],
        "The temperature decreases unless the inlet is closed.",
        "Alpha and Beta share pressure and temperature readings.",
    ]
    data = understanding()
    for key in ("required_knowledge", "requested_facets"):
        data[key][0]["requested_axes"] = ["pressures", "temperatures"]
    _, _, (selected, _, _, trace) = run(sentences, data)
    assert sentences[0] in selected[0]["text"]
    assert sentences[8] in selected[0]["text"]
    assert "f_0" in trace["decisions"][0]["axis_anchor_fragment_ids"]
    assert "f_8" in trace["decisions"][0]["axis_anchor_fragment_ids"]


def test_offsets_preserve_already_submitted_excerpt():
    item, blocks, (selected, ranges, _, _) = run(
        [
            "The pressure falls only if sealed.",
            "Alpha and Beta share a pressure reading.",
        ],
        understanding(),
        offset=200,
    )
    a, b = (
        ranges["chunk_a"]["submitted_start"] - 200,
        ranges["chunk_a"]["submitted_end"] - 200,
    )
    assert selected[0]["text"] == item["text"][a:b]
    assert ranges["chunk_a"]["submitted_start"] >= 200


@pytest.mark.parametrize(
    "change",
    [
        "version",
        "space",
        "end",
        "bool_start",
        "verbatim",
        "relation",
        "axes_none",
        "axes_string",
        "axes_empty",
        "axes_mixed",
        "source_none",
        "knowledge_string",
    ],
)
def test_invalid_or_unlocated_axes_keep_legacy_selection(change):
    data = understanding()
    point = data["required_knowledge"][0]
    if change == "version":
        data["version"] = "question_requirements_v4"
    elif change == "space":
        point["request_span"]["coordinate_space"] = "standalone_query"
    elif change == "end":
        point["request_span"]["end"] += 1
    elif change == "bool_start":
        point["request_span"]["start"] = False
    elif change == "verbatim":
        point["verbatim_request"] = "Different original request"
    elif change == "relation":
        point["relation"] = "causal_explanation"
    elif change == "axes_none":
        point["requested_axes"] = None
    elif change == "axes_string":
        point["requested_axes"] = "pressures"
    elif change == "axes_empty":
        point["requested_axes"] = []
    elif change == "axes_mixed":
        point["requested_axes"] = ["pressures", 5]
    elif change == "source_none":
        data["requirement_source_text"] = None
    elif change == "knowledge_string":
        data["required_knowledge"] = "untyped"
    assert _explicit_axis_terms(data) == set()
    _, _, (_, _, _, trace) = run(["The pressure falls.", "Alpha and Beta share pressure."], data)
    assert "axis_anchor_revision" not in trace


@pytest.mark.parametrize("kind", ["prose", "formula", "table", "caption", "unresolved_atomic"])
def test_clipped_prose_formula_and_table_are_not_promoted(kind):
    item, blocks = fixture(["The pressure differs.", "Alpha and Beta share a pressure boundary."])
    blocks[0].update(complete_block=False, block_kind=kind)
    selected, _, _, trace = select_context([item], blocks, "Compare", understanding())
    assert "f_0" not in trace["decisions"][0]["axis_anchor_fragment_ids"]
    assert blocks[0]["complete_block"] is False
    assert selected[0]["text"] == blocks[1]["exact_text"]
    for block in blocks:
        block["complete_block"] = False
    selected, _, excluded, _ = select_context([item], blocks, "Compare", understanding())
    assert selected == []
    assert excluded == [{"chunk_id": "chunk_a", "reason": "no_complete_source_block"}]


def test_exact_text_and_range_failures_remain_fail_closed():
    item, blocks = fixture(["The pressure differs."])
    bad = deepcopy(blocks)
    bad[0]["exact_text"] = "Different source text."
    with pytest.raises(ValueError, match="CONTEXT_SELECTION_TEXT_MISMATCH"):
        select_context([item], bad, "Compare", understanding())
    bad = deepcopy(blocks)
    bad[0]["chunk_end"] += 10
    with pytest.raises(ValueError, match="CONTEXT_SELECTION_RANGE_MISMATCH"):
        select_context([item], bad, "Compare", understanding())


def test_no_understanding_never_invents_an_axis():
    assert _explicit_axis_terms(None) == set()
    _, _, (_, _, _, trace) = run(["A pressure source.", "Another complete block."])
    assert "axis_anchor_revision" not in trace
