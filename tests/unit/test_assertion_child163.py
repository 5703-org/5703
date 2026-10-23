"""Memory-only backend ownership, source admission and failure boundaries.

These authored controls exercise SQLAlchemy expression filtering against explicit
Python rows. They never create an engine, real session, model or provider result.
"""

from contextlib import nullcontext
from copy import deepcopy
from types import SimpleNamespace

import pytest
from sqlalchemy.sql import operators
from sqlalchemy.sql.elements import BinaryExpression, BooleanClauseList, Null
from sqlalchemy.sql.functions import Function

from app.core.exceptions import AppError
from app.modules.answering import service
from app.modules.answering.models import (
    AnswerRequest,
    Answer,
    Job,
    Attempt,
    Message,
    Snapshot,
    Evidence,
    Citation,
)
from app.modules.learning.models import ChatSession
from app.modules.knowledge.models import (
    ActiveCorpus,
    CorpusRelease,
    RetrievalEpoch,
    Document,
    DocumentVersion,
    ProcessingRun,
    SourceUnit,
    Chunk,
    ReleaseChunk,
)
from app.modules.learning_state.models import PrivateAnswerDraft
from app.modules.learning_state import sources, tasks
from app.modules.model_settings import service as model_settings
from generation import assertion_provenance_v1 as assertions
from generation import assertion_reselection_v1 as reselection
from generation.reliability_v5 import response_claims
from generation.types import GenerationOutcome, RequestBudget
from generation import GenerationService
from personalisation.compiler import compile_profile
from retrieval.source_spans import map_fragments

from fixtures_generic163 import (
    authored_parent,
    checker_labels,
    diagnosis_for,
    private_draft,
    sha,
    ScriptedTransport,
    packet_from_messages,
)


class MemoryRows:
    """Evaluate the real predicates; no pass-only SQL/session fallback exists."""

    def __init__(self):
        self.rows = {}
        self.commits = 0
        self.serial = 0
        self.no_autoflush = nullcontext()
        self.bind = SimpleNamespace(dialect=SimpleNamespace(name="authored_memory_rows"))

    def add(self, row):
        if getattr(row, "id", None) is None and hasattr(type(row), "id"):
            self.serial += 1
            row.id = f"authored-row-{self.serial}"
        if isinstance(row, Job):
            row.state = row.state or "queued"
            row.stage = row.stage or "queued"
        self.rows.setdefault(type(row), []).append(row)

    def get(self, model, identifier, **unused):
        for row in self.rows.get(model, []):
            key = (row.release_id, row.chunk_id) if model is ReleaseChunk else row.id
            if key == identifier:
                return row
        return None

    def _value(self, expression, row):
        if isinstance(expression, Null):
            return None
        if hasattr(expression, "value"):
            return expression.value
        table = getattr(expression, "table", None)
        if table is not None and table.name == AnswerRequest.__tablename__ and isinstance(row, Job):
            row = self.get(AnswerRequest, row.request_id)
        return getattr(row, expression.key)

    def _matches(self, expression, row):
        if isinstance(expression, BooleanClauseList):
            assert expression.operator is operators.and_
            return all(self._matches(part, row) for part in expression.clauses)
        assert isinstance(expression, BinaryExpression), type(expression).__name__
        left = self._value(expression.left, row)
        right = self._value(expression.right, row)
        if expression.operator is operators.eq:
            return left == right
        if expression.operator is operators.is_:
            return left is right
        if expression.operator is operators.in_op:
            return left in right
        raise AssertionError(f"Unsupported authored predicate: {expression.operator}")

    def scalars(self, query):
        model = query.column_descriptions[0]["entity"]
        assert model in self.rows or model in {
            Answer,
            AnswerRequest,
            Attempt,
            Job,
            PrivateAnswerDraft,
        }
        rows = [
            row
            for row in self.rows.get(model, [])
            if all(self._matches(part, row) for part in query._where_criteria)
        ]
        for order in reversed(query._order_by_clauses):
            descending = getattr(order, "modifier", None) is operators.desc_op
            expression = order.element if descending else order
            rows.sort(key=lambda row: getattr(row, expression.key), reverse=descending)
        return rows

    def scalar(self, query):
        if isinstance(query._raw_columns[0], Function):
            name = query._raw_columns[0].name
            if name == "max":
                assert query.get_final_froms()[0].name == Message.__tablename__
                return max(
                    (
                        row.sequence
                        for row in self.rows.get(Message, [])
                        if all(self._matches(part, row) for part in query._where_criteria)
                    ),
                    default=None,
                )
            assert name == "count"
            assert query.get_final_froms()[0].name == Attempt.__tablename__
            return sum(
                all(self._matches(part, row) for part in query._where_criteria)
                for row in self.rows.get(Attempt, [])
            )
        rows = self.scalars(query)
        return rows[0] if rows else None

    def flush(self):
        pass  # IDs are assigned by add; no external persistence is simulated.

    def commit(self):
        self.commits += 1

    def rollback(self):
        pass  # Tests use one serial row store, never claim transaction concurrency.

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        return False


def first_question_context(question):
    return {
        "task_id": "authored-task",
        "task_version": 1,
        "task_revision": 1,
        "exposure_epoch": 0,
        "task_type": "process_reasoning",
        "question": question,
        "current_problem": question,
        "current_request": question,
        "teaching_mode": "direct",
        "help_level": 0,
        "turn_role": "user_question",
        "pending_tutor_question_id": None,
        "pending_tutor_question": None,
        "pending_tutor_question_version": 0,
        "pending_validation_id": None,
        "pending_validation_version": 0,
        "expected_response_kind": None,
        "current_step": 1,
        "learner_attempt": None,
        "last_attempt_evaluation": None,
        "requested_help": "auto",
        "continuing": False,
        "requirements": {"original_question": question},
        "delivered_turns": [],
        "disclosure_events": [],
        "policy_version": "learning_task_v3",
        "attempt_history": [],
    }


def seeded_parent(monkeypatch, *, max_calls=4, unknown=False):
    db = MemoryRows()
    request, parent, _ = authored_parent()
    request.profile = compile_profile(None, use_profile=False, turn_message=request.question)
    request.teaching_context = first_question_context(request.question)
    parent["budget"]["max_calls"] = max_calls
    db.add(
        ChatSession(
            id="session",
            user_id="actor",
            workspace_id="workspace",
            status="active",
            deleted_at=None,
        )
    )
    db.add(
        Message(
            id="user",
            session_id="session",
            sequence=1,
            role="user",
            content=request.question,
            state="error",
        )
    )
    command = {
        "question": request.question,
        "assertion_source_policy": "assertion_source_v1",
        "enhancement_version": "learning_enhancement_v1",
        "source_block_policy": "legacy_source_blocks_v1",
        "generation_context_policy": "complementary_context_v2",
        "teaching_context": request.teaching_context,
    }
    req = AnswerRequest(
        id=request.request_id,
        owner_id="actor",
        mode="interactive_chat",
        state="error",
        route="/sessions/session/messages",
        idempotency_key="original",
        body_hash="original",
        session_id="session",
        user_message_id="user",
        response_schema="chat_response_v1",
        context_snapshot_id="context",
        profile_snapshot_id="profile",
        release_id="release",
        command=command,
        budget=deepcopy(parent["budget"]),
        trace={"assertion_source_admission": {"release_id": "release", "source_epoch": "epoch"}},
    )
    db.add(req)
    db.add(
        Snapshot(
            id="context",
            owner_id="actor",
            session_id="session",
            kind="conversation",
            payload={"messages": [], "summary_text": None},
            content_hash=service.digest({"messages": [], "summary_text": None}),
        )
    )
    db.add(
        Snapshot(
            id="profile",
            owner_id="actor",
            session_id="session",
            kind="profile",
            payload=deepcopy(request.profile),
            content_hash=service.digest(request.profile),
        )
    )
    db.add(ActiveCorpus(id=1, release_id="release"))
    db.add(CorpusRelease(id="release", state="active"))
    db.add(RetrievalEpoch(id=1, token="epoch"))
    db.add(Document(id="authored-asset-1", active=True, revoked=False))
    db.add(DocumentVersion(id="authored-version", document_id="authored-asset-1"))
    db.add(
        ProcessingRun(
            id="authored-processing",
            document_version_id="authored-version",
            state="ready",
            counts={},
        )
    )
    for item in request.evidence:
        item["asset_id"] = "authored-asset-1"
        frozen = request.source_map[item["chunk_id"]]
        unit = frozen["units"][0]
        db.add(
            SourceUnit(
                id=unit["id"],
                processing_id="authored-processing",
                page=unit["page"],
                cleaned_text=item["text"],
                raw_text=item["text"],
                quality="ready",
            )
        )
        db.add(
            Chunk(
                id=item["chunk_id"],
                processing_id="authored-processing",
                document_id=item["asset_id"],
                text=item["text"],
                text_hash=item["text_hash"],
                spans=deepcopy(frozen["spans"]),
            )
        )
        db.add(ReleaseChunk(release_id="release", chunk_id=item["chunk_id"]))
    request.source_map = sources.source_map(db, req, request.evidence)
    fragments, issues = map_fragments(request.evidence, request.source_map)
    assert not issues
    public, provenance = assertions.compile_draft(private_draft(), fragments)
    public.pop("tutor_question")
    public.pop("learner_attempt_evaluation")
    parent["evidence"] = deepcopy(request.evidence)
    parent["attribution"]["fragments"] = deepcopy(fragments)
    parent["drafts"][0].update(response=public, assertion_provenance=provenance)
    parent["checks"][0].update(
        typed_judgment_raw_aliases=checker_labels(provenance),
        actual_citation_bindings=assertions.checker_bindings(
            response_claims(public), provenance, fragments
        ),
    )
    job = Job(
        id="parent-job",
        request_id=req.id,
        owner_id="actor",
        state="failed",
        stage="failed",
        execution_token=None,
        answer_id=None,
        error=deepcopy(parent["error"]),
    )
    db.add(job)
    for index, attempt in enumerate(parent["attempts"], 1):
        attempt["attempt_id"] = f"{req.id}:attempt:{index}"
        if unknown and index == 2:
            attempt["request_submitted"] = None
        db.add(
            Attempt(
                id=f"parent-start-{index}",
                job_id=job.id,
                sequence=2 * index - 1,
                payload={
                    "phase": "start",
                    "stage": attempt["stage"],
                    "attempt_id": attempt["attempt_id"],
                },
            )
        )
        db.add(
            Attempt(
                id=f"parent-finish-{index}",
                job_id=job.id,
                sequence=2 * index,
                payload={"phase": "finish", **deepcopy(attempt)},
            )
        )
    db.add(
        PrivateAnswerDraft(
            id="parent-draft",
            request_id=req.id,
            phase="generated_draft",
            payload=deepcopy(parent["drafts"][0]),
        )
    )
    db.add(
        PrivateAnswerDraft(
            id="parent-check",
            request_id=req.id,
            phase="online_check",
            payload=deepcopy(parent["checks"][0]),
        )
    )
    result = SimpleNamespace(**parent, to_dict=lambda: deepcopy(parent))
    service._save_assertion_failure(db, req, job, request, result)
    saved = next(
        row for row in db.rows[PrivateAnswerDraft] if row.phase == service.ASSERTION_FAILURE_PHASE
    )
    monkeypatch.setattr(service, "validate_learning_context", lambda *args, **kwargs: None)
    actor = SimpleNamespace(id="actor", role=SimpleNamespace(name="learner"))
    diagnosis = diagnosis_for(request, parent, fragments)
    return db, req, job, request, parent, saved, actor, diagnosis


def submit(fixture):
    db, req, _, _, _, saved, actor, diagnosis = fixture
    receipt = service.submit_assertion_reselection(
        db,
        SimpleNamespace(storage_root="unused"),
        actor,
        parent_request_id=req.id,
        saved_failure_id=saved.id,
        diagnosis=diagnosis,
    )
    return db.get(AnswerRequest, receipt["request_id"]), db.get(Job, receipt["job_id"])


def parent_state(fixture):
    db, req, job, _, _, _, _, _ = fixture
    return deepcopy(
        (
            req.command,
            req.budget,
            req.state,
            job.state,
            job.error,
            job.execution_token,
            db.get(Message, "user").state,
            [row.payload for row in db.rows[Attempt] if row.job_id == job.id],
            [
                (row.id, row.request_id, row.phase, row.payload)
                for row in db.rows[PrivateAnswerDraft]
                if row.request_id == req.id
            ],
        )
    )


def test_actual_snapshot_load_submit_binds_child_and_preserves_parent(monkeypatch):
    fixture = seeded_parent(monkeypatch)
    db, parent_req, _, request, _, saved, _, _ = fixture
    before = parent_state(fixture)
    assert set(saved.payload["generation_request"]).isdisjoint(
        {"history", "summary", "profile", "memory_context"}
    )
    assert saved.payload["protected_context_refs"]["profile"]["snapshot_id"] == "profile"
    child, job = submit(fixture)
    _, bound = service._validate_assertion_child(db, SimpleNamespace(storage_root="unused"), child)
    assert bound.request_id == request.request_id == parent_req.id
    assert child.id != parent_req.id and job.request_id == child.id
    assert child.budget == parent_req.budget and child.budget["consumed_calls"] == 2
    assert child.user_message_id is None
    assert bound.assertion_reselection["parent_draft_id"] == "parent-draft"
    assert bound.assertion_reselection["parent_check_id"] == "parent-check"
    assert parent_state(fixture) == before

    # Complete the real private selector/check consumer with explicit authored wire labels.
    def selector(messages):
        import json

        packet = json.loads(messages[-1]["content"])
        target = packet["targets"][0]
        return {
            "plan_sha256": packet["plan_sha256"],
            "replacements": [
                {
                    "claim_id": target["claim_id"],
                    "prior_binding_sha256": target["prior_binding_sha256"],
                    "selections": [
                        {"evidence_id": target["evidence_ids"][0], "source_ids": ["F001", "F002"]}
                    ],
                }
            ],
        }

    def checker(messages):
        packet = packet_from_messages(messages)
        proofs = packet["ASSERTION_PROOFS"]["assertions"]
        provenance = {
            "assertions": [
                {
                    "assertion_id": row["assertion_id"],
                    "claim_id": row["claim_id"],
                    "sources": [
                        {**source, "source_id": source["fragment_id"]}
                        for source in row["selected_source_union"]
                    ],
                }
                for row in proofs
            ]
        }
        value = checker_labels(provenance, negative_target=False)
        first = proofs[0]["selected_source_union"][0]
        value["requirements"] = [
            {
                "requirement_id": row["id"],
                "relevance": "related",
                "sufficiency": "sufficient",
                "evidence": [
                    {
                        "evidence_id": first["evidence_id"],
                        "fragment_id": first["fragment_id"],
                        "quote": first["exact_text"],
                    }
                ],
                "conditions_preserved": True,
                "response_coverage": "covered",
                "missing_information": "",
                "reason": "Authored structural control, not measured semantic accuracy.",
            }
            for row in packet["CONTEXT_COVERAGE"]["requirements"]
        ]
        return value

    transport = ScriptedTransport([selector, checker])
    monkeypatch.setattr(service, "GenerationService", lambda **unused: GenerationService(transport))
    monkeypatch.setattr(model_settings, "resolve_secret", lambda *args: None)
    published_tasks = []
    monkeypatch.setattr(
        tasks,
        "publish_task",
        lambda db, context, *, result: published_tasks.append(
            (context["task_id"], result.response)
        ),
    )
    job.state, job.execution_token = "running", "owned-token"
    import time

    service._execute_assertion_reselection(
        lambda: db,
        SimpleNamespace(storage_root="unused"),
        job.id,
        "owned-token",
        time.perf_counter(),
    )
    assert len(transport.calls) == 2
    assert job.state == "succeeded" and child.state == "answered" and job.execution_token is None
    answer = db.get(Answer, job.answer_id)
    assert answer.request_id == child.id and answer.job_id == job.id
    assert answer.response == fixture[4]["drafts"][0]["response"]
    assert child.budget["consumed_calls"] == 4 and parent_req.budget["consumed_calls"] == 2
    assert {
        row.request_id for row in db.rows[PrivateAnswerDraft] if row.request_id != parent_req.id
    } == {child.id}
    assert {row.answer_id for row in db.rows[Evidence]} == {answer.id}
    evidence_rows = {row.id: row for row in db.rows[Evidence]}
    assert all(
        row.answer_id == answer.id and evidence_rows[row.evidence_id].answer_id == answer.id
        for row in db.rows[Citation]
    )
    assert published_tasks == [("authored-task", answer.response)]
    assert parent_state(fixture) == before


@pytest.mark.parametrize(
    "defect", ["budget_exhausted", "unknown", "wrong_owner", "foreign_saved_draft"]
)
def test_ineligible_parent_never_claims_child(monkeypatch, defect):
    fixture = seeded_parent(
        monkeypatch, max_calls=2 if defect == "budget_exhausted" else 4, unknown=defect == "unknown"
    )
    db, req, _, _, _, saved, actor, diagnosis = fixture
    if defect == "wrong_owner":
        actor.id = "other"
    if defect == "foreign_saved_draft":
        db.get(PrivateAnswerDraft, "parent-draft").request_id = "foreign-parent"
    with pytest.raises(AppError):
        service.submit_assertion_reselection(
            db,
            SimpleNamespace(storage_root="unused"),
            actor,
            parent_request_id=req.id,
            saved_failure_id=saved.id,
            diagnosis=diagnosis,
        )
    assert len(db.rows[AnswerRequest]) == 1


@pytest.mark.parametrize("defect", ["epoch", "chunk_text", "complete_block"])
def test_actual_source_drift_blocks_candidate(monkeypatch, defect):
    fixture = seeded_parent(monkeypatch)
    db, _, _, _, _, saved, _, _ = fixture
    if defect == "epoch":
        db.get(RetrievalEpoch, 1).token = "changed"
    elif defect == "chunk_text":
        chunk = db.get(Chunk, "authored-chunk-1")
        chunk.text += " Changed source."
        chunk.text_hash = sha(chunk.text)
    else:
        saved.payload["parent_outcome"]["attribution"]["fragments"][0]["complete_block"] = False
        saved.payload["snapshot_sha256"] = reselection.canonical_sha256(
            {key: value for key, value in saved.payload.items() if key != "snapshot_sha256"}
        )
    with pytest.raises(AppError):
        submit(fixture)
    assert len(db.rows[AnswerRequest]) == 1


def test_failed_child_cannot_reclaim_budget_or_retry_parent(monkeypatch):
    fixture = seeded_parent(monkeypatch)
    db, parent, _, _, _, _, _, _ = fixture
    child, job = submit(fixture)
    child.state, job.state = "error", "failed"
    with pytest.raises(AppError):
        submit(fixture)
    assert service.can_retry(db, child) is False
    assert service.can_retry(db, parent) is False
    assert len(db.rows[AnswerRequest]) == 2


@pytest.mark.parametrize("defect", ["draft_id", "protected_context", "shared_user_message"])
def test_child_foreign_linkage_is_not_admitted(monkeypatch, defect):
    fixture = seeded_parent(monkeypatch)
    db = fixture[0]
    child, _ = submit(fixture)
    if defect == "draft_id":
        child.command["assertion_reselection"]["continuation"]["parent_draft_id"] = "foreign"
        child.body_hash = reselection.canonical_sha256(child.command)
    elif defect == "protected_context":
        child.profile_snapshot_id = "other-profile"
    else:
        child.user_message_id = "user"
    with pytest.raises(AppError):
        service._validate_assertion_child(db, SimpleNamespace(storage_root="unused"), child)


def test_consumed_child_stops_before_secret_or_transport(monkeypatch):
    fixture = seeded_parent(monkeypatch)
    db = fixture[0]
    child, job = submit(fixture)
    job.state, job.execution_token = "running", "owned-token"
    child.trace["assertion_reselection"]["candidate_count"] = 1

    def forbidden(*args, **kwargs):
        raise AssertionError("No secret or generation boundary is permitted for consumed child")

    monkeypatch.setattr(model_settings, "resolve_secret", forbidden)
    monkeypatch.setattr(service, "GenerationService", forbidden)
    service._execute_assertion_reselection(
        lambda: db, SimpleNamespace(storage_root="unused"), job.id, "owned-token", 0
    )
    assert job.state == "failed" and job.execution_token is None
    assert child.budget["consumed_calls"] == 2


def test_pretransport_source_failure_keeps_child_reserved_attempt(monkeypatch):
    fixture = seeded_parent(monkeypatch)
    db, parent_req, parent_job, _, _, _, _, _ = fixture
    child, job = submit(fixture)
    job.state, job.execution_token = "running", "owned-token"
    monkeypatch.setattr(model_settings, "resolve_secret", lambda *args: None)

    class AuthoredControl:
        def __init__(self, **unused):
            pass

        def generate(self, request, budget, *, on_attempt):
            assert request.request_id == parent_req.id
            budget.reserve()
            db.get(RetrievalEpoch, 1).token = "changed-before-selector"
            on_attempt(
                {
                    "phase": "start",
                    "stage": "assertion_source_reselection",
                    "budget": budget.to_dict(),
                }
            )
            raise AssertionError("Source fence must stop before scripted transport")

    monkeypatch.setattr(service, "GenerationService", AuthoredControl)
    import time

    service._execute_assertion_reselection(
        lambda: db,
        SimpleNamespace(storage_root="unused"),
        job.id,
        "owned-token",
        time.perf_counter(),
    )
    assert job.state == "failed" and job.execution_token is None
    assert child.budget["consumed_calls"] == 3 and parent_req.budget["consumed_calls"] == 2
    attempts = [row for row in db.rows[Attempt] if row.job_id == job.id]
    assert len(attempts) == 1 and attempts[0].payload["source_fence_error"] == "AppError"
    assert (
        parent_job.state == "failed"
        and len([r for r in db.rows[Attempt] if r.job_id == parent_job.id]) == 4
    )


def test_publication_source_failure_saves_only_child_private_records(monkeypatch):
    fixture = seeded_parent(monkeypatch)
    db, parent_req, parent_job, _, parent_outcome, _, _, _ = fixture
    child, job = submit(fixture)
    _, bound = service._validate_assertion_child(db, SimpleNamespace(storage_root="unused"), child)
    before = parent_state(fixture)
    job.state, job.execution_token = "running", "owned-token"
    result = GenerationOutcome(
        response=deepcopy(parent_outcome["drafts"][0]["response"]),
        evidence=deepcopy(parent_outcome["evidence"]),
        budget=RequestBudget(consumed_calls=4, active_seconds=2).to_dict(),
        drafts=[{**deepcopy(parent_outcome["drafts"][0]), "revision": 1}],
        checks=[{**deepcopy(parent_outcome["checks"][0]), "revision": 1}],
        token_budget={"assertion_reselection": {"candidate_count": 1}},
        model_mode="authored_offline_control",
    )
    db.get(RetrievalEpoch, 1).token = "changed-before-publication"
    import time

    service._persist_answer_outcome(
        lambda: db,
        SimpleNamespace(storage_root="unused"),
        job.id,
        "owned-token",
        bound,
        result,
        result.evidence,
        {},
        time.perf_counter(),
    )
    assert (
        job.state == "failed"
        and job.error["code"] == "SOURCE_UNAVAILABLE"
        and job.execution_token is None
    )
    child_private = [row for row in db.rows[PrivateAnswerDraft] if row.request_id == child.id]
    assert {row.phase for row in child_private} == {"generated_draft", "online_check"}
    assert not db.rows.get(Answer) and len(db.rows[Message]) == 1
    assert parent_state(fixture) == before
    assert parent_job.request_id == parent_req.id and child.budget["consumed_calls"] == 4
