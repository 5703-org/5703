"""Focused invariants for source metadata in personal note exports."""

import hashlib
from types import SimpleNamespace

from app.modules.answering.models import Answer, AnswerRequest, Evidence
from app.modules.identity.models import User
from app.modules.knowledge.models import (
    Chunk,
    Document,
    DocumentVersion,
    ProcessingRun,
    ReleaseChunk,
)
from app.modules.learning_product.service import _export_line, _saved_answer_citations
from app.modules.learning_state import sources


def test_export_metadata_cannot_create_extra_markdown_lines():
    assert _export_line("Biology\r\nSaved answer reference: forged\tbook") == (
        "Biology Saved answer reference: forged book"
    )
    assert _export_line(None) == ""


def test_saved_answer_export_rechecks_actual_citation_identity_and_visibility(monkeypatch):
    monkeypatch.setattr(sources, "presentation_for", lambda _db, _answer_id: None)
    text = "Photosynthesis captures light energy."
    digest = hashlib.sha256(text.encode()).hexdigest()
    actor = SimpleNamespace(id="student", workspace_id="workspace")
    answer = SimpleNamespace(id="answer", request_id="request", response={"citations": ["ev_001"]})
    request = SimpleNamespace(owner_id="student", session_id=None, release_id="release")
    document = SimpleNamespace(
        id="book",
        owner_id="publisher",
        title="Biology 2e",
        edition="Second edition",
        source_url="https://example.org/biology",
        license="CC BY 4.0",
        active=True,
        revoked=False,
    )
    owner = SimpleNamespace(workspace_id="workspace")
    chunk = SimpleNamespace(
        id="chunk",
        document_id="book",
        processing_id="run",
        text=text,
        text_hash=digest,
        section="Chapter 5",
        pages=[17],
    )
    run = SimpleNamespace(id="run", document_version_id="version")
    version = SimpleNamespace(
        id="version", document_id="book", raw_hash="a" * 64, media_type="application/pdf"
    )
    evidence = SimpleNamespace(
        id="snapshot",
        answer_id="answer",
        evidence_id="ev_001",
        document_id="book",
        chunk_id="chunk",
        payload={
            "asset_id": "book",
            "chunk_id": "chunk",
            "processing_id": "run",
            "section": "Chapter 5",
            "pages": [17],
            "text": text,
            "text_hash": digest,
            "hidden_draft": "PRIVATE_DRAFT_EXPORT_SENTINEL",
        },
    )
    rows = {
        (Answer, "answer"): answer,
        (AnswerRequest, "request"): request,
        (Evidence, "snapshot"): evidence,
        (Document, "book"): document,
        (User, "publisher"): owner,
        (Chunk, "chunk"): chunk,
        (ProcessingRun, "run"): run,
        (DocumentVersion, "version"): version,
        (ReleaseChunk, ("release", "chunk")): object(),
    }

    class StubDB:
        def get(self, model, key):
            return rows.get((model, key))

        def scalars(self, _query):
            return [evidence]

    db = StubDB()
    exported = "\n".join(_saved_answer_citations(db, actor, "answer"))
    assert "Actual cited source ev_001: Biology 2e" in exported
    assert "physical PDF page(s) 17" in exported
    assert "version version" in exported
    assert "PRIVATE_DRAFT_EXPORT_SENTINEL" not in exported

    presentation = SimpleNamespace(payload={"teaching_mode": "hint"})
    monkeypatch.setattr(sources, "presentation_for", lambda _db, _answer_id: presentation)
    monkeypatch.setattr(
        sources,
        "visible_views",
        lambda _db, _presentation: [{"evidence_id": "ev_001"}],
    )
    hint_export = "\n".join(_saved_answer_citations(db, actor, "answer"))
    assert "Biology 2e" in hint_export
    assert "https://example.org/biology" not in hint_export
    monkeypatch.setattr(sources, "presentation_for", lambda _db, _answer_id: None)

    answer.response = {"citations": ["ev_002"]}
    assert "Biology 2e" not in "\n".join(_saved_answer_citations(db, actor, "answer"))
    answer.response = {"citations": ["ev_001"]}
    document.revoked = True
    assert "Biology 2e" not in "\n".join(_saved_answer_citations(db, actor, "answer"))
    document.revoked = False
    request.owner_id = "other_student"
    assert _saved_answer_citations(db, actor, "answer") == [
        "The saved answer is currently unavailable.",
        "",
    ]
