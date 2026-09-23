"""Create an explicitly authored UI stress fixture through persisted app entities.

This fixture tests rendering/history/revision recovery, not generation quality.
It reuses only an existing authorized evidence snapshot with its exact hash.
"""

import copy
import json
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from app.core.config import Settings
from app.db.session import init_engine
from app.db.base import new_uuid
from app.modules.identity.repository import get_user_by_email
from app.modules.learning.models import ChatSession
from app.modules.answering.models import (
    AnswerRequest,
    Answer,
    Message,
    Snapshot,
    Evidence,
    Citation,
    Job,
    Feedback,
)
from app.modules.knowledge.service import digest


def main():
    settings = Settings()
    if settings.env not in ("dev", "test", "demo") or settings.model_mode != "mock":
        raise SystemExit("UI stress fixtures require explicit local mock development mode")
    engine = init_engine(settings.database_url)
    with sessionmaker(bind=engine, expire_on_commit=False)() as db:
        user = get_user_by_email(db, "student2@example.com")
        source = db.scalar(select(Evidence).order_by(Evidence.created_at))
        if not user or not source:
            raise SystemExit("Run the authored corpus/chat fixture first")
        s = ChatSession(
            user_id=user.id,
            workspace_id=user.workspace_id,
            title="UI stress fixture — long content and failed latest regeneration "
            + ("long conversation title " * 12),
        )
        s.title = s.title[:200]
        db.add(s)
        db.flush()
        u = Message(
            session_id=s.id,
            sequence=1,
            role="user",
            state="completed",
            content="Show the authored long-content rendering fixture.",
        )
        db.add(u)
        db.flush()
        paragraphs = "\n\n".join(
            f"Paragraph {i + 1}. This authored regression text verifies that a long answer remains readable, that scrolling reaches every paragraph, and that resizing preserves this conversation. [ev_001]"
            for i in range(35)
        )
        long_url = "https://example.com/" + ("long-path-" * 80)
        text = (
            paragraphs
            + "\n\n- First accessible list item\n- Second accessible list item\n\n"
            + long_url
            + "\n\n"
            + ("unbrokenword" * 100)
            + "\n\n```python\n"
            + ('long_variable_name = "local scrolling preserves every character"; ' * 30)
            + "\n```\n\n|"
            + "|".join("Column " + str(i) for i in range(16))
            + "|\n|"
            + "|".join("---" for _ in range(16))
            + "|\n|"
            + "|".join("Cell text " + str(i) for i in range(16))
            + "|\n\n$$ E = mc^2 $$\n\nFinal reachable paragraph. This is an authored UI fixture, not a measured model answer. [ev_001]"
        )
        assistant = Message(
            session_id=s.id, sequence=2, role="assistant", state="completed", content=text
        )
        db.add(assistant)
        db.flush()
        context = Snapshot(
            owner_id=user.id,
            session_id=s.id,
            kind="conversation",
            payload={
                "session_id": s.id,
                "cutoff_sequence": 0,
                "messages": [],
                "summary_id": None,
                "summary_hash": None,
                "covered_until_sequence": None,
                "summary_text": None,
                "profile_snapshot_id": None,
                "token_budget": {},
                "exclusions": [],
            },
            content_hash=digest({}),
        )
        db.add(context)
        db.flush()
        req = AnswerRequest(
            owner_id=user.id,
            route="ui-stress-fixture",
            idempotency_key=new_uuid(),
            body_hash=digest({}),
            mode="interactive_chat",
            response_schema="chat_response_v1",
            state="answered",
            session_id=s.id,
            user_message_id=u.id,
            assistant_message_id=assistant.id,
            context_snapshot_id=context.id,
            command={"question": u.content},
            budget={},
            trace={"fixture_kind": "authored_ui_stress", "not_generation_evidence": True},
        )
        db.add(req)
        db.flush()
        job = Job(owner_id=user.id, request_id=req.id, state="succeeded", stage="complete")
        db.add(job)
        db.flush()
        response = {
            "schema_version": "chat_response_v1",
            "response_type": "answer",
            "answer_text": text,
            "short_answer": "Authored UI rendering fixture",
            "citations": ["ev_001"],
            "refusal_reason": None,
            "follow_up_questions": [],
            "confidence": None,
        }
        answer = Answer(
            request_id=req.id,
            job_id=job.id,
            message_id=assistant.id,
            response_schema="chat_response_v1",
            response=response,
            model_mode="mock",
            timing={"fixture": True},
        )
        db.add(answer)
        db.flush()
        payload = copy.deepcopy(source.payload)
        payload["evidence_id"] = "ev_001"
        payload["context_order"] = 1
        ev = Evidence(
            answer_id=answer.id,
            evidence_id="ev_001",
            document_id=source.document_id,
            chunk_id=source.chunk_id,
            payload=payload,
        )
        db.add(ev)
        db.flush()
        db.add(Citation(answer_id=answer.id, evidence_id=ev.id))
        feedback = Feedback(
            answer_id=answer.id,
            owner_id=user.id,
            helpful=True,
            comment="Keep this original feedback when a replacement fails.",
        )
        db.add(feedback)
        assistant.active_answer_id = answer.id
        assistant.request_id = req.id
        u.request_id = req.id
        job.answer_id = answer.id
        failed = AnswerRequest(
            owner_id=user.id,
            route="ui-stress-regeneration",
            idempotency_key=new_uuid(),
            body_hash=digest({}),
            mode="interactive_chat",
            response_schema="chat_response_v1",
            state="error",
            session_id=s.id,
            user_message_id=u.id,
            assistant_message_id=assistant.id,
            context_snapshot_id=context.id,
            regeneration_of=answer.id,
            command={"question": u.content},
            budget={},
            trace={"fixture_kind": "authored_ui_stress_failure"},
        )
        db.add(failed)
        db.flush()
        failure = Job(
            owner_id=user.id,
            request_id=failed.id,
            state="failed",
            stage="failed",
            error={
                "code": "PROVIDER_TIMEOUT",
                "message": "Authored UI fixture: replacement timed out; original answer is retained.",
                "details": {"fixture": True},
            },
        )
        db.add(failure)
        db.commit()
        result = {
            "fixture_kind": "authored_ui_stress_not_generation_evidence",
            "session_id": s.id,
            "answer_id": answer.id,
            "feedback_id": feedback.id,
            "failed_regeneration_request_id": failed.id,
            "failed_job_id": failure.id,
            "user": "student2@example.com",
            "url": f"http://127.0.0.1:5173/chat/{s.id}",
        }
        folder = Path("evidence/integration")
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "ui_stress_fixture.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
        print(json.dumps(result))


if __name__ == "__main__":
    main()
