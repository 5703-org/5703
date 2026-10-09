"""Server-owned learning-task transitions and immutable request snapshots."""

import re
import copy
from uuid import uuid4
from sqlalchemy import select
from app.core.exceptions import AppError
from app.db.base import utcnow
from .models import LearningTask, LearningExposure, AnswerPresentation, PrivateAnswerDraft

HINT = re.compile(
    r"\b(?:hint|clue|do not (?:tell|give|show)|don't (?:tell|give|show)|without (?:solving|the answer)|let me (?:try|solve))\b",
    re.I,
)
FULL = re.compile(
    r"\b(?:full (?:answer|explanation|solution)|complete (?:answer|explanation|solution)|tell me the answer|show (?:me )?the (?:answer|solution))\b",
    re.I,
)
CONTINUE = re.compile(
    r"^\s*(?:another|next|more|one more|give me another|give me (?:the )?next|continue|what next|help me further)\b",
    re.I,
)
NEW_PROBLEM = re.compile(
    r"^\s*(?:new (?:problem|question|topic)|another (?:problem|question|topic)|"
    r"(?:let['’]s|can we|please) (?:switch|change) (?:to|topics?)|"
    r"(?:switch|change) (?:topic|subject)|instead[, :])\b",
    re.I,
)
QUESTION_OR_INSTRUCTION = re.compile(
    r"^\s*(?:what|why|how|where|when|who|which|explain|compare|define|describe|"
    r"calculate|compute|tell me about|teach me|can you|could you|would you)\b",
    re.I,
)
ATTEMPT_PREFIX = re.compile(
    r"^\s*(?:i (?:think|believe|guess|got|calculate|would|am|don't|do not)|"
    r"my (?:answer|calculation|reasoning)|the answer|because|yes\b|no\b|not\b|"
    r"it (?:is|isn't|should|would|must)|perhaps|maybe)\b",
    re.I,
)


def is_learner_attempt(task, body):
    """Classify a response to an actual pending question, never length alone."""
    if not task or not task.pending_tutor_question_id or task.teaching_mode != "hint":
        return False
    text = body.content.strip()
    if NEW_PROBLEM.search(text) or QUESTION_OR_INSTRUCTION.search(text) or text.endswith("?"):
        return False
    if HINT.search(text) or FULL.search(text) or navigation_only(text):
        return False
    bound = body.pending_tutor_question_id == task.pending_tutor_question_id
    if body.turn_role == "learner_attempt" or ATTEMPT_PREFIX.search(text):
        return True
    if task.expected_response_kind == "numeric":
        return bool(re.search(r"[+−-]?\d+(?:\.\d+)?", text)) and (bound or len(text) <= 160)
    if bound:
        return True
    # Older clients omit question bindings. Require a substantive shared term;
    # unrelated standalone words continue through ordinary question handling.
    tokens = set(re.findall(r"[a-z]{3,}", text.lower()))
    topic = set(
        re.findall(r"[a-z]{3,}", (task.question + " " + task.pending_tutor_question).lower())
    )
    return bool((tokens & topic) - {"the", "and", "this", "that", "with", "for", "answer", "which"})


# A bare navigation command has no new subject. Prefixes alone are insufficient:
# "another question: what is osmosis?" starts a different problem.
NAVIGATION_WORDS = frozenset(
    "a an the please give show tell provide offer me full complete answer explanation "
    "solution hint clue step example another next more one continue what help further "
    "for to of on about with this that it same current problem task question topic "
    "process now without solving do not don't can could would you i want like need "
    "may just only is my previous".split()
)


def navigation_only(content):
    words = re.findall(r"[^\W_]+(?:['’][^\W_]+)?", content.casefold())
    return bool(words) and all(word in NAVIGATION_WORDS for word in words)


def task_out(row):
    return {
        "id": row.id,
        "session_id": row.session_id,
        "question": row.question,
        "practice_item_id": row.requirements.get("practice_context", {}).get("item_id"),
        "practice_goal_id": row.requirements.get("practice_goal_context", {}).get("goal_id"),
        "practice_progress_version": row.requirements.get("practice_context", {}).get(
            "progress_version"
        ),
        "task_type": row.task_type,
        "teaching_mode": row.teaching_mode,
        "help_level": row.help_level,
        "state": row.state,
        "version": row.version,
        "pending_tutor_question_id": row.pending_tutor_question_id,
        "pending_tutor_question": row.pending_tutor_question,
        "pending_tutor_question_version": row.pending_tutor_question_version,
        "expected_response_kind": row.expected_response_kind,
        "current_step": row.current_step,
        "turn_role": row.turn_role,
        "last_attempt_evaluation": row.last_attempt_evaluation,
    }


def resolve_task(db, actor, session, message, body, context):
    """A same-topic new problem starts fresh; only actual continuation carries hints."""
    from conversation.query import prepare_query

    task = None
    if body.task_id:
        task = db.get(LearningTask, body.task_id)
        if not task or task.owner_id != actor.id or task.session_id != session.id:
            raise AppError("NOT_FOUND")
    else:
        task = db.scalar(
            select(LearningTask)
            .where(
                LearningTask.owner_id == actor.id,
                LearningTask.session_id == session.id,
                LearningTask.state == "active",
            )
            .order_by(LearningTask.created_at.desc())
            .limit(1)
        )
    if body.task_version is not None and (not task or task.version != body.task_version):
        raise AppError("CONFLICT", "The learning task changed. Reload the conversation.")
    if body.pending_tutor_question_id is not None and (
        not task
        or task.pending_tutor_question_id != body.pending_tutor_question_id
        or task.pending_tutor_question_version != body.pending_tutor_question_version
    ):
        raise AppError("CONFLICT", "The tutor question changed. Reload the conversation.")
    action = body.task_action
    explicit_full = action == "full_explanation" or bool(FULL.search(body.content))
    explicit_hint = action == "more_hint" or bool(HINT.search(body.content))
    explicit_new = action == "new" or bool(NEW_PROBLEM.search(body.content))
    learner_attempt = (
        not explicit_full
        and not explicit_new
        and action not in {"more_hint"}
        and is_learner_attempt(task, body)
    )
    if body.turn_role == "learner_attempt" and not (
        learner_attempt or explicit_full or explicit_new
    ):
        raise AppError("CONFLICT", "This message does not answer the current tutor question.")
    prepared = prepare_query(body.content, context.get("messages", []), context.get("summary_text"))
    pd = prepared.model_dump() if hasattr(prepared, "model_dump") else prepared
    continuing = bool(task) and (
        learner_attempt
        or action in {"continue", "more_hint", "full_explanation"}
        or (
            action == "auto"
            and (
                (CONTINUE.search(body.content) or explicit_full)
                and navigation_only(body.content)
                or pd.get("topic_relation") == "same_topic"
                and pd.get("intent") in {"follow_up", "reexplain", "source_request"}
            )
        )
    )
    if explicit_new:
        continuing = False
    if action in {"continue", "more_hint", "full_explanation"} and task is None:
        raise AppError("CONFLICT", "Select an existing learning task before continuing it.")
    if body.task_id and task and task.state != "active" and continuing:
        raise AppError("CONFLICT", "This task has ended. Start a new learning task.")
    mode = (
        "hint"
        if learner_attempt
        else body.teaching_mode
        or (
            "direct"
            if explicit_full
            else "hint"
            if explicit_hint
            else task.teaching_mode
            if continuing
            else "direct"
        )
    )
    if explicit_full:
        mode = "direct"
    if not continuing:
        if task and task.state == "active":
            task.state = "completed"
            task.version += 1
        task_type = (
            "concept_comparison"
            if re.search(r"\b(compare|comparison|difference|versus|vs)\b", body.content, re.I)
            else "simple_calculation"
            if re.search(
                r"\b(calculate|compute|how much|how many|moles|pressure|volume)\b",
                body.content,
                re.I,
            )
            and re.search(r"\d", body.content)
            else "process_reasoning"
        )
        task = LearningTask(
            owner_id=actor.id,
            session_id=session.id,
            initial_message_id=message.id,
            question=body.content,
            task_type=task_type,
            teaching_mode=mode,
            help_level=0,
            requirements={"original_question": body.content},
        )
        db.add(task)
        db.flush()
    else:
        task.teaching_mode = mode
        task.version += 1
        task.updated_at = utcnow()
    task.turn_role = "learner_attempt" if learner_attempt else "user_question"
    from app.modules.learning_product.tutoring import disclosure_turns

    practice = task.requirements.get("practice_context")
    prior = disclosure_turns(practice)
    events = []
    for event in db.scalars(
        select(LearningExposure)
        .where(LearningExposure.task_id == task.id)
        .order_by(LearningExposure.created_at)
    ):
        if event.kind == "delivered":
            presentation = db.get(AnswerPresentation, event.presentation_id)
            if presentation:
                prior.append(
                    {
                        "answer_id": event.answer_id,
                        "response": presentation.payload.get("response"),
                        "citation_views": presentation.payload.get("citation_views", []),
                        "help_level": presentation.payload.get("help_level", 0),
                    }
                )
        else:
            events.append(
                {"kind": event.kind, "answer_id": event.answer_id, "payload": event.payload}
            )
    return {
        "task_id": task.id,
        "task_version": task.version,
        "task_revision": task.version,
        "exposure_epoch": task.exposure_epoch,
        "task_type": task.task_type,
        "question": task.question,
        "current_problem": task.question,
        "current_request": body.content,
        "teaching_mode": mode,
        "help_level": task.help_level
        if learner_attempt
        else min(3, task.help_level + 1)
        if mode == "hint"
        else 0,
        "turn_role": task.turn_role,
        "pending_tutor_question_id": task.pending_tutor_question_id,
        "pending_tutor_question": task.pending_tutor_question,
        "pending_tutor_question_version": task.pending_tutor_question_version,
        "pending_validation_id": task.pending_tutor_question_id,
        "pending_validation_version": task.pending_tutor_question_version,
        "expected_response_kind": task.expected_response_kind,
        "current_step": task.current_step,
        "learner_attempt": body.content if learner_attempt else None,
        "last_attempt_evaluation": task.last_attempt_evaluation,
        "requested_help": action,
        "continuing": continuing,
        "requirements": task.requirements,
        **({"practice_context": practice} if practice else {}),
        "delivered_turns": prior,
        "disclosure_events": events,
        "policy_version": "learning_task_v3",
    }


def validate_task(db, owner_id, context):
    if not context:
        return
    task = db.get(LearningTask, context["task_id"])
    if task:
        db.refresh(task)
    if (
        not task
        or task.owner_id != owner_id
        or task.version != context["task_version"]
        or task.exposure_epoch != context.get("exposure_epoch", 0)
        or task.state != "active"
        or (
            context.get("policy_version") == "learning_task_v3"
            and (
                task.pending_tutor_question_id != context.get("pending_validation_id")
                or task.pending_tutor_question_version != context.get("pending_validation_version")
            )
        )
    ):
        raise AppError("CONFLICT", "The learning task changed. Submit a new request.")
    from app.modules.learning_product.tutoring import validate_context

    validate_context(db, owner_id, task, context)
    from app.modules.learning_product.goal_tutoring import validate_context as validate_goal

    validate_goal(db, owner_id, task, context)


def publish_task(db, context, result=None):
    if not context:
        return
    task = db.get(LearningTask, context["task_id"])
    task.help_level = context["help_level"]
    task.teaching_mode = context["teaching_mode"]
    approved = getattr(result, "teaching_context", {}) or {}
    response = getattr(result, "response", {}) or {}
    text = response.get("answer_text", "")
    next_question = approved.get("tutor_question")
    evaluation = approved.get("learner_attempt_evaluation")
    if (
        context.get("turn_role") == "learner_attempt"
        and getattr(result, "model_mode", None) == "live"
        and response.get("response_type") == "answer"
        and not evaluation
    ):
        raise AppError("VALIDATION_FAILED", "The checked response has no learner-attempt feedback.")
    if context.get("turn_role") == "learner_attempt" and evaluation:
        if (
            evaluation.get("status")
            not in (
                {"correct", "incorrect", "partial", "unclear", "unrelated"}
                if getattr(result, "token_budget", {}).get("reliability_policy")
                == "evidence_reliability_v5"
                else {"correct", "incorrect", "partial", "unclear"}
            )
            or not evaluation.get("feedback")
            or evaluation["feedback"] not in text
        ):
            raise AppError("VALIDATION_FAILED", "Learner feedback differs from the checked answer.")
        task.last_attempt_evaluation = {
            **evaluation,
            "basis": "model_feedback",
            "question_id": context.get("pending_tutor_question_id"),
            "question_version": context.get("pending_tutor_question_version"),
        }
        if evaluation["status"] == "correct" and not task.requirements.get("practice_context"):
            task.current_step = context.get("current_step", task.current_step) + 1
        else:
            task.current_step = context.get("current_step", task.current_step)
    if task.teaching_mode == "direct":
        task.pending_tutor_question_id = None
        task.pending_tutor_question = None
        task.expected_response_kind = None
        task.pending_tutor_question_version += 1
    elif next_question:
        if (
            not next_question.get("question")
            or next_question["question"] not in text
            or next_question.get("expected_response_kind")
            not in {"concept", "numeric", "explanation", "choice"}
        ):
            raise AppError("VALIDATION_FAILED", "Tutor question differs from the checked answer.")
        task.pending_tutor_question_id = str(uuid4())
        task.pending_tutor_question = next_question["question"]
        task.expected_response_kind = next_question["expected_response_kind"]
        task.pending_tutor_question_version += 1
    elif (
        context.get("turn_role") == "learner_attempt"
        and evaluation
        and evaluation["status"] == "correct"
    ):
        task.pending_tutor_question_id = None
        task.pending_tutor_question = None
        task.expected_response_kind = None
        task.pending_tutor_question_version += 1
    # Do not increment: a retry retains the frozen request task revision; next submission does.
    task.updated_at = utcnow()


def recent_attempt_feedback(db, owner_id, task_id):
    """Read only published, owned attempt feedback; erased private rows stay absent."""
    from app.modules.answering.models import AnswerRequest, Answer

    rows = db.execute(
        select(PrivateAnswerDraft, Answer)
        .join(AnswerRequest, AnswerRequest.id == PrivateAnswerDraft.request_id)
        .join(Answer, Answer.request_id == AnswerRequest.id)
        .where(
            AnswerRequest.owner_id == owner_id,
            AnswerRequest.command["teaching_context"]["task_id"].as_string() == task_id,
            PrivateAnswerDraft.phase == "generated_draft",
        )
        .order_by(PrivateAnswerDraft.created_at.desc())
        .limit(12)
    )
    observed, seen = [], set()
    for row, delivered in rows:
        evaluation = row.payload.get("learner_attempt_evaluation")
        if (
            row.request_id not in seen
            and row.payload.get("response") == delivered.response
            and evaluation
        ):
            observed.append({**evaluation, "request_id": row.request_id})
            seen.add(row.request_id)
            if len(observed) == 3:
                break
    chronological = list(reversed(observed))
    task = db.get(LearningTask, task_id)
    if task and task.owner_id == owner_id:
        practice = task.requirements.get("practice_context", {})
        recorded = [
            {
                "status": attempt["feedback"]["outcome"],
                "feedback": attempt["feedback"]["message"],
                "practice_attempt_id": attempt["id"],
                "basis": "deterministic_practice_rules",
            }
            for attempt in practice.get("recent_attempts", [])
            if attempt["feedback"]["outcome"] in {"correct", "incorrect", "partial", "unclear"}
        ]
        chronological = [*recorded, *chronological][-3:]
    return chronological


def refresh_disclosures(db, owner_id, context):
    """A new regeneration freezes newly displayed surfaces without changing its problem."""
    result = copy.deepcopy(context)
    task = db.get(LearningTask, result["task_id"])
    if (
        not task
        or task.owner_id != owner_id
        or task.state != "active"
        or task.version != result["task_version"]
    ):
        raise AppError("CONFLICT", "The learning task changed. Submit a new request.")
    result["exposure_epoch"] = task.exposure_epoch
    result["pending_validation_id"] = task.pending_tutor_question_id
    result["pending_validation_version"] = task.pending_tutor_question_version
    from app.modules.learning_product.tutoring import disclosure_turns

    result["delivered_turns"], result["disclosure_events"] = (
        disclosure_turns(result.get("practice_context")),
        [],
    )
    for event in db.scalars(
        select(LearningExposure)
        .where(LearningExposure.task_id == task.id)
        .order_by(LearningExposure.created_at)
    ):
        if event.kind == "delivered":
            presentation = db.get(AnswerPresentation, event.presentation_id)
            if presentation:
                result["delivered_turns"].append(
                    {
                        "answer_id": event.answer_id,
                        "response": presentation.payload.get("response"),
                        "citation_views": presentation.payload.get("citation_views", []),
                        "help_level": presentation.payload.get("help_level", 0),
                    }
                )
        else:
            result["disclosure_events"].append(
                {"kind": event.kind, "answer_id": event.answer_id, "payload": event.payload}
            )
    return result
