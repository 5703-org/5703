"""Authored admission mechanics; no model, database or semantic gold labels."""

from copy import deepcopy
from types import SimpleNamespace
import socket

import pytest

from generation.prompt_builder import build_messages
from generation.token_counting import TokenCounter
from generation.types import GenerationOutcome, GenerationRequest, ModelConfig
from retrieval.complementary_spans import select_context as native_selector
from retrieval.prerequisite_context_v1 import candidate, selector
from retrieval.prerequisite_context_v1.integration import prepare_context
from retrieval.source_spans import evidence_ranges, text_hash
from retrieval.source_spans_v2 import map_fragments as native_mapper
from test_raw_definition_source_blocks_v2 import SourcePublicationDB


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Admission mechanics cannot use network or DNS")

    for name in ("socket", "create_connection", "getaddrinfo"):
        monkeypatch.setattr(socket, name, denied)


def source(raw, *, start=0, end=None, block_kind=None, blocks=None):
    text = " ".join(raw.split())
    end = len(text) if end is None else end
    chunk_text = text[start:end]
    unit = dict(
        id="authored-unit",
        page=3,
        raw_text=raw,
        raw_text_hash=text_hash(raw),
        cleaned_text=text,
        text_hash=text_hash(text),
    )
    if block_kind:
        unit["block_kind"] = block_kind
    if blocks:
        unit["blocks"] = deepcopy(blocks)
    evidence = [
        dict(
            evidence_id="ev_004",
            chunk_id="authored-chunk",
            processing_id="authored-processing",
            asset_id="authored-asset",
            text=chunk_text,
            text_hash=text_hash(chunk_text),
            source_title="Authored admission mechanics",
            source_url="https://example.invalid/source",
            license="Authored fixture",
            locator="Unit 3",
            section="Authored section",
            pages=[3],
            context_order=4,
            inherited_from=None,
        )
    ]
    mapping = {
        "authored-chunk": dict(
            chunk_text=chunk_text,
            chunk_hash=text_hash(chunk_text),
            processing_id="authored-processing",
            asset_id="authored-asset",
            document_version_id="authored-version",
            units=[unit],
            spans=[
                dict(
                    unit_id=unit["id"],
                    page=3,
                    start=start,
                    end=end,
                    chunk_start=0,
                    chunk_end=len(chunk_text),
                )
            ],
        )
    }
    return evidence, mapping


def caption_source(credit="Credit: Authored Mechanics Lab.", body_start="To"):
    return (
        "FIGURE 8.1 The staged device passes a signal only if its gate is open.\n"
        f"{credit}\nMechanism Details\n"
        f"{body_start} understand the device, examine the signal path.\n"
        "The device does not operate unless the gate remains open."
    )


@pytest.mark.parametrize("credit", ["Credit: Authored Mechanics Lab.", "(credit: Authored Lab)"])
@pytest.mark.parametrize("body_start", ["To", "The", "One"])
def test_independent_credited_heading_preserves_whole_caption_and_conditions(credit, body_start):
    evidence, mapping = source(caption_source(credit, body_start))
    before = deepcopy((evidence, mapping))
    fragments, _ = candidate.map_fragments(evidence, mapping)
    caption = next(row for row in fragments if row["block_kind"] == "caption")
    assert caption["complete_block"]
    assert caption["exact_text"].endswith(credit)
    assert "only if its gate is open" in caption["exact_text"]
    assert caption["mapping_algorithm_revision"] == candidate.ALGORITHM_REVISION
    assert (
        caption["exact_text"]
        == mapping["authored-chunk"]["units"][0]["cleaned_text"][caption["start"] : caption["end"]]
    )
    selected, ranges, excluded, plan = selector.select_context(
        evidence,
        fragments,
        "Explain the device signal and gate condition",
        source_map=mapping,
    )
    assert not excluded
    assert caption["exact_text"] in selected[0]["text"]
    assert "does not operate unless" in selected[0]["text"]
    assert (
        selected[0]["text"]
        == evidence[0]["text"][
            ranges["authored-chunk"]["submitted_start"] : ranges["authored-chunk"]["submitted_end"]
        ]
    )
    assert plan["algorithm_revision"] == selector.ALGORITHM_REVISION
    assert (evidence, mapping) == before


@pytest.mark.parametrize(
    "tail",
    [
        "The arrows depict pathway direction.",
        "If the gate closes, would the signal increase or decrease?",
    ],
)
def test_credit_and_wrapped_capitalized_tail_do_not_prove_caption_completion(tail):
    raw = f"FIGURE 8.1 A layered pathway. Credit: Author Lab.\n{tail}"
    evidence, mapping = source(raw)
    fragments, _ = candidate.map_fragments(evidence, mapping)
    assert not any(row["block_kind"] == "caption" for row in fragments)
    assert not any(row["block_kind"] == "prose" for row in fragments)
    credit_end = len("FIGURE 8.1 A layered pathway. Credit: Author Lab.")
    clipped, clipped_map = source(raw, end=credit_end)
    fragments, issues = candidate.map_fragments(clipped, clipped_map)
    assert fragments and all(not row["complete_block"] for row in fragments)
    assert any(row["reason"] == "incomplete_atomic_block" for row in issues)


def test_possible_caption_continuation_remains_inside_caption_until_independent_heading():
    raw = (
        "FIGURE 8.1 A layered pathway. Credit: Author Lab.\n"
        "The arrows depict pathway direction.\nMechanism Details\n"
        "The pathway changes when energy is available."
    )
    evidence, mapping = source(raw)
    fragments, _ = candidate.map_fragments(evidence, mapping)
    caption = next(row for row in fragments if row["block_kind"] == "caption")
    assert "The arrows depict pathway direction." in caption["exact_text"]
    clipped, clipped_map = source(raw, end=len("FIGURE 8.1 A layered pathway. Credit: Author Lab."))
    fragments, issues = candidate.map_fragments(clipped, clipped_map)
    assert all(not row["complete_block"] for row in fragments)
    assert any(row["reason"] == "incomplete_atomic_block" for row in issues)


@pytest.mark.parametrize(
    "raw",
    [
        "FIGURE 8.1 A caption.\nThe arrows identify the next stage.",
        "FIGURE 8.1 A caption. (credit: Unclosed Lab\nMechanism Details\nTo inspect the device, open the case.",
        "VISU AL CONNE CTION\nFIGURE 8.1 A caption. Credit: Lab.\nIf the pH changes, would the gate open?",
    ],
)
def test_ambiguous_unclosed_credit_and_visual_question_stay_atomic(raw):
    evidence, mapping = source(raw)
    fragments, _ = candidate.map_fragments(evidence, mapping)
    assert not any(row["block_kind"] == "caption" for row in fragments)
    assert not any(row["block_kind"] == "prose" for row in fragments)


@pytest.mark.parametrize(
    "kind", ["caption", "table", "formula", "image_transcription", "unresolved_atomic"]
)
def test_explicit_atomic_authority_is_never_repartitioned(kind):
    evidence, mapping = source(caption_source(), block_kind=kind)
    before = deepcopy(mapping)
    fragments, _ = candidate.map_fragments(evidence, mapping)
    assert len(fragments) == 1 and fragments[0]["block_kind"] == kind
    assert mapping == before


def test_explicit_blocks_and_table_rows_keep_their_original_boundary_authority():
    raw = caption_source()
    length = len(" ".join(raw.split()))
    evidence, mapping = source(raw, blocks=[dict(start=0, end=length, kind="formula")])
    fragments, _ = candidate.map_fragments(evidence, mapping)
    assert len(fragments) == 1 and fragments[0]["block_kind"] == "formula"
    for table in ("TABLE 8.2 Values.\n", "A\tB\n", "A|B\n"):
        _, current = source(table + raw)
        assert candidate._partition(current["authored-chunk"]["units"][0]) is None


def test_complete_body_reference_is_prose_but_structural_equation_remains_atomic():
    raw = (
        caption_source()
        + "\nThe device uses the stored signal (Figure 8.2).\nThe equation x = 2 specifies the output."
    )
    evidence, mapping = source(raw)
    fragments, _ = candidate.map_fragments(evidence, mapping)
    reference = next(row for row in fragments if "stored signal" in row["exact_text"])
    equation = next(row for row in fragments if "x = 2" in row["exact_text"])
    assert reference["complete_block"] and reference["block_kind"] == "prose"
    assert reference["exact_text"] == "The device uses the stored signal (Figure 8.2)."
    assert equation["block_kind"] == "unresolved_atomic"


@pytest.mark.parametrize(
    "subjects", [("Nox", "Lug"), ("Caching", "Indexing"), ("Tension", "Compression")]
)
def test_complementary_definitions_and_repeated_conditions_survive_shared_terms(subjects):
    left, right = subjects
    sentences = [
        f"{left} refers to a first process.",
        f"{left} does not change unless its boundary is closed.",
        *[f"Neutral connecting statement number {i}." for i in range(6)],
        f"{right} uses a separate process.",
        f"{right} does not change unless its boundary is closed.",
        *[f"Other connecting statement number {i}." for i in range(6)],
        f"{left} and {right} share process labels.",
    ]
    evidence, mapping = source(" ".join(sentences))
    fragments, _ = candidate.map_fragments(evidence, mapping)
    selected, _, _, plan = selector.select_context(
        evidence, fragments, f"Compare {left} and {right} processes", source_map=mapping
    )
    assert all(
        sentence in selected[0]["text"]
        for sentence in (sentences[0], sentences[1], sentences[8], sentences[9])
    )
    decision = plan["decisions"][0]
    assert len(decision["definition_anchor_fragment_ids"]) >= 2
    assert len(decision["condition_anchor_fragment_ids"]) == 2
    assert decision["semantic_sufficiency"] is None


def test_unrelated_definition_and_condition_do_not_gain_request_linked_anchors():
    sentences = [
        "Other refers to a separate process.",
        "Other does not change unless inert.",
        *[f"Neutral connection number {i}." for i in range(8)],
        "Nox refers to the requested process.",
    ]
    evidence, mapping = source(" ".join(sentences))
    fragments, _ = candidate.map_fragments(evidence, mapping)
    selected, _, _, plan = selector.select_context(
        evidence, fragments, "Explain Nox", source_map=mapping
    )
    assert "Other refers" not in selected[0]["text"]
    assert plan["decisions"][0]["condition_anchor_fragment_ids"] == []


def test_request_linked_anchors_never_bridge_an_incomplete_formula():
    evidence, mapping = source(
        "Nox refers to the first process. Partial equation x = 2. Lug refers to the second process."
    )
    fragments, _ = candidate.map_fragments(evidence, mapping)
    formula = next(row for row in fragments if "x = 2" in row["exact_text"])
    formula["complete_block"] = False
    selected, _, _, plan = selector.select_context(
        evidence, fragments, "Compare Nox and Lug", source_map=mapping
    )
    assert "x = 2" not in selected[0]["text"]
    assert plan["decisions"][0]["incomplete_atomic_bridge_withheld"]
    assert plan["decisions"][0]["withheld_anchor_fragment_ids"]


@pytest.mark.parametrize(
    "defect",
    [
        "raw_hash",
        "unit_hash",
        "chunk_hash",
        "foreign_version",
        "revoked",
        "not_visible",
        "duplicate_normalization",
    ],
)
def test_original_integrity_guards_and_unique_alignment_remain_effective(defect):
    evidence, mapping = source(caption_source())
    unit = mapping["authored-chunk"]["units"][0]
    if defect == "duplicate_normalization":
        unit["cleaned_text"] += " " + unit["cleaned_text"]
        unit["text_hash"] = text_hash(unit["cleaned_text"])
        assert candidate._partition(unit) is None
        return
    if defect == "raw_hash":
        unit["raw_text_hash"] = "0" * 64
    elif defect == "unit_hash":
        unit["text_hash"] = "0" * 64
    elif defect == "chunk_hash":
        mapping["authored-chunk"]["chunk_hash"] = "0" * 64
    elif defect == "foreign_version":
        evidence[0]["document_version_id"] = "foreign"
    elif defect == "revoked":
        mapping["authored-chunk"]["revoked"] = True
    else:
        mapping["authored-chunk"]["source_visibility_verified"] = False
    with pytest.raises(ValueError):
        candidate.map_fragments(evidence, mapping)


def prepared():
    evidence, mapping = source(caption_source())
    request = GenerationRequest(
        request_id="authored-request",
        mode="interactive_chat",
        condition="E1",
        question="Explain the device signal and gate condition",
        evidence=evidence,
        source_map=deepcopy(mapping),
        config=ModelConfig(window_tokens=65536, tokenizer_provider="estimate"),
        source_block_policy=candidate.VERSION,
        generation_context_policy=selector.VERSION,
    )
    counter = TokenCounter(request.config)
    result = prepare_context(
        request,
        mapping,
        lambda current: build_messages(current, counter),
        native_mapper,
        native_selector,
    )
    return request, mapping, counter, result


def publication():
    request, mapping, counter, result = prepared()
    caption = next(row for row in result["fragments"] if row["block_kind"] == "caption")
    identity = caption["evidence_id"]
    text = caption["exact_text"] + f" [{identity}]"
    response = dict(
        schema_version="chat_response_v1",
        response_type="answer",
        answer_text=text,
        short_answer=None,
        citations=[identity],
        refusal_reason=None,
        follow_up_questions=[],
        confidence=0.5,
    )
    outcome = GenerationOutcome(
        response=response,
        evidence=deepcopy(result["selected"]),
        token_budget=result["report"],
        attribution=dict(
            fragments=deepcopy(result["fragments"]),
            evidence_ranges=evidence_ranges(result["selected"], result["source_map"]),
            claims=[
                dict(
                    answer_field="answer_text",
                    start=0,
                    end=len(text),
                    text=text,
                    fragment_ids=[caption["fragment_id"]],
                )
            ],
        ),
        delivered_projection=dict(
            response=deepcopy(response),
            citation_views=[
                dict(
                    evidence_id=identity,
                    claim_ids=[],
                    title="Authored caption",
                    pages=[3],
                    segments=[
                        dict(
                            text=caption["exact_text"],
                            highlight=True,
                            fragment_ids=[caption["fragment_id"]],
                        )
                    ],
                )
            ],
        ),
    )
    req = SimpleNamespace(
        id="authored-request",
        release_id="authored-release",
        owner_id="authored-learner",
        command=dict(
            enhancement_version="learning_enhancement_v1",
            source_block_policy=candidate.VERSION,
            generation_context_policy=selector.VERSION,
        ),
    )
    return (
        SourcePublicationDB(request.evidence, mapping),
        req,
        SimpleNamespace(id="authored-answer"),
        outcome,
        counter,
    )


def test_native_packer_relabels_local_ids_only_after_exact_context_and_publisher_revalidates_caption():
    from app.modules.learning_state import sources
    from app.modules.learning_state.models import AnswerAttribution, AnswerPresentation

    request, mapping, counter, result = prepared()
    assert result["selected"][0]["evidence_id"] == "ev_001"
    assert request.evidence[0]["evidence_id"] == "ev_004"
    assert result["report"]["evidence_tokens"] <= 3000
    assert sum(counter.count(row["text"]) for row in result["selected"]) <= 3000
    assert result["context_plan"]["algorithm_revision"] == selector.ALGORITHM_REVISION
    assert all(
        row["mapping_algorithm_revision"] == candidate.ALGORITHM_REVISION
        for row in result["fragments"]
    )
    db, req, answer, outcome, _ = publication()
    before = deepcopy(outcome.attribution)
    sources.persist_result(db, req, answer, outcome)
    assert outcome.attribution == before
    assert next(row for row in db.rows if isinstance(row, AnswerAttribution)).payload == before
    assert (
        next(row for row in db.rows if isinstance(row, AnswerPresentation)).payload["response"]
        == outcome.response
    )


@pytest.mark.parametrize(
    "defect", ["revoked", "changed_unit", "forged_caption", "foreign_citation"]
)
def test_actual_publication_stops_before_rows_on_changed_source_or_forged_caption(defect):
    from app.core.exceptions import AppError
    from app.modules.knowledge.models import Document, SourceUnit
    from app.modules.learning_state import sources

    db, req, answer, outcome, _ = publication()
    if defect == "revoked":
        db.records[Document, "authored-asset"].revoked = True
    elif defect == "changed_unit":
        db.records[SourceUnit, "authored-unit"].cleaned_text += " changed"
    elif defect == "forged_caption":
        outcome.attribution["fragments"][0]["exact_text"] += " forged"
    else:
        outcome.attribution["fragments"][0]["evidence_id"] = "ev_999"
    with pytest.raises(AppError):
        sources.persist_result(db, req, answer, outcome)
    assert not db.rows
