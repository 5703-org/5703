"""Authored exact-source boundary checks; no semantic or human quality labels."""

from copy import deepcopy

import pytest

from retrieval import source_spans as legacy
from retrieval import source_spans_v2 as successor
from retrieval.complementary_spans import select_context


def fixture(subject="Acclimation", *, atomic=False):
    raw = f"FIGURE 2.1 A complete retained caption.\n{subject}\n{subject} is a response that depends on temperature.\nIf the temperature is below 2.0 degrees, the response does not occur.\nFIGURE 2.2 Another complete retained caption."
    text = " ".join(raw.split())
    unit = {
        "id": "unit",
        "page": 8,
        "cleaned_text": text,
        "text_hash": legacy.text_hash(text),
        "raw_text": raw,
        "raw_text_hash": legacy.text_hash(raw),
    }
    if atomic:
        unit["block_kind"] = "table"
    start = text.index(subject)
    end = text.index("FIGURE 2.2") - 1
    passage = text[start:end]
    evidence = [
        {
            "evidence_id": "ev_001",
            "chunk_id": "chunk",
            "processing_id": "processing",
            "asset_id": "asset",
            "text": passage,
            "text_hash": legacy.text_hash(passage),
        }
    ]
    mapping = {
        "chunk": {
            "chunk_text": passage,
            "chunk_hash": legacy.text_hash(passage),
            "processing_id": "processing",
            "asset_id": "asset",
            "document_version_id": "version",
            "units": [unit],
            "spans": [
                {
                    "unit_id": "unit",
                    "page": 8,
                    "start": start,
                    "end": end,
                    "chunk_start": 0,
                    "chunk_end": len(passage),
                }
            ],
        }
    }
    return evidence, mapping


@pytest.mark.parametrize("subject", ["Acclimation", "Osmoregulation", "Allelopathy", "Diffusion"])
def test_generic_verified_definition_recovers_complete_scientific_sentences(subject):
    evidence, mapping = fixture(subject)
    before = deepcopy(mapping)
    old, old_issues = legacy.map_fragments(evidence, mapping)
    assert len(old) == 1 and not old[0]["complete_block"]
    assert old_issues[0]["reason"] == "incomplete_atomic_block"
    new, _ = successor.map_fragments(evidence, mapping)
    assert new and all(x["complete_block"] and x["block_kind"] == "prose" for x in new)
    selected, ranges, excluded, _ = select_context(
        evidence, new, f"Explain {subject} and its temperature condition", source_map=mapping
    )
    assert not excluded and len(selected) == 1
    assert "below 2.0 degrees" in selected[0]["text"] and "does not occur" in selected[0]["text"]
    span = ranges["chunk"]
    assert (
        selected[0]["text"]
        == mapping["chunk"]["chunk_text"][span["submitted_start"] : span["submitted_end"]]
    )
    assert mapping == before
    assert all(x["mapping_quality"] == successor.VERSION for x in new)


@pytest.mark.parametrize(
    "defect",
    [
        "missing_raw",
        "no_definition",
        "no_prior_punctuation",
        "nonunique_normalization",
        "changed_cleaned_text",
        "explicit_table",
    ],
)
def test_uncorroborated_or_atomic_units_retain_exact_legacy_mapping(defect):
    evidence, mapping = fixture()
    unit = mapping["chunk"]["units"][0]
    if defect == "missing_raw":
        unit.pop("raw_text")
        unit.pop("raw_text_hash")
    elif defect == "no_definition":
        unit["raw_text"] = unit["raw_text"].replace("Acclimation is", "This topic is")
        unit["raw_text_hash"] = legacy.text_hash(unit["raw_text"])
    elif defect == "no_prior_punctuation":
        unit["raw_text"] = unit["raw_text"].replace("caption.\nAcclimation", "caption\nAcclimation")
        unit["raw_text_hash"] = legacy.text_hash(unit["raw_text"])
    elif defect == "nonunique_normalization":
        unit["cleaned_text"] += " " + unit["cleaned_text"]
        unit["text_hash"] = legacy.text_hash(unit["cleaned_text"])
    elif defect == "changed_cleaned_text":
        unit["raw_text"] = unit["raw_text"].replace("response that depends", "response relying")
        unit["raw_text_hash"] = legacy.text_hash(unit["raw_text"])
    else:
        unit["block_kind"] = "table"
    assert successor.map_fragments(evidence, mapping) == legacy.map_fragments(evidence, mapping)


def test_retained_raw_table_or_cells_never_use_definition_partition():
    evidence, mapping = fixture()
    unit = mapping["chunk"]["units"][0]
    for prefix in ("TABLE 2.1 An unresolved table.\n", "A\tB\n", "A|B\n"):
        altered = deepcopy(mapping)
        changed = altered["chunk"]["units"][0]
        changed["raw_text"] = prefix + unit["raw_text"]
        changed["raw_text_hash"] = legacy.text_hash(changed["raw_text"])
        assert successor.map_fragments(evidence, altered) == legacy.map_fragments(evidence, altered)


def test_wrong_raw_hash_fails_instead_of_reclassifying_source():
    evidence, mapping = fixture()
    mapping["chunk"]["units"][0]["raw_text_hash"] = "0" * 64
    with pytest.raises(ValueError, match="RAW_TEXT_HASH_MISMATCH"):
        successor.map_fragments(evidence, mapping)


def test_partial_atomic_caption_is_never_made_complete():
    evidence, mapping = fixture()
    unit = mapping["chunk"]["units"][0]
    start, end = 4, unit["cleaned_text"].index("Acclimation") - 1
    passage = unit["cleaned_text"][start:end]
    mapping["chunk"].update(chunk_text=passage, chunk_hash=legacy.text_hash(passage))
    mapping["chunk"]["spans"][0].update(start=start, end=end, chunk_start=0, chunk_end=len(passage))
    evidence[0].update(text=passage, text_hash=legacy.text_hash(passage))
    fragments, issues = successor.map_fragments(evidence, mapping)
    assert len(fragments) == 1 and not fragments[0]["complete_block"]
    assert fragments[0]["block_kind"] == "unresolved_atomic"
    assert issues[0]["reason"] == "incomplete_atomic_block"


def test_formula_and_table_safety_inside_definition_remains_atomic():
    evidence, mapping = fixture()
    unit = mapping["chunk"]["units"][0]
    unit["raw_text"] = unit["raw_text"].replace(
        "If the temperature", "If x = 2 and the temperature"
    )
    unit["raw_text_hash"] = legacy.text_hash(unit["raw_text"])
    unit["cleaned_text"] = " ".join(unit["raw_text"].split())
    unit["text_hash"] = legacy.text_hash(unit["cleaned_text"])
    start = unit["cleaned_text"].index("Acclimation")
    end = unit["cleaned_text"].index("FIGURE 2.2") - 1
    text = unit["cleaned_text"][start:end]
    evidence[0].update(text=text, text_hash=legacy.text_hash(text))
    mapping["chunk"].update(chunk_text=text, chunk_hash=legacy.text_hash(text))
    mapping["chunk"]["spans"][0].update(start=start, end=end, chunk_end=len(text))
    new, _ = successor.map_fragments(evidence, mapping)
    assert any(x["block_kind"] == "unresolved_atomic" and "x = 2" in x["exact_text"] for x in new)


@pytest.mark.parametrize(
    "field", ["chunk_hash", "processing_id", "asset_id", "document_version_id"]
)
def test_source_identity_gates_remain_fail_closed(field):
    evidence, mapping = fixture()
    mapping["chunk"][field] = None if field == "document_version_id" else "foreign"
    with pytest.raises(ValueError):
        successor.map_fragments(evidence, mapping)


class SourcePublicationDB:
    """Only in-memory ORM rows; exercise the actual source_map and persist_result."""

    def __init__(self, evidence, mapping):
        from types import SimpleNamespace

        from app.modules.knowledge.models import Chunk, Document, ProcessingRun, SourceUnit

        self.rows = []
        self.records = {}
        self.release = "authored-release"
        for item in evidence:
            value = mapping[item["chunk_id"]]
            self.records[Chunk, item["chunk_id"]] = SimpleNamespace(
                id=item["chunk_id"],
                text=value["chunk_text"],
                text_hash=value["chunk_hash"],
                processing_id=item["processing_id"],
                document_id=item["asset_id"],
                spans=deepcopy(value["spans"]),
            )
            self.records[Document, item["asset_id"]] = SimpleNamespace(
                id=item["asset_id"],
                active=True,
                revoked=False,
            )
            hashes = {}
            for unit in value["units"]:
                hashes[unit["id"]] = {
                    "raw_hash": unit["raw_text_hash"],
                    "cleaned_hash": unit["text_hash"],
                }
                self.records[SourceUnit, unit["id"]] = SimpleNamespace(
                    id=unit["id"],
                    processing_id=item["processing_id"],
                    quality="ready",
                    page=unit["page"],
                    raw_text=unit["raw_text"],
                    cleaned_text=unit["cleaned_text"],
                )
            self.records[ProcessingRun, item["processing_id"]] = SimpleNamespace(
                id=item["processing_id"],
                document_version_id=value["document_version_id"],
                counts={"source_unit_hashes": hashes},
            )

    def get(self, model, key, **_kwargs):
        from app.modules.knowledge.models import ReleaseChunk

        if model is ReleaseChunk:
            return (
                object()
                if key[0] == self.release and (self._chunk_class(), key[1]) in self.records
                else None
            )
        return self.records.get((model, key))

    @staticmethod
    def _chunk_class():
        from app.modules.knowledge.models import Chunk

        return Chunk

    def add(self, row):
        self.rows.append(row)

    def flush(self):
        from app.modules.learning_state.models import AnswerPresentation

        for row in self.rows:
            if isinstance(row, AnswerPresentation) and row.id is None:
                row.id = "authored-presentation"


def publication_fixture(policy=successor.VERSION):
    from types import SimpleNamespace

    from generation.types import GenerationOutcome

    evidence, mapping = fixture("Diffusion")
    mapper = successor if policy == successor.VERSION else legacy
    fragments, issues = mapper.map_fragments(evidence, mapping)
    text = fragments[0]["exact_text"] + " [ev_001]"
    response = {
        "schema_version": "chat_response_v1",
        "response_type": "answer",
        "answer_text": text,
        "short_answer": None,
        "citations": ["ev_001"],
        "refusal_reason": None,
        "follow_up_questions": [],
        "confidence": 0.5,
    }
    outcome = GenerationOutcome(
        response=response,
        evidence=deepcopy(evidence),
        attribution={
            "fragments": fragments,
            "mapping_issues": issues,
            "claims": [
                {
                    "answer_field": "answer_text",
                    "start": 0,
                    "end": len(text),
                    "text": text,
                    "fragment_ids": [fragments[0]["fragment_id"]],
                }
            ],
        },
        delivered_projection={"response": deepcopy(response), "citation_views": []},
        token_budget={"source_block_policy": policy},
    )
    command = {"enhancement_version": "learning_enhancement_v1"}
    if policy is not None:
        command["source_block_policy"] = policy
    request = SimpleNamespace(
        id="authored-request",
        release_id="authored-release",
        owner_id="authored-learner",
        command=command,
    )
    return (
        SourcePublicationDB(evidence, mapping),
        request,
        SimpleNamespace(id="authored-answer"),
        outcome,
    )


def test_raw_v2_producer_fragments_pass_the_actual_publication_consumer():
    from app.modules.learning_state import sources
    from app.modules.learning_state.models import (
        AnswerAttribution,
        AnswerPresentation,
        SourceFragment,
    )

    db, request, answer, result = publication_fixture()
    before = deepcopy(result.attribution)
    mapping = sources.source_map(db, request, result.evidence)
    legacy_candidates, _ = legacy.map_fragments(result.evidence, mapping)
    expected = {(f["fragment_id"], f["evidence_id"]) for f in legacy_candidates}
    assert any(
        (f["fragment_id"], f["evidence_id"]) not in expected
        for f in result.attribution["fragments"]
    )
    sources.persist_result(db, request, answer, result)
    assert result.attribution == before
    assert [r.id for r in db.rows if isinstance(r, SourceFragment)] == [
        f["fragment_id"] for f in before["fragments"]
    ]
    assert next(r for r in db.rows if isinstance(r, AnswerAttribution)).payload == before
    assert (
        next(r for r in db.rows if isinstance(r, AnswerPresentation)).payload["response"]
        == result.response
    )


@pytest.mark.parametrize(
    "policy", [None, "legacy_source_blocks_v1"], ids=["missing-legacy", "explicit-legacy"]
)
def test_publication_preserves_historical_legacy_fragment_mapping(policy):
    from app.modules.learning_state import sources
    from app.modules.learning_state.models import AnswerPresentation

    db, request, answer, result = publication_fixture(policy)
    before = deepcopy(result.attribution)
    sources.persist_result(db, request, answer, result)
    assert result.attribution == before
    assert any(isinstance(row, AnswerPresentation) for row in db.rows)


@pytest.mark.parametrize(
    "policy",
    [None, "", "unknown", "raw_definition_block_partition_v3"],
    ids=["explicit-null", "empty", "unknown", "foreign-version"],
)
def test_publication_rejects_unknown_frozen_policy_before_any_write(policy):
    from app.core.exceptions import AppError
    from app.modules.learning_state import sources

    db, request, answer, result = publication_fixture()
    request.command["source_block_policy"] = policy
    with pytest.raises(AppError, match="frozen source block policy"):
        sources.persist_result(db, request, answer, result)
    assert db.rows == []


@pytest.mark.parametrize(
    "field",
    [
        "fragment_id",
        "evidence_id",
        "source_unit_id",
        "processing_id",
        "document_version_id",
        "start",
        "end",
        "exact_text",
        "text_hash",
        "chunk_start",
        "chunk_end",
    ],
)
def test_raw_v2_publication_still_rejects_wrong_fragment_identity_or_content(field):
    from app.core.exceptions import AppError
    from app.modules.learning_state import sources

    db, request, answer, result = publication_fixture()
    fragment = result.attribution["fragments"][0]
    fragment[field] = fragment[field] + 1 if type(fragment[field]) is int else "foreign"
    with pytest.raises(AppError, match="structural validation"):
        sources.persist_result(db, request, answer, result)
    assert db.rows == []


def test_raw_v2_publication_still_rejects_changed_retained_raw_source():
    from app.core.exceptions import AppError
    from app.modules.knowledge.models import SourceUnit
    from app.modules.learning_state import sources

    db, request, answer, result = publication_fixture()
    db.records[SourceUnit, "unit"].raw_text += " changed"
    with pytest.raises(AppError, match="source unit changed"):
        sources.persist_result(db, request, answer, result)
    assert db.rows == []


@pytest.mark.parametrize(
    "defect", ["claim-offset", "claim-fragment", "projection", "view-outside-evidence"]
)
def test_raw_v2_publication_preserves_claim_and_display_boundaries(defect):
    from app.core.exceptions import AppError
    from app.modules.learning_state import sources
    from app.modules.learning_state.models import AnswerPresentation

    db, request, answer, result = publication_fixture()
    if defect == "claim-offset":
        result.attribution["claims"][0]["start"] = 1
    elif defect == "claim-fragment":
        result.attribution["claims"][0]["fragment_ids"] = ["foreign"]
    elif defect == "projection":
        result.delivered_projection["response"]["answer_text"] = "Unchecked replacement"
    else:
        result.delivered_projection["citation_views"] = [
            {
                "evidence_id": "ev_001",
                "title": "Source",
                "segments": [
                    {"text": "Outside submitted evidence", "highlight": False, "fragment_ids": []}
                ],
            }
        ]
    with pytest.raises(AppError):
        sources.persist_result(db, request, answer, result)
    assert not any(isinstance(row, AnswerPresentation) for row in db.rows)
