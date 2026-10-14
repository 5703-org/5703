"""Authored disposable API/worker tests; formal source quality remains separate."""

from copy import deepcopy
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.modules.answering import service
from app.modules.answering.models import AnswerRequest
from generation import coverage_v3, coverage_v4
from generation.coverage_query_policy_v1 import VERSION, freeze_policy

from .test_chat_runtime import call, corpus, session, submit


def test_new_settings_keep_auxiliary_lookup_off_and_default_checker_v5():
    settings = Settings(_env_file=None)
    assert settings.chat_coverage_query_policy == "off"
    assert settings.chat_joint_checker_policy == "typed_joint_v5"


@pytest.mark.parametrize(
    "relation,base",
    [
        ("off", coverage_v3),
        ("source_relation_contract_v1", coverage_v4),
        ("source_relation_contract_v2", coverage_v4),
    ],
)
def test_frozen_policy_reaches_worker_supplement_assessor_and_generation_after_live_settings_change(
    runtime, relation, base
):
    rt = runtime
    corpus(rt)
    rt.settings.chat_query_preparation_policy = "anchored_reference_v18"
    rt.settings.chat_source_relation_policy = relation
    rt.settings.chat_coverage_query_policy = VERSION
    receipt = submit(rt, session(rt), "Which energy units describe 2.5 J without heating?")
    with rt.db() as db:
        frozen = deepcopy(db.get(AnswerRequest, receipt["request_id"]).command)
        assert frozen["coverage_query_policy"] == freeze_policy(base.VERSION)
    rt.settings.chat_coverage_query_policy = "off"
    rt.settings.chat_source_relation_policy = (
        "source_relation_contract_v2" if relation == "off" else "off"
    )
    from generation import coverage_v5

    with (
        patch.object(
            coverage_v5, "supplement_once", wraps=coverage_v5.supplement_once
        ) as supplement,
        patch.object(
            coverage_v5, "assess_evidence_coverage", wraps=coverage_v5.assess_evidence_coverage
        ) as assessment,
        patch.object(
            service.GenerationService,
            "generate",
            side_effect=RuntimeError("AUTHORED_BOUNDARY_STOP"),
        ) as generate,
    ):
        assert rt.work()
    value = generate.call_args.args[0]
    assert supplement.call_count == 1
    assert supplement.call_args.kwargs["base_version"] == base.VERSION
    assert assessment.call_count >= 1
    assert all(call.kwargs["base_version"] == base.VERSION for call in assessment.call_args_list)
    assert value.coverage_query_policy == frozen["coverage_query_policy"]
    assert value.source_relation_policy == frozen["source_relation_policy"]
    assert value.question == frozen["question"]
    assert value.understanding["requirement_source_text"] == frozen["question"]
    assert value.evidence_coverage["version"] == "context_coverage_v5"
    assert value.evidence_coverage["base_coverage_version"] == base.VERSION
    with rt.db() as db:
        row = db.get(AnswerRequest, receipt["request_id"])
        assert row.command == frozen
        assert row.budget["consumed_calls"] == 0
        assert row.budget["max_calls"] == 4 and row.budget["max_active_seconds"] == 180


def test_old_command_without_field_stays_v3_after_live_policy_enable(runtime):
    rt = runtime
    corpus(rt)
    rt.settings.chat_source_relation_policy = "off"
    rt.settings.chat_coverage_query_policy = "off"
    receipt = submit(rt, session(rt), "What is photosynthesis?")
    with rt.db() as db:
        frozen = deepcopy(db.get(AnswerRequest, receipt["request_id"]).command)
        assert "coverage_query_policy" not in frozen
    rt.settings.chat_coverage_query_policy = VERSION
    with patch.object(
        service.GenerationService, "generate", side_effect=RuntimeError("AUTHORED_BOUNDARY_STOP")
    ) as generate:
        assert rt.work()
    value = generate.call_args.args[0]
    assert value.coverage_query_policy is None
    assert value.evidence_coverage["version"] == coverage_v3.VERSION
    with rt.db() as db:
        assert db.get(AnswerRequest, receipt["request_id"]).command == frozen


@pytest.mark.parametrize("defect", ["catalog", "base", "unknown", "condition", "source_relation"])
def test_tampered_policy_fails_before_retrieval_or_model_with_retained_failed_job(runtime, defect):
    rt = runtime
    corpus(rt)
    rt.settings.chat_coverage_query_policy = VERSION
    receipt = submit(rt, session(rt), "Which energy units describe 2.5 J without heating?")
    with rt.db() as db:
        row = db.get(AnswerRequest, receipt["request_id"])
        frozen = deepcopy(row.command)
        if defect == "condition":
            frozen["condition"] = "E0"
        elif defect == "source_relation":
            frozen["source_relation_policy"] = "unknown"
        elif defect == "catalog":
            frozen["coverage_query_policy"]["catalog_sha256"] = "0" * 64
        elif defect == "base":
            frozen["coverage_query_policy"]["base_version"] = coverage_v4.VERSION
        else:
            frozen["coverage_query_policy"]["version"] = "unknown"
        row.command = frozen
        db.commit()
    with (
        patch.object(service, "retrieve") as retrieve,
        patch.object(service.GenerationService, "generate") as generate,
    ):
        assert rt.work()
        retrieve.assert_not_called()
        generate.assert_not_called()
    job = call(rt, "GET", "/jobs/" + receipt["job_id"])
    assert job["state"] == "failed" and job.get("answer_id") is None
    with rt.db() as db:
        row = db.get(AnswerRequest, receipt["request_id"])
        assert row.command == frozen and row.budget["consumed_calls"] == 0


def test_client_cannot_override_server_frozen_lookup_policy(runtime):
    rt = runtime
    conversation = session(rt)
    call(
        rt,
        "POST",
        f"/sessions/{conversation['id']}/messages",
        {
            "content": "Hello",
            "use_profile": False,
            "coverage_query_policy": freeze_policy(coverage_v3.VERSION),
        },
        headers={**rt.headers(), "Idempotency-Key": str(uuid4())},
        status=422,
    )
