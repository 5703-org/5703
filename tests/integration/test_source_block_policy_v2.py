"""Authored API/worker policy persistence on disposable PostgreSQL; no quality labels."""

from copy import deepcopy
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.modules.answering import service
from app.modules.answering.models import AnswerRequest, Job
from generation.adapters import LLMAdapter
from retrieval.source_spans_v2 import VERSION
from .test_chat_runtime import call, corpus, session, submit


def test_new_policy_is_server_owned_and_invalid_settings_fail(runtime):
    assert Settings(_env_file=None).chat_source_block_policy == VERSION
    with pytest.raises(ValidationError):
        Settings(_env_file=None, chat_source_block_policy="unknown")
    s = session(runtime)
    call(
        runtime,
        "POST",
        f"/sessions/{s['id']}/messages",
        {
            "content": "Explain the source",
            "source_block_policy": "legacy_source_blocks_v1",
        },
        status=422,
    )


def test_new_policy_freezes_through_worker_settings_change_and_retry(runtime):
    rt = runtime
    corpus(rt)
    rt.settings.chat_source_block_policy = VERSION
    receipt = submit(rt, session(rt))
    with rt.db() as db:
        frozen = deepcopy(db.get(AnswerRequest, receipt["request_id"]).command)
    assert frozen["source_block_policy"] == VERSION
    rt.settings.chat_source_block_policy = "legacy_source_blocks_v1"
    with patch.object(
        service.GenerationService, "generate", side_effect=RuntimeError("AUTHORED_STOP")
    ) as generate:
        assert rt.work()
    assert generate.call_args.args[0].source_block_policy == VERSION
    retry = call(
        rt,
        "POST",
        "/answer-requests/" + receipt["request_id"] + "/retry",
        {},
        {**rt.headers(), "Idempotency-Key": "source-block-policy-retry"},
        202,
    )
    assert retry["request_id"] == receipt["request_id"]
    with patch.object(
        service.GenerationService, "generate", side_effect=RuntimeError("AUTHORED_STOP")
    ) as generate:
        assert rt.work()
    assert generate.call_args.args[0].source_block_policy == VERSION
    with rt.db() as db:
        assert db.get(AnswerRequest, receipt["request_id"]).command == frozen


def test_missing_historical_policy_remains_legacy(runtime):
    rt = runtime
    corpus(rt)
    receipt = submit(rt, session(rt))
    with rt.db() as db:
        req = db.get(AnswerRequest, receipt["request_id"])
        command = dict(req.command)
        command.pop("source_block_policy")
        req.command = command
        db.commit()
    rt.settings.chat_source_block_policy = VERSION
    with patch.object(
        service.GenerationService, "generate", side_effect=RuntimeError("AUTHORED_STOP")
    ) as generate:
        assert rt.work()
    assert generate.call_args.args[0].source_block_policy == "legacy_source_blocks_v1"
    with rt.db() as db:
        assert db.get(AnswerRequest, receipt["request_id"]).command == command


def test_unknown_frozen_policy_fails_before_answer_model(runtime):
    rt = runtime
    corpus(rt)
    receipt = submit(rt, session(rt))
    with rt.db() as db:
        req = db.get(AnswerRequest, receipt["request_id"])
        req.command = {**req.command, "source_block_policy": "unknown"}
        db.commit()
    with patch.object(LLMAdapter, "generate", side_effect=AssertionError("NO_MODEL_CALL")) as model:
        assert rt.work()
        model.assert_not_called()
    with rt.db() as db:
        job = db.get(Job, receipt["job_id"])
        assert job.state == "failed"
        assert db.get(AnswerRequest, receipt["request_id"]).budget["consumed_calls"] == 0
