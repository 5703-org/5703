"""Twelve paired observation screens against real production gates.

The ungated condition is an evaluator-only JSON projection. It never writes the
candidate to product memory. Source messages are authored in the disposable DB.
"""

from sqlalchemy import select
from app.core.exceptions import AppError
from app.modules.identity.models import Role, User, Workspace
from app.modules.answering.models import Message
from app.modules.learning_state import memory_v2
from app.modules.learning_state.models import MemoryEntry
from contracts.learning import MemoryAssessmentCreate, MemoryRecordCreate
from evaluation.enhancement.memory_study import Structured
from evaluation.enhancement.protocol import freeze
from evaluation.memory_v2.memory_catalogue import gating_pairs


def execute(engine, settings, config, destination, *, cases=None):
    """Execute no model calls; caller validates the disposable DB boundary."""
    if destination.exists():
        raise ValueError("Observation gates already recorded; choose an explicit new run")
    records = []
    for case in gating_pairs() if cases is None else cases:
        arm = Structured(engine, settings, config, case["id"])
        with arm.db() as db:
            owner = db.get(User, arm.owner_id)
            role = db.scalar(select(Role).where(Role.name == "admin"))
            if role is None:
                role = Role(name="admin", description="Authored assessment fixture actor")
                db.add(role)
                db.flush()
            actor = User(
                email=case["id"].lower() + "-" + owner.id + "@example.com",
                full_name="Authored evaluator fixture",
                hashed_password="disabled-study-login",
                role_id=role.id,
                workspace_id=owner.workspace_id,
            )
            db.add(actor)
            text = case["source_text"]
            question = Message(session_id=arm.session_id, role="user", sequence=1, content=text)
            response = Message(
                session_id=arm.session_id,
                role="user",
                sequence=2,
                content=case["ambiguous_response"]
                if case["kind"] == "selected_response_substring"
                else case["response"],
            )
            db.add_all([question, response])
            db.flush()
            source_ids = {"question": question.id, "response": response.id}
            db.commit()
            error, accepted, stored = None, False, None
            try:
                if case["kind"] in {"question_only", "self_report", "invented_mastery"}:
                    body = MemoryRecordCreate(
                        category="self_reported_observation",
                        field_key="difficulty",
                        content=text,
                        scope="chemistry" if case["kind"] != "question_only" else "global",
                        source_message_id=question.id,
                        source_quote=text,
                    )
                    candidate = body.model_dump()
                    stored = memory_v2.create_record(db, owner.id, body)
                else:
                    kind = "exact_text" if case["kind"] == "scored_exact" else "numeric"
                    if case["kind"] in {
                        "missing_rubric",
                        "imported_score",
                        "human_without_attestation",
                    }:
                        kind = "recorded"
                    if case["kind"] == "wrong_owner":
                        other = Structured(engine, settings, config, case["id"] + "-other")
                        owner = db.get(User, other.owner_id)
                        actor = owner
                    if case["kind"] == "wrong_workspace":
                        space = Workspace(name="Other authored workspace", slug="other-" + actor.id)
                        db.add(space)
                        db.flush()
                        actor.workspace_id = space.id
                    body = MemoryAssessmentCreate(
                        owner_id=owner.id,
                        question_message_id=question.id,
                        response_message_id=response.id,
                        question_quote=question.content,
                        response_quote=case["selected_response"]
                        if case["kind"] == "selected_response_substring"
                        else response.content,
                        scope="chemistry",
                        scoring_basis="Authored arithmetic rubric",
                        evaluator_id=actor.id,
                        evaluator_version="fixture-v1",
                        score=None if case["kind"] == "missing_rubric" else 1.0,
                        confirmation="human"
                        if case["kind"] == "human_without_attestation"
                        else "automatic",
                        rubric_kind=kind,
                        expected_answer=case["expected_answer"] if kind != "recorded" else None,
                    )
                    if case["kind"] == "reversed_source_order":
                        body = body.model_copy(
                            update={
                                "question_message_id": response.id,
                                "question_quote": response.content,
                                "response_message_id": question.id,
                                "response_quote": question.content,
                            }
                        )
                    candidate = body.model_dump()
                    stored = memory_v2.record_assessment(db, actor, body)
                accepted = stored["verification"] in {
                    "self_reported",
                    "automatic_rubric_evaluated",
                    "human_attested",
                    "explicit_user_statement",
                }
            except AppError as exc:
                error = exc.code
                db.rollback()
            candidates = [candidate]
            records.append(
                {
                    **case,
                    "candidate": candidate,
                    "source_ids": source_ids,
                    "production": {
                        "admitted_to_learner_state": accepted,
                        "stored_verification": (stored or {}).get("verification"),
                        "error_code": error,
                    },
                    "gate_disabled_projection": {
                        "candidate_count": len(candidates),
                        "candidates": candidates,
                        "writes": 0,
                    },
                    "expected_match": accepted == case["automatic_expected_admitted"],
                    "human_rating": None,
                }
            )
            # The live product's provenance stays inspectable in this disposable
            # fixture; no fabricated human-confirmed assessment is ever inserted.
            assert not list(
                db.scalars(
                    select(MemoryEntry).where(
                        MemoryEntry.owner_id == arm.owner_id,
                        MemoryEntry.verification == "human_attested",
                    )
                )
            )
    return freeze(
        destination,
        {
            "planned_pairs": 12,
            "records": records,
            "model_calls": 0,
            "human_ratings": 0,
            "scope": "Software admission gates; candidate projection is isolated and never persisted as memory",
        },
    )
