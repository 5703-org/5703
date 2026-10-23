"""Original-PDF source-map/publication mechanics with authored geometry and rows.

No model, credentials, real database, real corpus or scientific acceptance is used.
The current-row fake records actual producer lookups; publication calls the real
source-map and fragment mapper, and stores ORM objects only in memory.
"""

import ast
from collections import Counter
from copy import deepcopy
import hashlib
import inspect
import socket
from types import SimpleNamespace

import pymupdf
import pytest

from app.core.exceptions import AppError
from app.modules.knowledge.models import (
    Chunk,
    Document,
    DocumentVersion,
    ProcessingRun,
    ReleaseChunk,
    SourceUnit,
)
from app.modules.learning_state import pdf_layout_sources_v1 as adapter, sources
from app.modules.learning_state.models import (
    AnswerAttribution,
    AnswerPresentation,
    LearningExposure,
    SourceFragment,
)
from pipelines.clean import clean_source_text
from retrieval.prerequisite_context_v1 import candidate, pdf_layout_authority_v1 as layout
from retrieval.source_spans import text_hash

SOURCE_POLICY = "raw_corroborated_prose_context_candidate_v1"
CONTEXT_POLICY = "literal_coverage_complementary_context_candidate_v1"
CAPTION = "FIGURE 8.7 The panel sends a signal only when its gate is open. Credit: Fixture Lab."
BODY = "The panel changes when its input is available. Its gate otherwise remains closed."


@pytest.fixture(autouse=True)
def forbid_external_execution(monkeypatch):
    from generation.adapters import LLMAdapter
    from sqlalchemy.engine import Engine

    def denied(*args, **kwargs):
        raise AssertionError("PDF_BINDING160_EXTERNAL_EXECUTION_FORBIDDEN")

    for name in ("getaddrinfo", "create_connection"):
        monkeypatch.setattr(socket, name, denied)
    for name in ("connect", "connect_ex"):
        monkeypatch.setattr(socket.socket, name, denied)
    for name in ("generate", "generate_basic", "count_tokens", "_call"):
        monkeypatch.setattr(LLMAdapter, name, denied)
    monkeypatch.setattr(Engine, "connect", denied)


def authored_pdf():
    """Create native image/caption/body blocks with distinct actual PDF type sizes."""
    with pymupdf.open() as document:
        page = document.new_page(width=500, height=250)
        image = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 2, 2), False)
        image.clear_with(100)
        page.insert_image(pymupdf.Rect(40, 20, 440, 56), stream=image.tobytes("png"))
        assert page.insert_textbox(pymupdf.Rect(30, 60, 450, 85), CAPTION, fontsize=7.5) >= 0
        assert page.insert_textbox(pymupdf.Rect(30, 87, 450, 170), BODY, fontsize=9) >= 0
        raw = page.get_text("text")
        return document.tobytes(), raw


class CurrentRows:
    """Invocation-visible row store and in-memory publication sink, without SQL."""

    def __init__(self, rows):
        self.rows = rows
        self.reads = []
        self.added = []
        self.flushes = 0

    def get(self, model, identifier, **kwargs):
        self.reads.append((model, identifier, kwargs))
        return deepcopy(self.rows.get((model, identifier)))

    def add(self, row):
        self.added.append(row)

    def flush(self):
        self.flushes += 1
        for index, row in enumerate(self.added):
            if getattr(row, "id", None) is None:
                row.id = f"authored-publication-{index}"

    def refreshed(self, model, identifier):
        return sum(
            m is model and key == identifier and options == {"populate_existing": True}
            for m, key, options in self.reads
        )


@pytest.fixture
def pdf_source(tmp_path):
    data, raw = authored_pdf()
    storage = tmp_path / "storage"
    storage.mkdir()
    original = storage / "original.pdf"
    original.write_bytes(data)
    cleaned = clean_source_text(raw)
    unit = {
        "id": "unit",
        "page": 1,
        "raw_text": raw,
        "raw_text_hash": text_hash(raw),
        "cleaned_text": cleaned,
        "text_hash": text_hash(cleaned),
    }
    spans = [
        {
            "unit_id": "unit",
            "page": 1,
            "start": 0,
            "end": len(cleaned),
            "chunk_start": 0,
            "chunk_end": len(cleaned),
        }
    ]
    mapping = {
        "chunk": {
            "document_version_id": "version",
            "asset_id": "asset",
            "processing_id": "run",
            "units": [unit],
            "chunk_text": cleaned,
            "chunk_hash": text_hash(cleaned),
            "spans": spans,
        }
    }
    version = DocumentVersion(
        id="version",
        document_id="asset",
        media_type="application/pdf",
        storage_path="original.pdf",
        raw_hash=hashlib.sha256(data).hexdigest(),
        size_bytes=len(data),
        original_filename="Authored original.pdf",
    )
    rows = {
        (DocumentVersion, "version"): version,
        (Document, "asset"): SimpleNamespace(id="asset", active=True, revoked=False),
        (ProcessingRun, "run"): SimpleNamespace(
            id="run",
            document_version_id="version",
            counts={
                "source_unit_hashes": {
                    "unit": {"raw_hash": unit["raw_text_hash"], "cleaned_hash": unit["text_hash"]}
                }
            },
        ),
        (SourceUnit, "unit"): SimpleNamespace(
            id="unit",
            page=1,
            processing_id="run",
            quality="ready",
            raw_text=raw,
            cleaned_text=cleaned,
        ),
        (Chunk, "chunk"): SimpleNamespace(
            id="chunk",
            processing_id="run",
            document_id="asset",
            text=cleaned,
            text_hash=text_hash(cleaned),
            spans=spans,
        ),
        (ReleaseChunk, ("release", "chunk")): SimpleNamespace(chunk_id="chunk"),
    }
    evidence = [
        {
            "evidence_id": "ev_001",
            "chunk_id": "chunk",
            "asset_id": "asset",
            "processing_id": "run",
            "text": cleaned,
            "text_hash": text_hash(cleaned),
            "source_title": "Authored geometry fixture",
            "source_url": "https://example.invalid/authored",
            "license": "Authored test fixture",
            "locator": "Page 1",
            "section": "Authored section",
            "pages": [1],
            "context_order": 1,
            "inherited_from": None,
        }
    ]
    request = SimpleNamespace(
        release_id="release",
        owner_id="authored-owner",
        mode="interactive_chat",
        command={
            "enhancement_version": "learning_enhancement_v1",
            "source_block_policy": SOURCE_POLICY,
            "generation_context_policy": CONTEXT_POLICY,
        },
    )
    return SimpleNamespace(
        data=data,
        original=original,
        storage=storage,
        unit=unit,
        mapping=mapping,
        version=version,
        store=CurrentRows(rows),
        evidence=evidence,
        request=request,
    )


def bind(source, mapping=None, current=None):
    callback = current or (lambda model, key: source.store.get(model, key, populate_existing=True))
    return adapter.attach_pdf_layout_authority(mapping or source.mapping, callback, source.storage)


def binding_spy(monkeypatch):
    calls = []
    actual = adapter.bind_caption_authority

    def invoke(original, **kwargs):
        calls.append((original, deepcopy(kwargs)))
        return actual(original, **kwargs)

    monkeypatch.setattr(adapter, "bind_caption_authority", invoke)
    return calls


def assert_unbound(mapping):
    assert "document_raw_hash" not in mapping["chunk"]
    assert "pdf_layout_authority" not in mapping["chunk"]["units"][0]


def generated_result(source):
    mapped = sources.source_map(
        source.store, source.request, source.evidence, storage_root=source.storage
    )
    fragments, _ = candidate.map_fragments(source.evidence, mapped)
    caption = next(f for f in fragments if f["block_kind"] == "caption")
    assert caption["complete_block"] and caption["exact_text"] == CAPTION
    pair = {
        "bundle_version": "raw_corroborated_literal_context_v1",
        "requested_source_version": SOURCE_POLICY,
        "requested_context_version": CONTEXT_POLICY,
        "actual_source_version": SOURCE_POLICY,
        "actual_context_version": CONTEXT_POLICY,
        "fallback": None,
        "fallback_error_type": None,
    }
    # A caption-only attribution makes this fixture's publication obligation precise.
    return SimpleNamespace(
        evidence=deepcopy(source.evidence),
        attribution={"fragments": [caption], "claims": []},
        response={
            "response_type": "answer",
            "answer_text": "Authored mechanical fixture.",
            "short_answer": None,
            "citations": ["ev_001"],
        },
        delivered_projection={},
        token_budget={"prerequisite_context_pair": pair},
        response_origin="authored_fixture",
    )


def test_adapter_derives_exact_caption_from_real_original_geometry_without_mutating_inputs(
    pdf_source,
):
    source = pdf_source
    before = deepcopy(source.mapping)
    mapped = bind(source)
    unit = mapped["chunk"]["units"][0]
    block = unit["pdf_layout_authority"]["blocks"][0]
    assert layout.validated_blocks(
        unit, document_version_id="version", expected_pdf_hash=source.version.raw_hash
    )
    assert unit["cleaned_text"][block["start"] : block["end"]] == CAPTION
    assert clean_source_text(unit["raw_text"][block["raw_start"] : block["raw_end"]]) == CAPTION
    assert mapped["chunk"]["document_raw_hash"] == source.version.raw_hash
    assert source.mapping == before
    assert source.store.refreshed(DocumentVersion, "version") == 1


def test_same_document_original_is_bound_once_per_invocation_and_refreshed_next_time(
    pdf_source, monkeypatch
):
    source = pdf_source
    grouped = deepcopy(source.mapping)
    grouped["chunk-two"] = deepcopy(grouped["chunk"])
    calls = binding_spy(monkeypatch)
    first = bind(source, grouped)
    second = bind(source, grouped)
    assert len(calls) == 2 and all(len(options["units"]) == 1 for _, options in calls)
    assert source.store.refreshed(DocumentVersion, "version") == 2
    assert first == second
    first["chunk"]["units"][0]["pdf_layout_authority"]["blocks"].clear()
    assert first["chunk-two"]["units"][0]["pdf_layout_authority"]["blocks"]
    assert second["chunk"]["units"][0]["pdf_layout_authority"]["blocks"]


@pytest.mark.parametrize(
    "change",
    [
        "missing-version",
        "foreign-document",
        "invalid-hash",
        "uppercase-hash",
        "wrong-size",
        "boolean-size",
        "traversal",
        "absolute-outside",
        "changed-bytes",
    ],
)
def test_original_metadata_path_and_byte_changes_fail_closed(pdf_source, change):
    source = pdf_source
    version = source.store.rows[DocumentVersion, "version"]
    if change == "missing-version":
        source.store.rows.pop((DocumentVersion, "version"))
    elif change == "foreign-document":
        version.document_id = "foreign"
    elif change == "invalid-hash":
        version.raw_hash = "bad"
    elif change == "uppercase-hash":
        version.raw_hash = version.raw_hash.upper()
    elif change == "wrong-size":
        version.size_bytes += 1
    elif change == "boolean-size":
        version.size_bytes = True
    elif change in {"traversal", "absolute-outside"}:
        outside = source.storage.parent / "outside.pdf"
        outside.write_bytes(source.data)
        version.storage_path = "../outside.pdf" if change == "traversal" else str(outside)
    else:
        source.original.write_bytes(source.data[:-1] + bytes([source.data[-1] ^ 1]))
    with pytest.raises(AppError) as error:
        bind(source)
    assert error.value.code == "EVIDENCE_UNAVAILABLE"
    assert not source.store.added


@pytest.mark.parametrize("change", ["missing-original", "non-pdf", "unambiguous-prose"])
def test_unknown_original_or_unneeded_layout_strips_stale_hints_conservatively(
    pdf_source, change, monkeypatch
):
    source = pdf_source
    mapping = deepcopy(source.mapping)
    mapping["chunk"]["document_raw_hash"] = "0" * 64
    mapping["chunk"]["units"][0]["pdf_layout_authority"] = {"caller_supplied": True}
    if change == "missing-original":
        source.original.unlink()
    elif change == "non-pdf":
        source.store.rows[DocumentVersion, "version"].media_type = "text/plain"
    else:
        unit = mapping["chunk"]["units"][0]
        unit.update(
            raw_text=BODY,
            cleaned_text=BODY,
            raw_text_hash=text_hash(BODY),
            text_hash=text_hash(BODY),
        )
    original = deepcopy(mapping)
    calls = binding_spy(monkeypatch)
    result = bind(source, mapping)
    assert_unbound(result)
    assert mapping == original and not calls
    assert source.store.refreshed(DocumentVersion, "version") == (
        0 if change == "unambiguous-prose" else 1
    )


def test_fresh_original_replaces_caller_supplied_authority_and_keeps_input_unchanged(pdf_source):
    supplied = deepcopy(pdf_source.mapping)
    supplied["chunk"]["document_raw_hash"] = "0" * 64
    supplied["chunk"]["units"][0]["pdf_layout_authority"] = {"caller_supplied": True}
    before = deepcopy(supplied)
    mapped = bind(pdf_source, supplied)
    assert mapped["chunk"]["document_raw_hash"] == pdf_source.version.raw_hash
    assert mapped["chunk"]["units"][0]["pdf_layout_authority"]["version"] == layout.VERSION
    assert supplied == before


@pytest.mark.parametrize("change", ["asset", "unit"])
def test_grouped_inconsistent_asset_or_unit_identity_is_rejected_before_original_binding(
    pdf_source, monkeypatch, change
):
    mapping = deepcopy(pdf_source.mapping)
    mapping["second"] = deepcopy(mapping["chunk"])
    if change == "asset":
        mapping["second"]["asset_id"] = "foreign"
    else:
        mapping["second"]["units"][0]["cleaned_text"] += " Changed."
    calls = binding_spy(monkeypatch)
    with pytest.raises(AppError) as error:
        bind(pdf_source, mapping)
    assert error.value.code == "EVIDENCE_UNAVAILABLE" and not calls and not pdf_source.store.reads


@pytest.mark.parametrize("change", ["missing-storage-root", "legacy-policy"])
def test_source_map_preserves_previous_text_path_when_layout_is_not_activated(
    pdf_source, monkeypatch, change
):
    source = pdf_source
    if change == "legacy-policy":
        source.request.command["source_block_policy"] = "legacy_source_blocks_v1"
    calls = binding_spy(monkeypatch)
    result = sources.source_map(
        source.store,
        source.request,
        source.evidence,
        storage_root=None if change == "missing-storage-root" else source.storage,
    )
    assert_unbound(result)
    assert result["chunk"]["chunk_text"] == source.unit["cleaned_text"]
    assert result["chunk"]["spans"] == source.mapping["chunk"]["spans"]
    assert not calls and source.store.refreshed(DocumentVersion, "version") == 0


def test_real_source_map_loads_current_version_and_keeps_submitted_ranges_and_text(pdf_source):
    source = pdf_source
    evidence = deepcopy(source.evidence)
    evidence[0].update(chunk_start=2, chunk_end=len(source.unit["cleaned_text"]) - 2)
    mapped = sources.source_map(source.store, source.request, evidence, storage_root=source.storage)
    assert mapped["chunk"]["document_raw_hash"] == source.version.raw_hash
    assert mapped["chunk"]["submitted_start"] == 2
    assert mapped["chunk"]["submitted_end"] == len(source.unit["cleaned_text"]) - 2
    assert mapped["chunk"]["chunk_text"] == source.unit["cleaned_text"]
    assert source.store.refreshed(DocumentVersion, "version") == 1
    assert all(
        options == {"populate_existing": True}
        for model, _, options in source.store.reads
        if model is DocumentVersion
    )


def test_real_publication_rebinds_original_and_persists_exact_caption_in_memory(
    pdf_source, monkeypatch
):
    source = pdf_source
    calls = binding_spy(monkeypatch)
    result = generated_result(source)
    sources.persist_result(
        source.store,
        source.request,
        SimpleNamespace(id="authored-answer"),
        result,
        storage_root=source.storage,
    )
    assert len(calls) == 2 and source.store.refreshed(DocumentVersion, "version") == 2
    assert source.store.flushes == 1
    kinds = Counter(type(row) for row in source.store.added)
    assert kinds == Counter(
        {SourceFragment: 1, AnswerAttribution: 1, AnswerPresentation: 1, LearningExposure: 1}
    )
    fragment = next(row for row in source.store.added if isinstance(row, SourceFragment))
    assert fragment.text == CAPTION and fragment.text_hash == text_hash(CAPTION)
    assert fragment.document_version_id == "version" and fragment.source_unit_id == "unit"


@pytest.mark.parametrize("change", ["byte-hash", "size", "fresh-row-asset", "original-missing"])
def test_publication_revalidates_generation_original_before_any_fixture_write(pdf_source, change):
    source = pdf_source
    result = generated_result(source)
    if change == "byte-hash":
        source.original.write_bytes(source.data[:-1] + bytes([source.data[-1] ^ 1]))
    elif change == "size":
        source.original.write_bytes(source.data + b"\n")
    elif change == "fresh-row-asset":
        source.store.rows[DocumentVersion, "version"].document_id = "foreign"
    else:
        source.original.unlink()
    with pytest.raises(AppError) as error:
        sources.persist_result(
            source.store,
            source.request,
            SimpleNamespace(id="authored-answer"),
            result,
            storage_root=source.storage,
        )
    assert error.value.code == (
        "VALIDATION_FAILED" if change == "original-missing" else "EVIDENCE_UNAVAILABLE"
    )
    assert not source.store.added and source.store.flushes == 0
    assert source.store.refreshed(DocumentVersion, "version") == 2


def test_publication_without_original_storage_cannot_reuse_generation_caption_hint(pdf_source):
    source = pdf_source
    result = generated_result(source)
    with pytest.raises(AppError) as error:
        sources.persist_result(
            source.store, source.request, SimpleNamespace(id="authored-answer"), result
        )
    assert error.value.code == "VALIDATION_FAILED" and not source.store.added


def test_native_answering_generation_and_publication_hooks_supply_the_same_storage_setting():
    from app.modules.answering import service

    tree = ast.parse(inspect.getsource(service))
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    source_calls = [
        node
        for node in calls
        if (isinstance(node.func, ast.Name) and node.func.id == "source_map")
        or (isinstance(node.func, ast.Attribute) and node.func.attr == "persist_result")
    ]
    # Initial generation, continuation generation, and publication all bind the same root.
    assert len(source_calls) == 3
    for call in source_calls:
        setting = next(keyword.value for keyword in call.keywords if keyword.arg == "storage_root")
        assert isinstance(setting, ast.Attribute) and setting.attr == "storage_root"
        assert isinstance(setting.value, ast.Name) and setting.value.id == "settings"
