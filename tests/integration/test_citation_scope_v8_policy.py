"""V8's saved checker axis is independent of mutable environment settings."""

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.modules.answering import service
from app.modules.answering.models import AnswerRequest
from .test_chat_runtime import corpus, session, submit


def test_opt_in_v8_is_frozen_on_submission_and_replayed_by_worker(runtime):
    rt = runtime
    corpus(rt)
    rt.settings.chat_joint_checker_policy = "scoped_compact_v8"
    receipt = submit(rt, session(rt), "What is photosynthesis?")
    with rt.db() as db:
        frozen = dict(db.get(AnswerRequest, receipt["request_id"]).command)
    assert frozen["joint_checker_policy"] == "scoped_compact_v8"
    rt.settings.chat_joint_checker_policy = "typed_joint_v5"
    with patch.object(
        service.GenerationService, "generate", side_effect=RuntimeError("BOUNDARY_TEST_STOP")
    ) as generated:
        assert rt.work()
    assert generated.call_args.args[0].joint_checker_policy == "scoped_compact_v8"
    with rt.db() as db:
        row = db.get(AnswerRequest, receipt["request_id"])
        assert row.command == frozen and row.budget["consumed_calls"] == 0


def test_v8_rejects_parallel_source_contract_and_keeps_default_v5():
    assert Settings(_env_file=None).chat_joint_checker_policy == "typed_joint_v5"
    with pytest.raises(ValidationError, match="cannot combine"):
        Settings(
            _env_file=None,
            chat_joint_checker_policy="scoped_compact_v8",
            chat_source_relation_policy="source_relation_contract_v2",
        )
