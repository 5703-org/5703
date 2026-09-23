"""Queued chat executes its immutable managed config and sends no environment secret."""

import json
from unittest.mock import patch
import pytest

from generation.adapters import LLMAdapter, chat_value
from generation.types import ProviderResult
from app.modules.answering.models import AnswerRequest, Attempt
from sqlalchemy import select
from .test_chat_runtime import call, corpus, session, submit


@pytest.fixture(autouse=True)
def restore_test_model_pointer_and_cancel_own_jobs(runtime):
    """This shared test database outlives a test; leave no queued work or active fixture model."""
    from app.modules.answering.models import Job
    from app.modules.answering.service import cancel_job
    from app.modules.identity.models import User
    from app.modules.model_settings.models import ActiveModelConfiguration

    with runtime.db() as db:
        before_jobs = set(db.scalars(select(Job.id)))
        workspace_id = db.scalar(select(User.workspace_id).where(User.email == "admin@example.com"))
        pointer = db.get(ActiveModelConfiguration, workspace_id)
        before_model = pointer.configuration_id if pointer else None
        before_checker = pointer.checker_configuration_id if pointer else None
    yield
    with runtime.db() as db:
        for job in db.scalars(
            select(Job).where(Job.state.in_(["queued", "running", "retry_wait"]))
        ):
            if job.id not in before_jobs:
                cancel_job(db, job)
        pointer = db.get(ActiveModelConfiguration, workspace_id)
        if pointer and (
            pointer.configuration_id != before_model
            or pointer.checker_configuration_id != before_checker
        ):
            pointer.configuration_id = before_model
            pointer.checker_configuration_id = before_checker
            pointer.version += 1
        db.commit()


def test_queued_chat_freezes_model_and_transient_secret_boundary(runtime):
    rt = runtime
    corpus(rt)
    admin = rt.headers("admin@example.com")
    prefix = "/admin/model-configurations"

    def configured(name):
        return call(
            rt,
            "POST",
            prefix,
            {
                "name": name,
                "config": {
                    "provider": "local",
                    "model": name,
                    "base_url": "http://localhost:1/v1",
                    "tokenizer_provider": "estimate",
                },
            },
            admin,
            201,
        )

    def activate(value):
        from generation.probes import description

        probe_calls = []

        def scripted_probe(adapter, messages, **kwargs):
            name = kwargs.get("response_schema_name", "compatibility_basic_v2")
            tier = "basic" if name.endswith("basic_v2") else "structured"
            role = "checker" if name == "joint_check_v2" else "answer"
            if name in {"chat_response_v1", "joint_check_v2"}:
                tier = "project"
            assert adapter.config.configuration_id == "model-settings:" + value["id"]
            assert adapter._api_key is None
            probe_calls.append(name)
            authored = description(adapter.config, tier, role)["mock_value"]
            return ProviderResult(
                raw_text=authored if isinstance(authored, str) else json.dumps(authored),
                provider="local",
                model=value["config"]["model"],
                finish_reason="stop",
                request_submitted=True,
            )

        with (
            patch.object(LLMAdapter, "generate_basic", scripted_probe),
            patch.object(LLMAdapter, "generate", scripted_probe),
        ):
            checked = call(rt, "POST", prefix + f"/{value['id']}/test", headers=admin)
            checker = call(rt, "POST", prefix + f"/{value['id']}/test", {"role": "checker"}, admin)
        for receipt in (checked, checker):
            assert receipt["status"] == "passed" and receipt["project_passed"]
            assert [stage["tier"] for stage in receipt["stages"]] == [
                "basic",
                "structured",
                "project",
            ]
        assert probe_calls == [
            "compatibility_basic_v2",
            "compatibility_structured_v2",
            "chat_response_v1",
            "compatibility_basic_v2",
            "compatibility_structured_v2",
            "joint_check_v2",
        ]
        state = call(rt, "GET", prefix, headers=admin)
        call(
            rt,
            "POST",
            prefix + f"/{value['id']}/activate",
            {
                "test_id": checked["id"],
                "checker_test_id": checker["id"],
                "expected_active_version": state["active_version"],
            },
            admin,
        )

    first, second = configured("frozen-A"), configured("later-B")
    activate(first)
    chat = session(rt)
    receipt = submit(rt, chat, "What is photosynthesis? Please give a short answer.")
    activate(second)
    seen = []

    def transport(adapter, messages, **kwargs):
        seen.append((adapter.config, adapter._api_key, kwargs["response_schema_name"]))
        assert adapter.config.configuration_id == "model-settings:" + first["id"]
        assert adapter.config.model == "frozen-A"
        assert adapter._api_key is None
        if kwargs["response_schema_name"] == "joint_check_v2":
            # Scripted association verifies the immutable transport boundary only.
            data = json.loads(messages[-1]["content"])
            value = {
                "claims": [
                    {
                        "claim_id": claim["claim_id"],
                        "factual": True,
                        "status": "supported",
                        "fragment_ids": [data["SOURCE_FRAGMENTS"][0]["fragment_id"]],
                        "basis": "textbook",
                        "problem_quote": None,
                        "derivation": None,
                        "reason": "Scripted fixture association, not semantic validation.",
                    }
                    for claim in data["CLAIMS"]
                ],
                "body_ok": True,
                "specific_help": True,
                "scope_ok": True,
                "suggestions_ok": True,
                "evidence_display_ok": True,
                "cumulative_ok": True,
                "complete_answer": True,
                "coverage": "full",
                "missing_facets": [],
                "limitations_explicit": True,
                "repair_fragment_ids": [],
                "reason": "Scripted checker for configuration freezing.",
            }
        else:
            eid = kwargs["request_context"]["evidence"][0]["evidence_id"]
            value = chat_value(
                "answer",
                f"Photosynthesis captures light energy. [{eid}]",
                short_answer=f"Light energy capture [{eid}]",
                citations=[eid],
            )
        return ProviderResult(
            raw_text=json.dumps(value),
            provider="local",
            model="frozen-A",
            finish_reason="stop",
            request_submitted=True,
        )

    with (
        patch.dict("os.environ", {"LLM_API_KEY": "must-never-enter-managed-request"}),
        patch.object(LLMAdapter, "generate", transport),
    ):
        assert rt.work()
        job = call(rt, "GET", "/jobs/" + receipt["job_id"])
        assert job["state"] == "succeeded", json.dumps(job.get("error"))
        answer = call(rt, "GET", "/answers/" + job["answer_id"])
    assert answer["model_mode"] == "live" and len(seen) == 2
    assert seen[1][2] == "joint_check_v2"
    assert seen[0][0].max_tokens == first["config"]["max_tokens"]
    assert seen[1][0].max_tokens == max(first["config"]["max_tokens"], 4096)
    with rt.db() as db:
        req = db.get(AnswerRequest, receipt["request_id"])
        assert req.command["model_config"]["configuration_id"] == "model-settings:" + first["id"]
        assert req.command["checker_config"]["configuration_id"] == "model-settings:" + first["id"]
        assert req.command["checker_config"]["max_tokens"] == 4096
        assert req.budget["consumed_calls"] == 2
        attempts = db.scalars(select(Attempt).where(Attempt.job_id == receipt["job_id"])).all()
        persisted = json.dumps([req.command, req.trace, *[row.payload for row in attempts]])
        assert "must-never-enter-managed-request" not in persisted
        assert req.trace["evidence_selection"]["cited_count"] == 1
        stages = req.trace["token_budget"]["stage_token_budgets"]
        assert [stage["stage"] for stage in stages] == ["generation", "joint_check"]
        assert all(stage["counter"]["is_estimate"] for stage in stages)
        assert "presentation_policy" in req.trace["model_messages"][0]["content"]


def test_request_and_job_admin_access_stays_in_workspace(runtime):
    from uuid import uuid4
    import pytest
    from app.core.exceptions import AppError
    from app.modules.identity.models import User, Workspace
    from app.modules.answering.service import request_owned, job_owned

    rt = runtime
    receipt = submit(rt, session(rt), "Hello")
    with rt.db() as db:
        admin = db.scalar(select(User).where(User.email == "admin@example.com"))
        workspace = Workspace(name="Foreign test workspace", slug=uuid4().hex)
        db.add(workspace)
        db.flush()
        foreign = User(
            email=uuid4().hex + "@example.invalid",
            full_name="Foreign fixture admin",
            hashed_password=admin.hashed_password,
            role_id=admin.role_id,
            workspace_id=workspace.id,
        )
        db.add(foreign)
        db.commit()
        assert request_owned(db, receipt["request_id"], admin).id == receipt["request_id"]
        assert job_owned(db, receipt["job_id"], admin).id == receipt["job_id"]
        for getter, identity in (
            (request_owned, receipt["request_id"]),
            (job_owned, receipt["job_id"]),
        ):
            with pytest.raises(AppError) as caught:
                getter(db, identity, foreign)
            assert caught.value.code == "NOT_FOUND"


def test_required_tokenizer_failure_rejects_before_saving_user_turn(runtime):
    from app.modules.answering.models import Message
    from sqlalchemy import func
    from uuid import uuid4

    rt = runtime
    chat = session(rt)
    with patch(
        "app.modules.answering.service.TokenCounter",
        side_effect=ValueError("TOKENIZER_UNAVAILABLE"),
    ):
        result = rt.client.post(
            f"/api/v1/sessions/{chat['id']}/messages",
            headers={**rt.headers(), "Idempotency-Key": str(uuid4())},
            json={"content": "What is photosynthesis?", "use_profile": True},
        )
    assert result.status_code == 503 and result.json()["error"]["code"] == "MODEL_UNAVAILABLE"
    with rt.db() as db:
        assert (
            db.scalar(
                select(func.count()).select_from(Message).where(Message.session_id == chat["id"])
            )
            == 0
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(AnswerRequest)
                .where(AnswerRequest.session_id == chat["id"])
            )
            == 0
        )
