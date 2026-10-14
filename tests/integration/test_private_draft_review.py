"""Local draft inspection never exposes unrestricted stored provider payloads."""

import json
from sqlalchemy import select

from app.modules.answering.models import AnswerRequest
from app.modules.identity.models import User, Workspace
from app.modules.knowledge.models import Chunk, Document
from app.modules.learning.models import ChatSession
from app.modules.learning_state.models import PrivateAnswerDraft
from .test_chat_runtime import call, corpus, finish, session, submit


def _saved(rt):
    document, _ = corpus(rt)
    chat = session(rt)
    receipt = submit(rt, chat)
    finish(rt, receipt)
    with rt.db() as db:
        req = db.get(AnswerRequest, receipt["request_id"])
        chunk = db.scalar(select(Chunk).where(Chunk.document_id == document["id"]))
        req.trace = {
            "evidence_selection": {
                "submitted_evidence_ids": ["ev_local"],
                "submitted_chunk_ids": [chunk.id],
            }
        }
        db.add(
            PrivateAnswerDraft(
                request_id=req.id,
                phase="generated_draft",
                payload={
                    "revision": 77,
                    "response": {"answer_text": "A saved draft. API_KEY=never-expose-this-value"},
                    "raw_model_output": "private-provider-payload",
                    "rubric": "private-answer-key",
                    "memory_contents": "private-memory",
                    "projection": {
                        "citation_views": [
                            {
                                "evidence_id": "ev_local",
                                "source_title": "untrusted stored title",
                                "segments": [{"text": chunk.text}],
                            }
                        ]
                    },
                },
            )
        )
        db.add(
            PrivateAnswerDraft(
                request_id=req.id,
                phase="online_check",
                payload={"raw_text": "private-checker-answer-key"},
            )
        )
        db.commit()
        return req.id, chat["id"], document["id"], chunk.id


def _review(rt, request_id, status=200):
    return call(
        rt,
        "GET",
        f"/admin/failures/{request_id}/drafts",
        headers=rt.headers("admin@example.com"),
        status=status,
    )


def test_local_draft_allowlist_and_live_provenance(runtime):
    rt = runtime
    request_id, _, document_id, chunk_id = _saved(rt)
    response = _review(rt, request_id)
    text = json.dumps(response)
    for secret in (
        "never-expose-this-value",
        "private-provider-payload",
        "private-answer-key",
        "private-memory",
        "private-checker-answer-key",
        "untrusted stored title",
    ):
        assert secret not in text
    draft = next(d for d in response["items"] if d["revision"] == 77)
    assert draft["source_status"] == "validated"
    assert draft["sources"][0]["chunk_id"] == chunk_id
    with rt.db() as db:
        doc = db.get(Document, document_id)
        doc.revoked = True
        db.commit()
    draft = next(d for d in _review(rt, request_id)["items"] if d["revision"] == 77)
    assert draft["source_status"] == "source_unavailable"
    assert draft["withheld_source_count"] == 1 and not draft["sources"]


def test_draft_review_role_workspace_deleted_and_active_scope(runtime):
    rt = runtime
    request_id, chat_id, _, _ = _saved(rt)
    call(rt, "GET", f"/admin/failures/{request_id}/drafts", status=403)
    with rt.db() as db:
        req = db.get(AnswerRequest, request_id)
        req.state = "running"
        db.commit()
    _review(rt, request_id, 409)
    with rt.db() as db:
        req = db.get(AnswerRequest, request_id)
        req.state = "answered"
        actor = db.scalar(select(User).where(User.email == "admin@example.com"))
        original_workspace = actor.workspace_id
        workspace = Workspace(name="Separate inspector", slug="draft-inspector-other")
        db.add(workspace)
        db.flush()
        actor.workspace_id = workspace.id
        db.commit()
    _review(rt, request_id, 404)
    with rt.db() as db:
        actor = db.scalar(select(User).where(User.email == "admin@example.com"))
        actor.workspace_id = original_workspace
        chat = db.get(ChatSession, chat_id)
        chat.deleted_at = actor.created_at
        db.commit()
    _review(rt, request_id, 404)


def test_draft_review_does_not_guess_missing_binding_or_allow_changed_source(runtime):
    rt = runtime
    request_id, _, _, chunk_id = _saved(rt)
    with rt.db() as db:
        chunk = db.get(Chunk, chunk_id)
        original_text = chunk.text
        chunk.text = "Changed source bytes"
        db.commit()
    draft = next(d for d in _review(rt, request_id)["items"] if d["revision"] == 77)
    assert draft["source_status"] == "source_unavailable" and not draft["sources"]
    with rt.db() as db:
        db.get(Chunk, chunk_id).text = original_text
        db.get(AnswerRequest, request_id).trace = {}
        db.commit()
    draft = next(d for d in _review(rt, request_id)["items"] if d["revision"] == 77)
    assert draft["source_status"] == "incomplete_binding" and not draft["sources"]
