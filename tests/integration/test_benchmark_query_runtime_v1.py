"""Authored native producer/worker PostgreSQL checks; semantic ratings remain zero."""

from copy import deepcopy

import pytest
from sqlalchemy import select

from app.core.exceptions import AppError
from app.modules.answering import service as answering
from app.modules.answering.models import Answer, AnswerRequest
from app.modules.experiment.bridge import validate_request_environment
from app.modules.knowledge import service as knowledge
from app.modules.knowledge.models import Configuration, CorpusRelease, ReleaseChunk
from evaluation.runner import EvaluationRun
from generation import benchmark_query_runtime_v1 as policy
from tests.integration.test_evaluation_postgres import config
from tests.integration.test_evaluation_postgres import evaluation_backend as evaluation_backend


def declare(runtime, backend, device="cpu"):
    with runtime.db() as db:
        prior = db.get(Configuration, backend.configuration_id)
        row = knowledge.config_create(
            db,
            "evaluation",
            "Authored benchmark runtime",
            {
                **prior.values,
                policy.CONFIGURATION_FIELD: {"version": policy.VERSION, "device": device},
            },
        )
        backend.configuration_id = row.id
        db.commit()
    return row.id


@pytest.mark.parametrize("protocol", ["sciq_openqa", "sciq_mcq"])
def test_native_e1_cpu_freezes_and_executes_without_changing_corpus(
    runtime, evaluation_backend, tmp_path, monkeypatch, protocol
):
    backend, _ = evaluation_backend
    configuration_id = declare(runtime, backend)
    original_retrieve = answering.retrieve
    calls = []

    def observed_retrieve(*args, **kwargs):
        calls.append(deepcopy(kwargs))
        return original_retrieve(*args, **kwargs)

    monkeypatch.setattr(answering, "retrieve", observed_retrieve)
    with runtime.db() as db:
        before = [
            (r.id, deepcopy(r.configuration), deepcopy(r.manifest))
            for r in db.scalars(select(CorpusRelease))
        ]
        vectors = [
            (r.release_id, r.chunk_id, list(r.embedding)) for r in db.scalars(select(ReleaseChunk))
        ]
    run = EvaluationRun.freeze(config(tmp_path, protocol, limit=1), backend)
    runtime.settings.local_model_device = "cuda"
    assert run.advance(backend)["status"] == "completed"
    assert len(calls) == 1 and calls[0]["runtime_device"] == "cpu"
    assert calls[0]["variant"] == "R0" and calls[0]["top_k"] == 1
    with runtime.db() as db:
        req = db.scalar(select(AnswerRequest).where(AnswerRequest.run_id == run.manifest["run_id"]))
        frozen = policy.freeze(db.get(Configuration, configuration_id))
        assert req.command[policy.COMMAND_FIELD] == frozen
        assert req.command["retriever"] == "R0" and req.command["condition"] == "E1"
        assert (
            req.command["top_k"] == 1
            and req.release_id == run.manifest["environment"]["corpus_release_id"]
        )
        assert req.trace["local_model_execution"]["requested_device"] == "cpu"
        assert req.trace["local_model_execution"]["resolved_device"] == "cpu"
        assert req.trace["local_model_execution"][policy.COMMAND_FIELD] == frozen
        assert req.budget["max_calls"] == 4 and req.budget["max_active_seconds"] == 180
        assert before == [
            (r.id, deepcopy(r.configuration), deepcopy(r.manifest))
            for r in db.scalars(select(CorpusRelease))
        ]
        assert vectors == [
            (r.release_id, r.chunk_id, list(r.embedding)) for r in db.scalars(select(ReleaseChunk))
        ]


@pytest.mark.parametrize("protocol", ["sciq_openqa", "sciq_mcq"])
def test_native_e0_declared_cpu_still_never_retrieves(
    runtime, evaluation_backend, tmp_path, monkeypatch, protocol
):
    backend, _ = evaluation_backend
    declare(runtime, backend)

    def forbidden(*args, **kwargs):
        raise AssertionError("E0 must retain zero retrieval")

    monkeypatch.setattr(answering, "retrieve", forbidden)
    run = EvaluationRun.freeze({**config(tmp_path, protocol, limit=1), "condition": "E0"}, backend)
    assert run.advance(backend)["status"] == "completed"
    with runtime.db() as db:
        req = db.scalar(select(AnswerRequest).where(AnswerRequest.run_id == run.manifest["run_id"]))
        assert req.command[policy.COMMAND_FIELD]["device"] == "cpu"
        assert req.command["retriever"] is None and req.release_id is None
        assert req.trace["retrieval_candidates"] == []
        assert "local_model_execution" not in req.trace


def test_native_legacy_missing_policy_remains_recorded(
    runtime, evaluation_backend, tmp_path, monkeypatch
):
    backend, _ = evaluation_backend
    original = answering.retrieve
    calls = []

    def observed(*args, **kwargs):
        calls.append(deepcopy(kwargs))
        return original(*args, **kwargs)

    monkeypatch.setattr(answering, "retrieve", observed)
    runtime.settings.local_model_device = "cpu"
    run = EvaluationRun.freeze(config(tmp_path, limit=1), backend)
    assert run.advance(backend)["status"] == "completed"
    assert len(calls) == 1 and "runtime_device" not in calls[0]
    with runtime.db() as db:
        req = db.scalar(select(AnswerRequest).where(AnswerRequest.run_id == run.manifest["run_id"]))
        assert policy.COMMAND_FIELD not in req.command
        assert req.trace["local_model_execution"] == {
            "requested_device": "recorded",
            "resolved_device": None,
            "scope": "query embedding and interactive reranking; corpus unchanged",
        }


@pytest.mark.parametrize("device", ["gpu", "cuda:1", False])
def test_native_unknown_declaration_rejected_before_submission(
    runtime, evaluation_backend, tmp_path, device
):
    backend, _ = evaluation_backend
    declare(runtime, backend, device)
    with pytest.raises(AppError, match="Unsupported benchmark"):
        EvaluationRun.freeze(config(tmp_path, limit=1), backend)
    with runtime.db() as db:
        assert not list(
            db.scalars(
                select(AnswerRequest).where(AnswerRequest.config_id == backend.configuration_id)
            )
        )


@pytest.mark.parametrize("defect", ["device", "configuration_id", "missing"])
def test_native_replay_rejects_tampered_policy_before_generation(
    runtime, evaluation_backend, tmp_path, defect
):
    backend, _ = evaluation_backend
    declare(runtime, backend)
    run = EvaluationRun.freeze(config(tmp_path, limit=1), backend)
    key = f"evaluation:{run.manifest['run_id']}:{run.commands[0]['item_id']}"
    backend.register_run(run.manifest)
    receipt = backend.submit(run.commands[0], run_context=run.manifest, idempotency_key=key)
    with runtime.db() as db:
        req = db.get(AnswerRequest, receipt["request_id"])
        command = deepcopy(req.command)
        if defect == "missing":
            command.pop(policy.COMMAND_FIELD)
        else:
            command[policy.COMMAND_FIELD][defect] = "foreign"
        req.command = command
        with pytest.raises(AppError):
            validate_request_environment(db, runtime.settings, req)
        db.commit()
    outcome = backend.poll(receipt)
    assert outcome["status"] == "error"
    with runtime.db() as db:
        req = db.get(AnswerRequest, receipt["request_id"])
        assert req.budget["consumed_calls"] == 0
        assert not list(db.scalars(select(Answer).where(Answer.request_id == req.id)))
