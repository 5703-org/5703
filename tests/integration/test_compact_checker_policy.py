"""Durable request/worker policy snapshots against actual disposable PostgreSQL."""

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.modules.answering import service
from app.modules.answering.models import AnswerRequest
from .test_chat_runtime import corpus, session, submit


@pytest.mark.parametrize("submitted", ["typed_joint_v5", "scoped_compact_v6", "scoped_compact_v7"])
def test_submitted_checker_policy_survives_later_setting_change(runtime, submitted):
    rt = runtime
    corpus(rt)
    rt.settings.chat_joint_checker_policy = submitted
    receipt = submit(rt, session(rt), "What is photosynthesis?")
    with rt.db() as db:
        frozen = dict(db.get(AnswerRequest, receipt["request_id"]).command)
        assert frozen["joint_checker_policy"] == submitted
    rt.settings.chat_joint_checker_policy = (
        "typed_joint_v5" if submitted == "scoped_compact_v6" else "scoped_compact_v6"
    )
    with patch.object(
        service.GenerationService, "generate", side_effect=RuntimeError("BOUNDARY_TEST_STOP")
    ) as generated:
        assert rt.work()
    assert generated.call_args.args[0].joint_checker_policy == submitted
    with rt.db() as db:
        row = db.get(AnswerRequest, receipt["request_id"])
        assert row.command == frozen
        assert row.budget["consumed_calls"] == 0


def test_old_command_without_checker_axis_preserves_v5(runtime):
    rt = runtime
    corpus(rt)
    receipt = submit(rt, session(rt), "What is photosynthesis?")
    with rt.db() as db:
        row = db.get(AnswerRequest, receipt["request_id"])
        frozen = dict(row.command)
        frozen.pop("joint_checker_policy")
        row.command = frozen
        db.commit()
    rt.settings.chat_joint_checker_policy = "scoped_compact_v6"
    with patch.object(
        service.GenerationService, "generate", side_effect=RuntimeError("BOUNDARY_TEST_STOP")
    ) as generated:
        assert rt.work()
    assert generated.call_args.args[0].joint_checker_policy == "typed_joint_v5"
    with rt.db() as db:
        assert db.get(AnswerRequest, receipt["request_id"]).command == frozen


@pytest.mark.parametrize("policy", ["scoped_compact_v6", "scoped_compact_v7"])
def test_startup_rejects_combined_checker_contracts(policy):
    with pytest.raises(ValidationError, match="cannot combine"):
        Settings(
            _env_file=None,
            chat_joint_checker_policy=policy,
            chat_source_relation_policy="source_relation_contract_v1",
        )
