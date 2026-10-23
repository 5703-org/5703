"""Fresh source-map reads are unique per validation and refresh at publication."""

from collections import Counter
from copy import deepcopy
import hashlib
from types import SimpleNamespace

import pytest

from app.core.exceptions import AppError
from app.modules.knowledge.models import Chunk, Document, ProcessingRun, ReleaseChunk, SourceUnit
from app.modules.learning_state import sources


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class CountingSourceStore:
    """Return independent current records and record real source-read requests."""

    def __init__(self, records):
        self.records = records
        self.reads = []

    def get(self, model, identifier, **kwargs):
        self.reads.append((model, identifier, kwargs))
        return deepcopy(self.records.get((model, identifier)))

    def fresh_reads(self):
        return Counter(
            (model, identifier)
            for model, identifier, kwargs in self.reads
            if kwargs.get("populate_existing") is True
        )


def source_fixture():
    units = {
        "unit-shared": SimpleNamespace(
            id="unit-shared",
            processing_id="run",
            quality="ready",
            page=2,
            raw_text="Publisher heading\nWater crosses the membrane.",
            cleaned_text="Water crosses the membrane.",
        ),
        "unit-first": SimpleNamespace(
            id="unit-first",
            processing_id="run",
            quality="ready",
            page=3,
            raw_text="Water enters cells.\n",
            cleaned_text="Water enters cells.",
        ),
        "unit-second": SimpleNamespace(
            id="unit-second",
            processing_id="run",
            quality="ready",
            page=4,
            raw_text="The source remains exact.\n",
            cleaned_text="The source remains exact.",
        ),
    }
    chunks = {
        "chunk-a": ["unit-shared", "unit-first", "unit-shared"],
        "chunk-b": ["unit-shared", "unit-second"],
        "chunk-c": ["unit-shared"],
    }
    records = {
        (Document, "book"): SimpleNamespace(id="book", active=True, revoked=False),
        (ProcessingRun, "run"): SimpleNamespace(
            id="run",
            document_version_id="version",
            counts={
                "source_unit_hashes": {
                    uid: {
                        "raw_hash": sha256(unit.raw_text),
                        "cleaned_hash": sha256(unit.cleaned_text),
                    }
                    for uid, unit in units.items()
                }
            },
        ),
        **{(SourceUnit, uid): unit for uid, unit in units.items()},
    }
    for chunk_id, unit_ids in chunks.items():
        text = "\n".join(units[uid].cleaned_text for uid in dict.fromkeys(unit_ids))
        records[Chunk, chunk_id] = SimpleNamespace(
            id=chunk_id,
            processing_id="run",
            document_id="book",
            text=text,
            text_hash=sha256(text),
            spans=[{"unit_id": uid} for uid in unit_ids],
        )
        records[ReleaseChunk, ("release", chunk_id)] = SimpleNamespace(chunk_id=chunk_id)
    evidence = [
        {"chunk_id": chunk_id, "asset_id": "book", "processing_id": "run"} for chunk_id in chunks
    ]
    # Multiple submitted ranges can reference the same released chunk.
    evidence.append({**evidence[0], "chunk_start": 2, "chunk_end": 12})
    return CountingSourceStore(records), SimpleNamespace(release_id="release"), evidence


def expected_mapping(db):
    expected = {}
    for chunk_id, unit_ids in (
        ("chunk-a", ["unit-shared", "unit-first"]),
        ("chunk-b", ["unit-shared", "unit-second"]),
        ("chunk-c", ["unit-shared"]),
    ):
        chunk = db.records[Chunk, chunk_id]
        expected[chunk_id] = {
            "document_version_id": "version",
            "processing_id": "run",
            "asset_id": "book",
            "chunk_text": chunk.text,
            "chunk_hash": chunk.text_hash,
            "spans": deepcopy(chunk.spans),
            "units": [
                {
                    "id": uid,
                    "page": db.records[SourceUnit, uid].page,
                    "cleaned_text": db.records[SourceUnit, uid].cleaned_text,
                    "text_hash": sha256(db.records[SourceUnit, uid].cleaned_text),
                    "raw_text": db.records[SourceUnit, uid].raw_text,
                    "raw_text_hash": sha256(db.records[SourceUnit, uid].raw_text),
                }
                for uid in unit_ids
            ],
        }
    expected["chunk-a"].update(submitted_start=2, submitted_end=12)
    return expected


def test_shared_sources_are_freshly_read_once_with_complete_identical_mapping():
    db, request, evidence = source_fixture()
    mapping = sources.source_map(db, request, evidence)
    assert mapping == expected_mapping(db)
    assert list(mapping) == ["chunk-a", "chunk-b", "chunk-c"]
    assert db.fresh_reads() == Counter(
        {
            (Chunk, "chunk-a"): 1,
            (Chunk, "chunk-b"): 1,
            (Chunk, "chunk-c"): 1,
            (Document, "book"): 1,
            (ProcessingRun, "run"): 1,
            (SourceUnit, "unit-shared"): 1,
            (SourceUnit, "unit-first"): 1,
            (SourceUnit, "unit-second"): 1,
        }
    )
    memberships = [identifier for model, identifier, kwargs in db.reads if model is ReleaseChunk]
    assert memberships == [("release", ev["chunk_id"]) for ev in evidence]
    assert all(kwargs == {} for model, identifier, kwargs in db.reads if model is ReleaseChunk)
    mapping["chunk-a"]["spans"][0]["unit_id"] = "foreign"
    assert db.records[Chunk, "chunk-a"].spans[0]["unit_id"] == "unit-shared"


def test_generation_and_publication_each_refresh_all_selected_sources():
    db, request, evidence = source_fixture()
    generated_mapping = sources.source_map(db, request, evidence)
    published_mapping = sources.source_map(db, request, evidence)
    assert generated_mapping == published_mapping == expected_mapping(db)
    assert set(db.fresh_reads().values()) == {2}
    assert sum(db.fresh_reads().values()) == 16


@pytest.mark.parametrize(
    "model, identifier, attribute, value, changed_hash",
    [
        (Chunk, "chunk-a", None, None, False),
        (Document, "book", None, None, False),
        (ProcessingRun, "run", None, None, False),
        (SourceUnit, "unit-first", None, None, False),
        (ReleaseChunk, ("release", "chunk-a"), None, None, False),
        (Document, "book", "active", False, False),
        (Document, "book", "revoked", True, False),
        (Chunk, "chunk-a", "processing_id", "foreign-run", False),
        (Chunk, "chunk-a", "document_id", "foreign-book", False),
        (SourceUnit, "unit-first", "processing_id", "foreign-run", False),
        (SourceUnit, "unit-first", "quality", "rejected", False),
        (SourceUnit, "unit-first", "raw_text", "Changed raw source.", True),
        (SourceUnit, "unit-first", "cleaned_text", "Changed cleaned source.", True),
        (
            ProcessingRun,
            "run",
            "counts",
            {"source_unit_hashes": {"unit-shared": {"raw_hash": "bad", "cleaned_hash": "bad"}}},
            True,
        ),
    ],
    ids=[
        "missing-chunk",
        "missing-document",
        "missing-processing-run",
        "missing-selected-source-unit",
        "removed-release-membership",
        "inactive-document",
        "revoked-document",
        "changed-chunk-processing",
        "changed-chunk-document",
        "changed-unit-processing",
        "unready-source-unit",
        "changed-raw-source",
        "changed-cleaned-source",
        "changed-processing-hashes",
    ],
)
def test_next_validation_rejects_source_changes(model, identifier, attribute, value, changed_hash):
    db, request, evidence = source_fixture()
    sources.source_map(db, request, evidence)
    if attribute is None:
        db.records.pop((model, identifier))
    else:
        setattr(db.records[model, identifier], attribute, value)
    with pytest.raises(AppError) as failure:
        sources.source_map(db, request, evidence)
    assert failure.value.code == "EVIDENCE_UNAVAILABLE"
    if changed_hash:
        assert failure.value.detail == "A selected source unit changed."
    else:
        assert failure.value.detail is None
    if model is not ReleaseChunk:
        assert db.fresh_reads()[model, identifier] == 2


def test_new_store_with_same_identifiers_cannot_reuse_previous_validation():
    first_db, request, evidence = source_fixture()
    sources.source_map(first_db, request, evidence)
    second_db, _, _ = source_fixture()
    second_db.records[Document, "book"].revoked = True
    with pytest.raises(AppError) as failure:
        sources.source_map(second_db, request, evidence)
    assert failure.value.code == "EVIDENCE_UNAVAILABLE"
    assert second_db.fresh_reads()[Document, "book"] == 1


def test_empty_evidence_needs_no_source_reads():
    db, request, _ = source_fixture()
    assert sources.source_map(db, request, []) == {}
    assert db.reads == []
