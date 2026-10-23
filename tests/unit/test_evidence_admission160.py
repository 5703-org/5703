"""PDF layout and exact admission controls; no inference or real database."""

from copy import deepcopy
import hashlib
import socket

import pymupdf
import pytest

from pipelines.clean import clean_source_text
from retrieval.prerequisite_context_v1 import candidate, selector
from retrieval.prerequisite_context_v1 import pdf_layout_authority_v1 as layout
from retrieval.source_spans import text_hash
from test_evidence_admission158 import source


@pytest.fixture(autouse=True)
def no_external_calls(monkeypatch):
    from generation import adapters, checked, service

    def denied(*args, **kwargs):
        raise AssertionError("Phase160 admission cannot use a generator, checker, DNS or socket")

    for name in ("socket", "create_connection", "getaddrinfo"):
        monkeypatch.setattr(socket, name, denied)
    for adapter in (adapters.LLMAdapter, service.LLMAdapter):
        for name in ("generate", "generate_basic", "count_tokens", "_call"):
            monkeypatch.setattr(adapter, name, denied)


def authored_pdf(
    *,
    image=True,
    body_size=9,
    caption=None,
    body_y=100,
    split_tail=False,
    caption_bottom=89,
    body_text=None,
    prefix_text=None,
):
    caption = (
        caption
        or "FIGURE 8.7 The device passes a signal only if its gate is open. Credit: Authored Lab."
    )
    document = pymupdf.open()
    page = document.new_page(width=500, height=250)
    if prefix_text:
        page.insert_text((30, 12), prefix_text, fontsize=9)
    if image:
        pixel = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 2, 2), False)
        pixel.clear_with(100)
        page.insert_image(pymupdf.Rect(40, 20, 440, 56), stream=pixel.tobytes("png"))
    page.insert_textbox(pymupdf.Rect(30, 60, 450, caption_bottom), caption, fontsize=7.5)
    if split_tail:
        page.insert_textbox(
            pymupdf.Rect(30, 90, 450, 109),
            "The arrows depict the next stage. Credit: Other Lab.",
            fontsize=7.5,
        )
        body_y = 120
    body = body_text or (
        "The device changes when its input is available. It remains closed unless its gate is open."
    )
    page.insert_textbox(pymupdf.Rect(30, body_y, 450, 170), body, fontsize=body_size)
    raw = page.get_text("text")
    data = document.tobytes()
    document.close()
    evidence, mapping = source(raw)
    unit = mapping["authored-chunk"]["units"][0]
    unit["page"] = 1
    mapping["authored-chunk"]["spans"][0]["page"] = 1
    evidence[0]["pages"] = [1]
    cleaned = clean_source_text(raw)
    if cleaned != unit["cleaned_text"]:
        unit["cleaned_text"] = cleaned
        unit["text_hash"] = text_hash(cleaned)
        evidence[0]["text"] = cleaned
        evidence[0]["text_hash"] = text_hash(cleaned)
        mapping["authored-chunk"].update(chunk_text=cleaned, chunk_hash=text_hash(cleaned))
        mapping["authored-chunk"]["spans"][0].update(end=len(cleaned), chunk_end=len(cleaned))
    return data, evidence, mapping


def bind(data, mapping):
    current = mapping["authored-chunk"]
    current["document_raw_hash"] = hashlib.sha256(data).hexdigest()
    current["units"] = layout.bind_caption_authority(
        data,
        document_version_id=current["document_version_id"],
        expected_pdf_hash=current["document_raw_hash"],
        units=current["units"],
    )
    return current["units"][0]


def test_actual_pdf_blocks_prove_whole_no_heading_caption_without_changing_source():
    data, evidence, mapping = authored_pdf(body_y=87)
    original = deepcopy((evidence, mapping))
    assert layout.needs_layout_authority(mapping["authored-chunk"]["units"][0])
    before, _ = candidate.map_fragments(evidence, mapping)
    assert not any(f["block_kind"] == "caption" for f in before)
    unit = bind(data, mapping)
    proof = unit["pdf_layout_authority"]["blocks"][0]
    fragments, _ = candidate.map_fragments(evidence, mapping)
    caption = next(f for f in fragments if f["block_kind"] == "caption")
    assert caption["complete_block"]
    assert caption["exact_text"] == unit["cleaned_text"][proof["start"] : proof["end"]]
    assert (
        clean_source_text(unit["raw_text"][proof["raw_start"] : proof["raw_end"]])
        == caption["exact_text"]
    )
    assert evidence == original[0]
    assert all(
        unit[k] == original[1]["authored-chunk"]["units"][0][k]
        for k in ("raw_text", "cleaned_text", "raw_text_hash", "text_hash")
    )
    selected, ranges, excluded, plan = selector.select_context(
        evidence, fragments, "Explain the device signal and gate condition", source_map=mapping
    )
    assert not excluded and caption["exact_text"] in selected[0]["text"]
    assert (
        selected[0]["text"]
        == evidence[0]["text"][
            ranges["authored-chunk"]["submitted_start"] : ranges["authored-chunk"]["submitted_end"]
        ]
    )
    assert plan["decisions"][0]["semantic_sufficiency"] is None


@pytest.mark.parametrize(
    "change", ["no_image", "same_type_scale", "overlap", "split_tail", "question", "equation"]
)
def test_unknown_or_ambiguous_pdf_structure_does_not_complete_caption(change):
    args = {"body_y": 87}
    if change == "no_image":
        args["image"] = False
    elif change == "same_type_scale":
        args["body_size"] = 7.5
    elif change == "overlap":
        args["body_y"] = 66
    elif change == "split_tail":
        args["split_tail"] = True
    elif change == "question":
        args["caption"] = "FIGURE 8.7 Which arrow depicts the signal? Credit: Author Lab."
    else:
        args["caption"] = "FIGURE 8.7 The relation x = 2 defines the signal. Credit: Author Lab."
    data, evidence, mapping = authored_pdf(**args)
    unit = bind(data, mapping)
    assert "pdf_layout_authority" not in unit
    fragments, _ = candidate.map_fragments(evidence, mapping)
    assert not any(f["block_kind"] == "caption" for f in fragments)


@pytest.mark.parametrize(
    "defect",
    [
        "pdf_hash",
        "version",
        "unit",
        "page",
        "raw_hash",
        "clean_hash",
        "range",
        "body_range",
        "style",
        "geometry",
        "unknown_revision",
        "missing_current_pdf_hash",
    ],
)
def test_declared_layout_binding_defects_are_integrity_stops(defect):
    data, evidence, mapping = authored_pdf(body_y=87)
    unit = bind(data, mapping)
    authority = unit["pdf_layout_authority"]
    block = authority["blocks"][0]
    if defect == "pdf_hash":
        authority["pdf_hash"] = "0" * 64
    elif defect == "version":
        authority["document_version_id"] = "foreign"
    elif defect == "unit":
        authority["source_unit_id"] = "foreign"
    elif defect == "page":
        authority["page"] = 2
    elif defect == "raw_hash":
        authority["raw_text_hash"] = "0" * 64
    elif defect == "clean_hash":
        authority["cleaned_text_hash"] = "0" * 64
    elif defect == "range":
        block["end"] -= 1
    elif defect == "body_range":
        block["body_start"] += 1
    elif defect == "style":
        block["body_font_size"] = block["caption_font_size"]
    elif defect == "geometry":
        block["following_body_bbox"][1] = block["caption_bbox"][1]
    elif defect == "unknown_revision":
        authority["algorithm_revision"] = "unknown"
    else:
        mapping["authored-chunk"].pop("document_raw_hash")
    with pytest.raises(ValueError):
        candidate.map_fragments(evidence, mapping)


@pytest.mark.parametrize("field", ["raw_text_hash", "text_hash"])
def test_producer_does_not_hide_source_unit_integrity_failure(field):
    data, _, mapping = authored_pdf(body_y=87)
    mapping["authored-chunk"]["units"][0][field] = "0" * 64
    with pytest.raises(ValueError, match="HASH_MISMATCH"):
        bind(data, mapping)


def test_pdf_bytes_hash_is_fresh_and_missing_input_drops_old_authority():
    data, _, mapping = authored_pdf(body_y=87)
    unit = bind(data, mapping)
    with pytest.raises(ValueError, match="DOCUMENT_HASH_MISMATCH"):
        layout.bind_caption_authority(
            data + b"changed",
            document_version_id="authored-version",
            expected_pdf_hash=hashlib.sha256(data).hexdigest(),
            units=[unit],
        )
    missing = layout.bind_caption_authority(
        None,
        document_version_id="authored-version",
        expected_pdf_hash=hashlib.sha256(data).hexdigest(),
        units=[unit],
    )
    assert "pdf_layout_authority" not in missing[0]
    invalid = b"not a PDF"
    malformed = layout.bind_caption_authority(
        invalid,
        document_version_id="authored-version",
        expected_pdf_hash=hashlib.sha256(invalid).hexdigest(),
        units=[unit],
    )
    assert "pdf_layout_authority" not in malformed[0]


@pytest.mark.parametrize(
    "kind", ["caption", "table", "formula", "image_transcription", "unresolved_atomic"]
)
def test_explicit_atomic_precedence_survives_original_pdf_layout(kind):
    data, evidence, mapping = authored_pdf(body_y=87)
    unit = mapping["authored-chunk"]["units"][0]
    unit["block_kind"] = kind
    assert not layout.needs_layout_authority(unit)
    unit = bind(data, mapping)
    assert "pdf_layout_authority" not in unit
    fragments, _ = candidate.map_fragments(evidence, mapping)
    assert len(fragments) == 1 and fragments[0]["block_kind"] == kind


@pytest.mark.parametrize("cut", ["inside_caption", "after_caption"])
def test_authority_never_turns_clipped_caption_into_complete_evidence(cut):
    data, evidence, mapping = authored_pdf(body_y=87)
    unit = bind(data, mapping)
    caption_end = unit["pdf_layout_authority"]["blocks"][0]["end"]
    end = caption_end - 1 if cut == "inside_caption" else caption_end
    current = mapping["authored-chunk"]
    current.update(submitted_start=0, submitted_end=end)
    evidence[0].update(
        text=current["chunk_text"][:end], text_hash=text_hash(current["chunk_text"][:end])
    )
    fragments, _ = candidate.map_fragments(evidence, mapping)
    caption = next(f for f in fragments if f["block_kind"] == "caption")
    assert caption["complete_block"] == (cut == "after_caption")
    assert all(f["chunk_end"] <= end for f in fragments)


def test_existing_hard_hyphen_cleaner_preserves_exact_raw_and_cleaned_caption_ranges():
    data, evidence, mapping = authored_pdf(
        body_y=87, caption="FIGURE 8.7 A co-\ntransport device acts. Credit: Lab."
    )
    unit = bind(data, mapping)
    block = unit["pdf_layout_authority"]["blocks"][0]
    fragments, _ = candidate.map_fragments(evidence, mapping)
    caption = next(fragment for fragment in fragments if fragment["block_kind"] == "caption")
    assert "co-transport" in caption["exact_text"]
    raw = unit["raw_text"][block["raw_start"] : block["raw_end"]]
    assert "co-\ntransport" in raw
    assert clean_source_text(raw) == caption["exact_text"]
    assert caption["complete_block"]


def test_path_stream_and_bytes_fixture_produce_the_same_bound_authority(tmp_path):
    data, _, mapping = authored_pdf(body_y=87)
    pdf = tmp_path / "fixture.pdf"
    pdf.write_bytes(data)
    args = dict(
        document_version_id="authored-version",
        expected_pdf_hash=hashlib.sha256(data).hexdigest(),
        units=mapping["authored-chunk"]["units"],
    )
    assert layout.bind_caption_authority(pdf, **args) == layout.bind_caption_authority(data, **args)
    pdf.write_bytes(data + b"changed")
    with pytest.raises(ValueError, match="DOCUMENT_HASH_MISMATCH"):
        layout.bind_caption_authority(pdf, **args)


def test_already_proven_raw_heading_caption_does_not_request_new_original_pdf_io():
    from test_evidence_admission158 import caption_source

    _, mapping = source(caption_source())
    assert not layout.needs_layout_authority(mapping["authored-chunk"]["units"][0])


def test_authority_resource_ceiling_is_a_conservative_no_hint(monkeypatch):
    data, _, mapping = authored_pdf(body_y=87)
    monkeypatch.setattr(layout, "MAX_PDF_BYTES", len(data) - 1)
    unit = bind(data, mapping)
    assert "pdf_layout_authority" not in unit


def test_oversize_path_is_not_opened_or_hashed(tmp_path, monkeypatch):
    data, _, mapping = authored_pdf(body_y=87)
    pdf = tmp_path / "oversize-fixture.pdf"
    pdf.write_bytes(data)
    monkeypatch.setattr(layout, "MAX_PDF_BYTES", len(data) - 1)
    original_open = type(pdf).open

    def denied_open(path, *args, **kwargs):
        if path == pdf:
            raise AssertionError("An oversize original must not be read")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(type(pdf), "open", denied_open)
    units = layout.bind_caption_authority(
        pdf,
        document_version_id="authored-version",
        expected_pdf_hash=hashlib.sha256(data).hexdigest(),
        units=mapping["authored-chunk"]["units"],
    )
    assert all("pdf_layout_authority" not in unit for unit in units)


def test_ordinary_path_change_during_layout_is_an_integrity_stop(tmp_path, monkeypatch):
    data, _, mapping = authored_pdf(body_y=87)
    pdf = tmp_path / "changing-fixture.pdf"
    pdf.write_bytes(data)
    original_open = pymupdf.open

    def changed_open(*args, **kwargs):
        document = original_open(*args, **kwargs)
        if args and args[0] == pdf:
            with pdf.open("ab") as stream:
                stream.write(b"changed")
        return document

    monkeypatch.setattr(pymupdf, "open", changed_open)
    with pytest.raises(ValueError, match="DOCUMENT_CHANGED"):
        layout.bind_caption_authority(
            pdf,
            document_version_id="authored-version",
            expected_pdf_hash=hashlib.sha256(data).hexdigest(),
            units=mapping["authored-chunk"]["units"],
        )


def test_same_size_pdf_swap_with_restored_mtime_cannot_bind_old_hash_to_new_geometry(
    tmp_path, monkeypatch
):
    import os

    original, _, mapping = authored_pdf(body_y=87)
    alternative, _, _ = authored_pdf(body_y=86)
    size = max(len(original), len(alternative))
    original = original.ljust(size, b"\n")
    alternative = alternative.ljust(size, b"\n")
    assert original != alternative and len(original) == len(alternative)
    pdf = tmp_path / "same-size-fixture.pdf"
    pdf.write_bytes(original)
    initial_stat = pdf.stat()
    extract = layout._page_captions

    def changed_layout(page):
        blocks = extract(page)
        pdf.write_bytes(alternative)
        os.utime(pdf, ns=(initial_stat.st_atime_ns, initial_stat.st_mtime_ns))
        return blocks

    monkeypatch.setattr(layout, "_page_captions", changed_layout)
    with pytest.raises(ValueError, match="DOCUMENT_HASH_MISMATCH"):
        layout.bind_caption_authority(
            pdf,
            document_version_id="authored-version",
            expected_pdf_hash=hashlib.sha256(original).hexdigest(),
            units=mapping["authored-chunk"]["units"],
        )


def test_full_verified_pdf_caption_suppresses_internal_heading_and_cropped_prefix_completion():
    data, evidence, mapping = authored_pdf(
        body_y=107,
        caption_bottom=102,
        caption="FIGURE 8.7 A pathway. Credit: Lab.\nMechanism Details\nThe arrows depict its path.",
    )
    unit = bind(data, mapping)
    full = unit["pdf_layout_authority"]["blocks"][0]
    fragments, _ = candidate.map_fragments(evidence, mapping)
    captions = [fragment for fragment in fragments if fragment["block_kind"] == "caption"]
    assert len(captions) == 1 and captions[0]["complete_block"]
    assert "Mechanism Details" in captions[0]["exact_text"]
    assert "The arrows depict its path." in captions[0]["exact_text"]
    assert captions[0]["start"] == full["start"] and captions[0]["end"] == full["end"]
    end = mapping["authored-chunk"]["chunk_text"].index("Mechanism Details") - 1
    mapping["authored-chunk"].update(submitted_start=0, submitted_end=end)
    evidence[0].update(
        text=evidence[0]["text"][:end], text_hash=text_hash(evidence[0]["text"][:end])
    )
    clipped, _ = candidate.map_fragments(evidence, mapping)
    assert clipped and all(not fragment["complete_block"] for fragment in clipped)
    assert not any("Mechanism Details" in fragment["exact_text"] for fragment in clipped)


def test_stream_that_grows_during_hash_cannot_extend_original_size_budget(tmp_path, monkeypatch):
    data, _, mapping = authored_pdf(body_y=87)
    pdf = tmp_path / "growing-fixture.pdf"
    pdf.write_bytes(data)
    original_open = type(pdf).open
    reads = []

    class GrowingStream:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.stream.close()

        def read(self, size):
            reads.append(size)
            block = self.stream.read(size)
            if len(reads) == 1:
                with original_open(pdf, "ab") as writer:
                    writer.write(b"changed")
            return block

    def changed_open(path, *args, **kwargs):
        stream = original_open(path, *args, **kwargs)
        return GrowingStream(stream) if path == pdf and args == ("rb",) else stream

    monkeypatch.setattr(type(pdf), "open", changed_open)
    with pytest.raises(ValueError, match="DOCUMENT_CHANGED"):
        layout.bind_caption_authority(
            pdf,
            document_version_id="authored-version",
            expected_pdf_hash=hashlib.sha256(data).hexdigest(),
            units=mapping["authored-chunk"]["units"],
        )
    assert len(reads) == 2 and reads[-1] == 1
    assert max(reads) <= 8 * 1024 * 1024


@pytest.mark.parametrize(
    "question,linked",
    [
        ("Explain the device signal", True),
        ("Explain Figure 8.7", True),
        ("Explain Figure 8.8 and the device signal", False),
        ("Using Table 8.7, explain the device signal", False),
        ("Explain Figure 8.8 and incidental number 8.7 from Credit Lab", False),
        ("Explain chlorophyll and photosynthesis", False),
        ("Explain Credit Lab", False),
        ("Explain figure number 8.7", False),
    ],
)
def test_new_pdf_caption_requires_actual_request_anchor_or_exact_explicit_reference(
    question, linked
):
    data, evidence, mapping = authored_pdf(body_y=87)
    bind(data, mapping)
    fragments, _ = candidate.map_fragments(evidence, mapping)
    caption = next(fragment for fragment in fragments if fragment["block_kind"] == "caption")
    before = deepcopy(fragments)
    selected, _, excluded, plan = selector.select_context(
        evidence, fragments, question, source_map=mapping
    )
    retained = any(caption["exact_text"] in row["text"] for row in selected)
    assert retained == linked
    assert fragments == before
    decision = plan["decisions"][0] if plan["decisions"] else excluded[0]
    assert (
        caption["fragment_id"] in decision.get("linked_layout_caption_fragment_ids", [])
    ) == linked
    assert (caption["fragment_id"] in decision["withheld_layout_caption_fragment_ids"]) != linked


def test_existing_raw_complete_caption_keeps_no_overlap_fallback_even_with_extra_pdf_hint():
    data, evidence, mapping = authored_pdf(
        body_y=87, body_text="Mechanism Details\nThe device changes when its input is available."
    )
    old, _ = candidate.map_fragments(evidence, mapping)
    assert any(
        fragment["block_kind"] == "caption" and fragment["complete_block"] for fragment in old
    )
    prior, _, _, _ = selector.select_context(evidence, old, "Explain Canines", source_map=mapping)
    bind(data, mapping)
    current, _ = candidate.map_fragments(evidence, mapping)
    selected, _, _, plan = selector.select_context(
        evidence, current, "Explain Canines", source_map=mapping
    )
    assert selected == prior
    assert plan["decisions"][0]["withheld_layout_caption_fragment_ids"] == []


def test_semantic_synonym_prose_fallback_is_unchanged_without_pdf_caption_authority():
    evidence, mapping = source("Dogs bark to signal their presence.")
    fragments, _ = candidate.map_fragments(evidence, mapping)
    selected, _, excluded, plan = selector.select_context(
        evidence, fragments, "Explain Canines", source_map=mapping
    )
    assert not excluded and selected[0]["text"] == evidence[0]["text"]
    assert plan["decisions"][0]["withheld_layout_caption_fragment_ids"] == []


def test_foreign_facet_reference_cannot_override_actual_question_reference():
    data, evidence, mapping = authored_pdf(body_y=87)
    bind(data, mapping)
    fragments, _ = candidate.map_fragments(evidence, mapping)
    understanding = {"requested_facets": [{"request": "Explain Figure 8.7 device signal"}]}
    selected, _, excluded, plan = selector.select_context(
        evidence, fragments, "Explain Figure 8.8 and the device", understanding, mapping
    )
    assert all("FIGURE 8.7" not in row["text"] for row in selected)
    record = plan["decisions"][0] if plan["decisions"] else excluded[0]
    assert record["withheld_layout_caption_fragment_ids"]


@pytest.mark.parametrize(
    "question",
    [
        "Why can bicycles not fly?",
        "Explain photosynthesis only if light is available",
        "Explain weather unless the forecast changes",
    ],
)
def test_function_and_condition_words_alone_cannot_link_a_new_pdf_caption(question):
    data, evidence, mapping = authored_pdf(
        body_y=87,
        caption="FIGURE 8.7 The device only signals if the gate opens and does not reset unless the lever returns. Credit: Lab.",
    )
    bind(data, mapping)
    fragments, _ = candidate.map_fragments(evidence, mapping)
    caption = next(fragment for fragment in fragments if fragment["block_kind"] == "caption")
    selected, _, excluded, plan = selector.select_context(
        evidence, fragments, question, source_map=mapping
    )
    assert all(caption["exact_text"] not in row["text"] for row in selected)
    record = plan["decisions"][0] if plan["decisions"] else excluded[0]
    assert caption["fragment_id"] in record["withheld_layout_caption_fragment_ids"]
    linked, _, _, _ = selector.select_context(
        evidence, fragments, "Explain Figure 8.7", source_map=mapping
    )
    assert caption["exact_text"] in linked[0]["text"]
    assert "only signals if" in linked[0]["text"] and "does not reset unless" in linked[0]["text"]


@pytest.mark.parametrize(
    "question",
    [
        "Why can bicycles not fly?",
        "Explain photosynthesis only if light is available",
        "Explain Canines",
        "Explain Figure 8.8 device and input",
        "Using Table 8.7, explain the device input",
    ],
)
def test_new_pdf_only_successor_prose_cannot_activate_old_empty_fallback(question):
    data, evidence, mapping = authored_pdf(body_y=87)
    # The admitted chunk contains only the successor, while the full unit and
    # original caption remain immutable authority. The old whole atomic region
    # is clipped; complete old coarse atomic units are a separate fallback.
    current_map = mapping["authored-chunk"]
    start = current_map["chunk_text"].index("The device changes")
    current_map.update(submitted_start=start, submitted_end=len(current_map["chunk_text"]))
    evidence[0].update(
        text=current_map["chunk_text"][start:],
        text_hash=text_hash(current_map["chunk_text"][start:]),
    )
    before_fragments, _ = candidate.map_fragments(evidence, mapping)
    before, _, _, _ = selector.select_context(
        evidence, before_fragments, question, source_map=mapping
    )
    assert before == []
    bind(data, mapping)
    fragments, _ = candidate.map_fragments(evidence, mapping)
    after, _, excluded, _ = selector.select_context(
        evidence, fragments, question, source_map=mapping
    )
    assert after == []
    assert excluded[0]["withheld_layout_prose_fragment_ids"]
    assert excluded[0]["reason"] == "no_request_linked_pdf_context"


def test_meaningful_new_body_anchor_can_retain_its_exact_sentence_without_unlinked_caption():
    data, evidence, mapping = authored_pdf(body_y=87)
    bind(data, mapping)
    fragments, _ = candidate.map_fragments(evidence, mapping)
    selected, _, _, plan = selector.select_context(
        evidence, fragments, "Describe the input availability", source_map=mapping
    )
    assert selected and "input is available" in selected[0]["text"]
    assert "FIGURE 8.7" not in selected[0]["text"]
    assert plan["decisions"][0]["linked_layout_prose_fragment_ids"]


def test_prior_prose_same_unit_survives_synonym_fallback_beside_new_ambiguous_caption():
    data, evidence, mapping = authored_pdf(
        body_y=87, prefix_text="Dogs bark to signal their presence."
    )
    current_map = mapping["authored-chunk"]
    end = current_map["chunk_text"].index("It remains closed") - 1
    current_map.update(submitted_start=0, submitted_end=end)
    evidence[0].update(
        text=current_map["chunk_text"][:end], text_hash=text_hash(current_map["chunk_text"][:end])
    )
    prior_fragments, _ = candidate.map_fragments(evidence, mapping)
    prior, _, _, _ = selector.select_context(
        evidence, prior_fragments, "Explain Canines", source_map=mapping
    )
    assert prior and prior[0]["text"] == "Dogs bark to signal their presence."
    bind(data, mapping)
    fragments, _ = candidate.map_fragments(evidence, mapping)
    selected, _, _, plan = selector.select_context(
        evidence, fragments, "Explain Canines", source_map=mapping
    )
    assert selected == prior
    assert not plan["decisions"][0]["linked_layout_prose_fragment_ids"]


def test_new_body_own_anchor_keeps_next_pronoun_only_condition_in_exact_context():
    data, evidence, mapping = authored_pdf(body_y=87)
    bind(data, mapping)
    current = mapping["authored-chunk"]
    start = current["chunk_text"].index("The device changes")
    current.update(submitted_start=start, submitted_end=len(current["chunk_text"]))
    evidence[0].update(
        text=current["chunk_text"][start:], text_hash=text_hash(current["chunk_text"][start:])
    )
    fragments, _ = candidate.map_fragments(evidence, mapping)
    selected, _, excluded, plan = selector.select_context(
        evidence, fragments, "Describe the input availability", source_map=mapping
    )
    assert not excluded and selected[0]["text"] == evidence[0]["text"]
    assert "It remains closed unless its gate is open." in selected[0]["text"]
    assert len(plan["decisions"][0]["linked_layout_prose_fragment_ids"]) == 2
