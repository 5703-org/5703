"""Authored PDF boundary mechanics; no scientific/model quality measurements."""

from copy import deepcopy
import hashlib
import socket
import unicodedata

import pytest

from generation import evidence_budget
from generation.token_counting import estimate_tokens
from retrieval.prerequisite_context_v1 import candidate, selector
from retrieval.prerequisite_context_v1.pdf_layout_authority_v1 import bind_caption_authority
from retrieval.source_spans import text_hash

CAPTION = (
    "FIGURE 9.4 The flux regulator transfers pressure only when its gate is open. "
    "The regulator does not reset unless the lever returns. Credit: Authored Mechanics Laboratory."
)
BODY = (
    "The regulator uses a movable plate to keep the passage aligned. "
    "Its lever returns to rest when the operator releases the control. "
    "The following sequence explains how to operate the regulator."
)
QUESTION = "Explain the flux regulator gate and reset conditions"


@pytest.fixture(autouse=True)
def forbid_external_transport(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("OFFLINE160_PDF_LAYOUT_TRANSPORT_FORBIDDEN")

    from generation import adapters

    for name in ("getaddrinfo", "create_connection"):
        monkeypatch.setattr(socket, name, denied)
    for name in ("connect", "connect_ex"):
        monkeypatch.setattr(socket.socket, name, denied)
    monkeypatch.setattr(adapters, "open_provider", denied)
    monkeypatch.setattr(adapters.LLMAdapter, "_call", denied)
    monkeypatch.setattr(adapters.http, "urlopen", denied)


def authored_pdf(*, image_count=1, caption_size=7.5, body_size=9, caption=CAPTION):
    """Create independent image/caption/body PDF blocks with authored text."""
    import pymupdf

    with pymupdf.open() as document:
        page = document.new_page(width=600, height=800)
        pixmap = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 20, 20), False)
        pixmap.clear_with(200)
        for index in range(image_count):
            # Two overlapping images intentionally make predecessor authority ambiguous.
            page.insert_image(
                pymupdf.Rect(40 + index, 40, 490 + index, 100), stream=pixmap.tobytes("png")
            )
        assert (
            page.insert_textbox(pymupdf.Rect(40, 105, 540, 138), caption, fontsize=caption_size)
            >= 0
        )
        assert page.insert_textbox(pymupdf.Rect(40, 141, 540, 220), BODY, fontsize=body_size) >= 0
        raw = page.get_text("text")
        data = document.tobytes()
    text = " ".join(unicodedata.normalize("NFC", raw).split())
    unit = {
        "id": "authored-unit",
        "page": 1,
        "raw_text": raw,
        "raw_text_hash": text_hash(raw),
        "cleaned_text": text,
        "text_hash": text_hash(text),
    }
    evidence = [
        {
            "evidence_id": "dev_004",
            "chunk_id": "authored-chunk",
            "asset_id": "authored-asset",
            "processing_id": "authored-processing",
            "document_version_id": "authored-version",
            "text": text,
            "text_hash": text_hash(text),
            "context_order": 4,
            "pages": [1],
            "source_title": "Authored PDF layout mechanics",
            "section": "DEV",
            "locator": "Page1",
        }
    ]
    mapping = {
        "authored-chunk": {
            "asset_id": "authored-asset",
            "processing_id": "authored-processing",
            "document_version_id": "authored-version",
            "chunk_text": text,
            "chunk_hash": text_hash(text),
            "units": [unit],
            "spans": [
                {
                    "unit_id": "authored-unit",
                    "page": 1,
                    "start": 0,
                    "end": len(text),
                    "chunk_start": 0,
                    "chunk_end": len(text),
                }
            ],
            "active": True,
            "revoked": False,
            "source_visibility_verified": True,
        }
    }
    return data, evidence, mapping


def bound_case(**kwargs):
    data, evidence, mapping = authored_pdf(**kwargs)
    before = deepcopy(mapping)
    units = bind_caption_authority(
        data,
        document_version_id="authored-version",
        expected_pdf_hash=hashlib.sha256(data).hexdigest(),
        units=mapping["authored-chunk"]["units"],
    )
    assert mapping == before
    mapping["authored-chunk"]["units"] = units
    mapping["authored-chunk"]["document_raw_hash"] = hashlib.sha256(data).hexdigest()
    return data, evidence, mapping


def stages(evidence, mapping, question=QUESTION):
    before = deepcopy((evidence, mapping))
    fragments, issues = candidate.map_fragments(evidence, mapping)
    selected, ranges, excluded, plan = selector.select_context(
        evidence,
        fragments,
        question,
        source_map=mapping,
    )
    packed, pack_excluded, report = evidence_budget.pack_evidence(
        deepcopy(selected),
        evidence_budget.requested_facets(question),
        estimate_tokens,
        3000,
    )
    assert (evidence, mapping) == before
    assert sum(estimate_tokens(row["text"]) for row in packed) <= 3000
    return fragments, packed, ranges


def test_verified_image_caption_body_layout_retains_whole_caption_and_both_conditions():
    _, evidence, mapping = bound_case()
    unit = mapping["authored-chunk"]["units"][0]
    block = unit["pdf_layout_authority"]["blocks"][0]
    assert unit["cleaned_text"][block["start"] : block["end"]] == CAPTION
    fragments, packed, ranges = stages(evidence, mapping)
    caption = next(row for row in fragments if row["block_kind"] == "caption")
    assert caption["complete_block"] and caption["exact_text"] == CAPTION
    assert any(CAPTION in row["text"] for row in packed)
    assert all(
        row["text"]
        == mapping["authored-chunk"]["chunk_text"][
            ranges[row["chunk_id"]]["submitted_start"] : ranges[row["chunk_id"]]["submitted_end"]
        ]
        for row in packed
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"image_count": 0},
        {"image_count": 2},
        {"caption_size": 9},
        {"caption": CAPTION + " Would closing the gate reduce pressure?"},
    ],
)
def test_no_image_ambiguous_image_same_type_scale_or_caption_question_supplies_no_layout_authority(
    kwargs,
):
    _, evidence, mapping = bound_case(**kwargs)
    assert "pdf_layout_authority" not in mapping["authored-chunk"]["units"][0]
    fragments, _, _ = stages(evidence, mapping)
    assert not any(row["block_kind"] == "caption" and row["complete_block"] for row in fragments)


def test_missing_pdf_bytes_remove_untrusted_incoming_hints_and_do_not_guess_boundary():
    _, evidence, mapping = authored_pdf()
    unit = mapping["authored-chunk"]["units"][0]
    unit["pdf_layout_authority"] = {"version": "unverified-caller-metadata"}
    rebuilt = bind_caption_authority(
        None, document_version_id="authored-version", expected_pdf_hash=None, units=[unit]
    )
    assert "pdf_layout_authority" not in rebuilt[0]
    mapping["authored-chunk"]["units"] = rebuilt
    fragments, _, _ = stages(evidence, mapping)
    assert not any(row["block_kind"] == "caption" and row["complete_block"] for row in fragments)


@pytest.mark.parametrize(
    "defect",
    [
        "raw_hash",
        "cleaned_hash",
        "chunk_hash",
        "evidence_hash",
        "asset",
        "processing",
        "version",
        "revoked",
        "visibility",
        "inactive",
        "proof_unit",
        "proof_page",
        "proof_raw_hash",
        "proof_cleaned_hash",
        "proof_version",
        "proof_block_hash",
        "proof_range",
        "proof_geometry",
        "proof_pdf_hash",
        "source_pdf_hash",
        "missing_pdf_hash",
    ],
)
def test_source_or_layout_binding_defect_fails_before_admission(defect):
    _, evidence, mapping = bound_case()
    source = mapping["authored-chunk"]
    unit = source["units"][0]
    proof = unit["pdf_layout_authority"]
    if defect == "raw_hash":
        unit["raw_text_hash"] = "0" * 64
    elif defect == "cleaned_hash":
        unit["text_hash"] = "0" * 64
    elif defect == "chunk_hash":
        source["chunk_hash"] = "0" * 64
    elif defect == "evidence_hash":
        evidence[0]["text_hash"] = "0" * 64
    elif defect == "asset":
        evidence[0]["asset_id"] = "foreign"
    elif defect == "processing":
        evidence[0]["processing_id"] = "foreign"
    elif defect == "version":
        evidence[0]["document_version_id"] = "foreign"
    elif defect == "revoked":
        source["revoked"] = True
    elif defect == "visibility":
        source["source_visibility_verified"] = False
    elif defect == "inactive":
        source["active"] = False
    elif defect == "proof_unit":
        proof["source_unit_id"] = "foreign"
    elif defect == "proof_page":
        proof["page"] = 2
    elif defect == "proof_raw_hash":
        proof["raw_text_hash"] = "0" * 64
    elif defect == "proof_cleaned_hash":
        proof["cleaned_text_hash"] = "0" * 64
    elif defect == "proof_version":
        proof["document_version_id"] = "foreign"
    elif defect == "proof_block_hash":
        proof["blocks"][0]["text_hash"] = "0" * 64
    elif defect == "proof_range":
        proof["blocks"][0]["end"] -= 1
    elif defect == "proof_pdf_hash":
        proof["pdf_hash"] = "0" * 64
    elif defect == "source_pdf_hash":
        source["document_raw_hash"] = "0" * 64
    elif defect == "missing_pdf_hash":
        source.pop("document_raw_hash")
    else:
        proof["blocks"][0]["caption_bbox"][3] = proof["blocks"][0]["following_body_bbox"][3]
    with pytest.raises(ValueError) as caught:
        candidate.map_fragments(evidence, mapping)
    if defect != "missing_pdf_hash":
        assert str(caught.value) != "SOURCE_PDF_LAYOUT_DOCUMENT_HASH_MISSING"


def test_pdf_byte_hash_mismatch_and_duplicate_unit_identity_fail_closed():
    data, _, mapping = authored_pdf()
    units = mapping["authored-chunk"]["units"]
    with pytest.raises(ValueError, match="SOURCE_PDF_LAYOUT_DOCUMENT_HASH_MISMATCH"):
        bind_caption_authority(
            data, document_version_id="authored-version", expected_pdf_hash="0" * 64, units=units
        )
    with pytest.raises(ValueError, match="SOURCE_UNIT_DUPLICATE"):
        bind_caption_authority(
            data,
            document_version_id="authored-version",
            expected_pdf_hash=hashlib.sha256(data).hexdigest(),
            units=[*units, *units],
        )


@pytest.mark.parametrize(
    "kind", ["caption", "table", "formula", "image_transcription", "unresolved_atomic"]
)
def test_explicit_atomic_authority_precedes_pdf_layout_and_clipped_block_is_withheld(kind):
    data, evidence, mapping = authored_pdf()
    unit = mapping["authored-chunk"]["units"][0]
    unit["block_kind"] = kind
    rebuilt = bind_caption_authority(
        data,
        document_version_id="authored-version",
        expected_pdf_hash=hashlib.sha256(data).hexdigest(),
        units=[unit],
    )
    assert rebuilt == [unit] and "pdf_layout_authority" not in rebuilt[0]
    mapping["authored-chunk"]["units"] = rebuilt
    end = len(evidence[0]["text"]) // 2
    evidence[0]["text"] = evidence[0]["text"][:end]
    evidence[0]["text_hash"] = text_hash(evidence[0]["text"])
    mapping["authored-chunk"]["submitted_start"] = 0
    mapping["authored-chunk"]["submitted_end"] = end
    fragments, packed, _ = stages(evidence, mapping)
    assert fragments and all(not row["complete_block"] for row in fragments)
    assert not packed


def test_verified_caption_cannot_recover_text_beyond_admitted_nonzero_crop():
    _, evidence, mapping = bound_case()
    source = mapping["authored-chunk"]
    proof = source["units"][0]["pdf_layout_authority"]["blocks"][0]
    start, end = proof["start"] + 12, proof["end"] - 8
    evidence[0]["text"] = source["chunk_text"][start:end]
    evidence[0]["text_hash"] = text_hash(evidence[0]["text"])
    source["submitted_start"], source["submitted_end"] = start, end
    fragments, packed, _ = stages(evidence, mapping)
    assert fragments and all(not row["complete_block"] for row in fragments)
    assert not packed


def test_unverified_layout_metadata_is_rejected_at_consumer_without_raw_guess_fallback():
    _, evidence, mapping = authored_pdf()
    mapping["authored-chunk"]["document_raw_hash"] = "0" * 64
    mapping["authored-chunk"]["units"][0]["pdf_layout_authority"] = {"version": "unverified"}
    with pytest.raises(ValueError, match="SOURCE_PDF_LAYOUT_BINDING_MISMATCH"):
        candidate.map_fragments(evidence, mapping)


def test_explicit_generic_figure_reference_keeps_complete_verified_caption_without_content_terms():
    _, evidence, mapping = bound_case()
    fragments, packed, _ = stages(evidence, mapping, question="What does Figure 9.4 show?")
    assert any(
        row["block_kind"] == "caption" and row["complete_block"] and row["exact_text"] == CAPTION
        for row in fragments
    )
    assert any(CAPTION in row["text"] for row in packed)


def test_scoped_caption_guard_preserves_canine_dog_prose_fallback():
    _, evidence, mapping = authored_pdf()
    text = "Canines are mammals with a keen sense of smell. A canine can learn routines through repeated practice."
    unit = mapping["authored-chunk"]["units"][0]
    unit.update(
        raw_text=text, raw_text_hash=text_hash(text), cleaned_text=text, text_hash=text_hash(text)
    )
    evidence[0].update(text=text, text_hash=text_hash(text))
    source = mapping["authored-chunk"]
    source.update(chunk_text=text, chunk_hash=text_hash(text))
    source["spans"][0].update(start=0, end=len(text), chunk_start=0, chunk_end=len(text))
    _, packed, _ = stages(evidence, mapping, question="Tell me about dogs.")
    assert packed and "Canines are mammals with a keen sense of smell." in packed[0]["text"]


@pytest.mark.parametrize(
    "question", ["Why can bicycles not fly?", "Why do bridges fail only if supports are absent?"]
)
def test_new_caption_does_not_link_on_conditional_function_words_alone(question):
    _, evidence, mapping = bound_case()
    source = mapping["authored-chunk"]
    text = source["chunk_text"]
    end = text.index("The regulator uses a movable plate to keep the passage aligned.") + len(
        "The regulator uses a movable plate to keep the passage aligned."
    )
    evidence[0].update(text=text[:end], text_hash=text_hash(text[:end]))
    source["submitted_start"], source["submitted_end"] = 0, end
    fragments, packed, _ = stages(evidence, mapping, question=question)
    assert any(
        row["block_kind"] == "caption" and row["complete_block"] and row["exact_text"] == CAPTION
        for row in fragments
    )
    assert all(CAPTION not in row["text"] for row in packed)
    assert packed == []  # No newly released unrelated body may remain.


def test_wrong_figure_reference_blocks_new_body_even_with_subject_word_overlap():
    _, evidence, mapping = bound_case()
    source = mapping["authored-chunk"]
    text = source["chunk_text"]
    end = text.index("The regulator uses a movable plate to keep the passage aligned.") + len(
        "The regulator uses a movable plate to keep the passage aligned."
    )
    evidence[0].update(text=text[:end], text_hash=text_hash(text[:end]))
    source["submitted_start"], source["submitted_end"] = 0, end
    _, packed, _ = stages(
        evidence, mapping, question="Using Figure 9.5, explain the flux regulator."
    )
    assert packed == []


def test_new_body_own_meaningful_terms_keep_exact_sentence_without_caption_dependency():
    _, evidence, mapping = bound_case()
    source = mapping["authored-chunk"]
    text = source["chunk_text"]
    quote = "The regulator uses a movable plate to keep the passage aligned."
    end = text.index(quote) + len(quote)
    evidence[0].update(text=text[:end], text_hash=text_hash(text[:end]))
    source["submitted_start"], source["submitted_end"] = 0, end
    _, packed, _ = stages(
        evidence, mapping, question="How does its movable plate keep the passage aligned?"
    )
    assert any(quote in row["text"] for row in packed)
