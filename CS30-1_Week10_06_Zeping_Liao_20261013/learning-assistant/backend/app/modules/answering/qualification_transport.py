"""Freeze a narrowly bound isolated checker transport without changing defaults."""

import hashlib

from app.core.exceptions import AppError

VERSION = "ordinary_qa_compact_v2"
BINDING_VERSION = "isolated_qualification_transport_v1"


def question_hash(question):
    return hashlib.sha256(question.encode("utf-8")).hexdigest()


def submission_fields(settings, session_id, body, teaching):
    """Only the configured session and exact normalized API question opt in."""
    transport = getattr(settings, "chat_qualification_source_transport", None)
    if transport is None or session_id != settings.chat_qualification_transport_session_id:
        return {}
    if (question_hash(body.content) != settings.chat_qualification_transport_question_sha256
            or body.answer_mode != "textbook" or body.reading_context is not None
            or (teaching or {}).get("teaching_mode") != "direct"
            or (teaching or {}).get("help_level") != 0
            or any((teaching or {}).get(key) for key in (
                "attempt", "learner_attempt", "practice_context", "pending_tutor_question_id",
                "check_cumulative", "check_suggestions", "control_evidence"))):
        raise AppError("CONFLICT", detail="The isolated checker binding is outside ordinary QA scope.")
    return {
        "qualification_source_transport": transport,
        "qualification_transport_binding": {
            "version": BINDING_VERSION,
            "session_id": session_id,
            "question_sha256": question_hash(body.content),
        },
    }


def generation_fields(command, session_id):
    """Consume the frozen command; current server settings cannot retarget it."""
    if "qualification_source_transport" not in command:
        if "qualification_transport_binding" in command:
            raise AppError("CONFLICT", detail="The frozen isolated checker transport is missing.")
        return {}
    binding = command.get("qualification_transport_binding")
    if (command["qualification_source_transport"] != VERSION
            or not isinstance(binding, dict)
            or binding != {
                "version": BINDING_VERSION, "session_id": session_id,
                "question_sha256": question_hash(command["question"]),
            }):
        raise AppError("CONFLICT", detail="The frozen isolated checker binding is invalid.")
    return {"qualification_source_transport": VERSION}
