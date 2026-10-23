"""Real disposable PostgreSQL/worker with authored transports; no network."""

from copy import deepcopy
import json
from uuid import uuid4
import pytest
from sqlalchemy import select
from app.modules.answering import service
from app.modules.answering.models import AnswerRequest, Job, Answer
from app.modules.learning_state.models import PrivateAnswerDraft
from app.modules.model_settings import service as models
from generation import GenerationService, ModelConfig
from generation.types import ProviderResult, failure
from generation import assertion_provenance_v1 as assertions
from generation import assertion_bounded_revision_v1 as revision
from generation import requirement_scope_v1 as scope
from generation.requirement_axes_v1 import DERIVED_FIELDS
from .test_chat_runtime import call, corpus, session


@pytest.fixture
def authored_revision(runtime, monkeypatch):
    from pathlib import Path

    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "unit"))
    from test_assertion_provenance161 import decode_packet, authored_full_checker

    rt = runtime
    corpus(rt)
    rt.settings.model_mode = "live"
    rt.settings.llm_provider = "local"
    rt.settings.llm_model = "authored-native-revision"
    rt.settings.llm_api_base = "http://127.0.0.1:9/v1"
    rt.settings.experimental_assertion_revision_enabled = True
    config = ModelConfig(
        provider="local",
        model="authored-native-checker",
        base_url="http://127.0.0.1:9/v1",
        window_tokens=32000,
        max_tokens=4096,
        tokenizer_provider="estimate",
    )
    monkeypatch.setattr(models, "resolve_active_checker_model_config", lambda *a: config)
    calls = []
    requests = []
    control = {"reject_recheck": False}

    def no_network(*a, **kw):
        raise AssertionError("No external transport in native fixture")

    monkeypatch.setattr("generation.adapters.open_provider", no_network)
    monkeypatch.setattr("generation.adapters.LLMAdapter._call", no_network)

    class Transport:
        def generate(self, messages, **kwargs):
            name = kwargs["response_schema_name"]
            calls.append(name)
            if name == revision.PROPOSAL_SCHEMA:
                if control.get("during_revision"):
                    control["during_revision"]()
                if control.get("timeout"):
                    return ProviderResult(
                        provider="deliberately_scripted_offline",
                        model="authored-native",
                        request_submitted=None,
                        error=failure("PROVIDER_TIMEOUT", "Authored unknown-result timeout"),
                    )
                packet = json.loads(messages[-1]["content"])
                target = packet["targets"][0]
                output = {
                    **packet["bindings"],
                    "plan_sha256": packet["plan_sha256"],
                    "edits": [
                        {
                            "claim_id": target["claim_id"],
                            "prior_binding_sha256": target["prior_binding_sha256"],
                            "replacement_text": "Photosynthesis captures light energy and stores chemical energy in sugars.",
                        }
                    ],
                }
            elif name.startswith("teaching_assertion"):
                data = next(
                    json.loads(m["content"].split("\n", 1)[1])
                    for m in messages
                    if m["content"].startswith("CONTEXT_DATA_JSON:")
                )
                bank = assertions.decode_generation_source_bank(
                    {
                        k: data[k]
                        for k in (
                            "ASSERTION_SOURCE_BANK",
                            "ASSERTION_SOURCE_LOCATORS",
                            "GENERATION_INPUT_ENCODING",
                        )
                    }
                )
                chosen = next(
                    s for s in bank if "Photosynthesis captures light energy" in s["exact_text"]
                )
                output = {
                    "schema_version": "chat_response_v1",
                    "response_type": "answer",
                    "answer_text": [
                        {
                            "assertion_id": "A001",
                            "text": "Photosynthesis creates chemical energy without requiring light.",
                            "source_ids": [chosen["source_id"]],
                        }
                    ],
                    "short_answer": None,
                    "citations": [chosen["evidence_id"]],
                    "refusal_reason": None,
                    "follow_up_questions": [],
                    "tutor_question": None,
                    "learner_attempt_evaluation": None,
                    "confidence": None,
                }
            else:
                negative = len(calls) == 2 or control["reject_recheck"]
                output = authored_full_checker(messages, "negative_status" if negative else None)
                packet = decode_packet(messages)
                if "REQUIREMENT_SCOPE" in packet:
                    frozen = packet["REQUIREMENT_SCOPE"]
                    for field in scope.DERIVED_SCOPE_FIELDS:
                        output.pop(field, None)
                    for row in output["requirements"]:
                        row.update(necessity="required", response_missing_information="")
                    output.update(
                        requirement_scope_version=scope.VERSION,
                        requirement_scope_sha256=frozen["scope_sha256"],
                        optional_extensions=[],
                    )
            return ProviderResult(
                raw_text=json.dumps(output),
                provider="deliberately_scripted_offline",
                model="authored-native",
                finish_reason="stop",
                request_submitted=True,
                usage={"input_tokens": 50, "output_tokens": 50, "total_tokens": 100, "cost": 0},
            )

    class LocalService(GenerationService):
        def __init__(self, *a, **kw):
            super().__init__(
                Transport(), checker_adapter=Transport(), cancelled=kw.get("cancelled")
            )

        def generate(self, request, *a, **kw):
            requests.append(deepcopy(request))
            result = super().generate(request, *a, **kw)
            if result.error:
                print("AUTHORED_ERROR", json.dumps(result.error))
            return result

    monkeypatch.setattr(service, "GenerationService", LocalService)
    yield rt, calls, requests, control
    with rt.db() as db:
        for job in db.scalars(select(Job).where(Job.state.in_(service.ACTIVE))):
            service.cancel_job(db, job)
        db.commit()


def failed_parent(
    fixture, *, admit=True, question="How does photosynthesis capture and store energy?"
):
    rt, calls, requests, _ = fixture
    chat = session(rt)
    receipt = call(
        rt,
        "POST",
        f"/sessions/{chat['id']}/messages",
        {
            "content": question,
            "use_profile": False,
            "check_answer": True,
        },
        {**rt.headers(), "Idempotency-Key": str(uuid4())},
        202,
    )
    assert rt.work()
    job = call(rt, "GET", "/jobs/" + receipt["job_id"])
    assert job["state"] == "failed", job
    assert job["error"]["code"] == "SEMANTIC_CHECK_FAILED", (job, requests[-1].teaching_context)
    assert len(calls) == 2
    with rt.db() as db:
        req = db.get(AnswerRequest, receipt["request_id"])
        saved = db.scalar(
            select(PrivateAnswerDraft).where(
                PrivateAnswerDraft.request_id == req.id,
                PrivateAnswerDraft.phase == service.ASSERTION_FAILURE_PHASE,
            )
        )
        assert saved is not None, {
            "trace": req.trace.get("assertion_failure_snapshot"),
            "context": requests[-1].teaching_context,
            "profile": requests[-1].profile,
        }
        payload = deepcopy(saved.payload)
        out = payload["parent_outcome"]
        draft = out["drafts"][0]
        row = draft["assertion_provenance"]["assertions"][0]
        source = row["sources"][0]
        diagnosis = {
            "version": "assertion_revision_diagnosis_v1",
            "parent_outcome_sha256": revision.canonical_sha256(out),
            "request_binding_sha256": revision.request_sha256(requests[-1]),
            "source_bank_sha256": revision.canonical_sha256(
                assertions.source_bank(out["attribution"]["fragments"], out["evidence"])
            ),
            "targets": [
                {
                    "claim_id": row["claim_id"],
                    "prior_binding_sha256": revision.binding_sha256(row),
                    "kind": "unsupported_assertion",
                    "requirement_ids": [
                        r["id"]
                        for r in out["token_budget"]["context_coverage"]["packed_coverage"][
                            "requirements"
                        ]
                    ],
                    "support_quotes": [
                        {
                            "source_id": source["source_id"],
                            "text_sha256": source["text_sha256"],
                            "quote": source["exact_text"],
                        }
                    ],
                    "reason": "Independent authored diagnosis: no-light statement contradicts the captured light-energy source.",
                }
            ],
        }
        from app.modules.identity.models import User

        actor = db.get(User, req.owner_id)
        fixture[3]["admission"] = {
            "parent_request_id": req.id,
            "saved_failure_id": saved.id,
            "diagnosis": diagnosis,
            "owner_id": req.owner_id,
        }
        child = (
            service.submit_assertion_revision(
                db,
                rt.settings,
                actor,
                parent_request_id=req.id,
                saved_failure_id=saved.id,
                diagnosis=diagnosis,
            )
            if admit
            else None
        )
    return receipt, child


def test_native_revision_publishes_only_after_whole_recheck_and_cannot_repeat(authored_revision):
    rt, calls, requests, _ = authored_revision
    parent, child = failed_parent(authored_revision)
    assert rt.work()
    job = call(rt, "GET", "/jobs/" + child["job_id"])
    assert job["state"] == "succeeded", job
    answer = call(rt, "GET", "/answers/" + job["answer_id"])
    assert "captures light energy" in answer["response"]["answer_text"]
    assert len(calls) == 4
    with rt.db() as db:
        old = db.get(AnswerRequest, parent["request_id"])
        new = db.get(AnswerRequest, child["request_id"])
        assert old.state == "error" and old.budget["consumed_calls"] == 2
        assert new.budget["consumed_calls"] == 4
        assert not service.can_retry(db, new) and not service.can_retry(db, old)
        assert db.scalar(select(Answer).where(Answer.request_id == old.id)) is None
    assert not rt.work()
    call(rt, "GET", "/jobs/" + child["job_id"])
    assert len(calls) == 4


@pytest.mark.parametrize(
    "fault",
    [
        "cancel_queued",
        "cancel_inflight",
        "source_epoch",
        "source_inflight",
        "disabled",
        "recheck_rejected",
        "unknown_timeout",
        "stale_inflight",
    ],
)
def test_native_revision_terminal_boundaries_never_repeat(authored_revision, fault):
    from datetime import timedelta
    from app.db.base import utcnow
    from app.worker import recover_stale
    from app.modules.knowledge.models import RetrievalEpoch

    rt, calls, requests, control = authored_revision
    parent, child = failed_parent(authored_revision)
    if fault == "cancel_queued":
        call(rt, "POST", "/jobs/" + child["job_id"] + "/cancel", {})
    elif fault == "cancel_inflight":
        control["during_revision"] = lambda: call(
            rt, "POST", "/jobs/" + child["job_id"] + "/cancel", {}
        )
    elif fault in {"source_epoch", "source_inflight"}:

        def change_source():
            with rt.db() as db:
                epoch = db.get(RetrievalEpoch, 1)
                epoch.token = str(uuid4())
                db.commit()

        if fault == "source_epoch":
            change_source()
        else:
            control["during_revision"] = change_source
    elif fault == "disabled":
        rt.settings.experimental_assertion_revision_enabled = False
    elif fault == "recheck_rejected":
        control["reject_recheck"] = True
    elif fault == "unknown_timeout":
        control["timeout"] = True
    elif fault == "stale_inflight":

        def stale():
            with rt.db() as db:
                row = db.get(Job, child["job_id"])
                row.updated_at = utcnow() - timedelta(seconds=120)
                db.commit()
            assert recover_stale(rt.engine, 60) == 1

        control["during_revision"] = stale
    if fault == "cancel_queued":
        assert not rt.work()
    else:
        assert rt.work()
    job = call(rt, "GET", "/jobs/" + child["job_id"])
    assert job["state"] in {"failed", "cancelled"}, job
    assert job["answer_id"] is None
    expected = (
        2
        if fault in {"cancel_queued", "source_epoch", "disabled"}
        else 4
        if fault == "recheck_rejected"
        else 3
    )
    assert len(calls) == expected
    with rt.db() as db:
        child_request = db.get(AnswerRequest, child["request_id"])
        assert not service.can_retry(db, child_request)
        assert db.scalar(select(Answer).where(Answer.request_id == child_request.id)) is None
        assert db.get(AnswerRequest, parent["request_id"]).budget["consumed_calls"] == 2
    assert not rt.work()
    call(rt, "GET", "/jobs/" + child["job_id"])
    assert len(calls) == expected


def test_native_duplicate_admission_keeps_one_child(authored_revision):
    from app.core.exceptions import AppError
    from app.modules.identity.models import User
    from sqlalchemy import func

    rt, calls, _, control = authored_revision
    parent, child = failed_parent(authored_revision)
    with rt.db() as db:
        args = deepcopy(control["admission"])
        actor = db.get(User, args.pop("owner_id"))
        with pytest.raises(AppError):
            service.submit_assertion_revision(db, rt.settings, actor, **args)
        db.rollback()
        assert (
            db.scalar(
                select(func.count())
                .select_from(AnswerRequest)
                .where(
                    AnswerRequest.route
                    == service.ASSERTION_CONTINUATION_ROUTE + parent["request_id"]
                )
            )
            == 1
        )
    call(rt, "POST", "/jobs/" + child["job_id"] + "/cancel", {})
    with rt.db() as db:
        args = deepcopy(control["admission"])
        actor = db.get(User, args.pop("owner_id"))
        with pytest.raises(AppError):
            service.submit_assertion_revision(db, rt.settings, actor, **args)
    assert len(calls) == 2 and not rt.work()


def test_native_concurrent_admission_creates_exactly_one_child(authored_revision):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from app.core.exceptions import AppError
    from app.modules.identity.models import User
    from sqlalchemy import func

    rt, calls, _, control = authored_revision
    parent, _ = failed_parent(authored_revision, admit=False)
    barrier = Barrier(2)

    def admit():
        with rt.db() as db:
            args = deepcopy(control["admission"])
            actor = db.get(User, args.pop("owner_id"))
            barrier.wait(timeout=10)
            try:
                return service.submit_assertion_revision(db, rt.settings, actor, **args)
            except AppError as exc:
                return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(admit) for _ in range(2)]
        results = [f.result(timeout=20) for f in futures]
    successes = [r for r in results if isinstance(r, dict)]
    assert len(successes) == 1 and results.count("CONFLICT") == 1, results
    with rt.db() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(AnswerRequest)
                .where(
                    AnswerRequest.route
                    == service.ASSERTION_CONTINUATION_ROUTE + parent["request_id"]
                )
            )
            == 1
        )
    call(rt, "POST", "/jobs/" + successes[0]["job_id"] + "/cancel", {})
    assert len(calls) == 2 and not rt.work()


@pytest.mark.parametrize(
    "question,kind",
    [
        ("Compare photosynthesis with the claim that light is unnecessary.", "concept_comparison"),
        ("Calculate the energy stored by photosynthesis in 2 plants.", "simple_calculation"),
    ],
)
@pytest.mark.parametrize("preparer", ["recorded", "anchored_reference_v25"])
def test_scoped_task_uses_native_revision_and_preserves_identity(
    authored_revision, question, kind, preparer
):
    """Authored semantic results exercise lifecycle only, not question-answer accuracy."""
    from generation.assertion_task_scope import KEY, valid

    rt, calls, requests, _ = authored_revision
    rt.settings.experimental_current_reference_enabled = True
    rt.settings.chat_query_preparation_policy = preparer
    parent, child = failed_parent(authored_revision, question=question)
    original = requests[0]
    assert original.question == question
    assert original.teaching_context["task_type"] == kind
    assert valid(original.teaching_context)
    assert rt.work()
    job = call(rt, "GET", "/jobs/" + child["job_id"])
    assert job["state"] == "succeeded", job
    assert len(calls) == 4 and calls[2] == revision.PROPOSAL_SCHEMA
    continued = requests[-1]
    assert continued.question == question
    assert continued.teaching_context["task_type"] == kind
    assert continued.teaching_context[KEY] == original.teaching_context[KEY]
    with rt.db() as db:
        old = db.get(AnswerRequest, parent["request_id"])
        new = db.get(AnswerRequest, child["request_id"])
        assert old.state == "error" and new.budget["consumed_calls"] == 4
        assert not service.can_retry(db, new) and not service.can_retry(db, old)
    assert not rt.work() and len(calls) == 4
