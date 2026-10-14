"""Isolated real API freezing and native consumer scope controls; no providers."""

from copy import deepcopy
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import sessionmaker

from app.cli import seed
from app.core.config import Settings
from app.core.exceptions import AppError
from app.db.base import Base
from app.main import create_app
from app.modules.answering.models import AnswerRequest
from app.modules.answering.qualification_transport import generation_fields, question_hash
from generation.source_relations_v2 import validate_checker_schema_request, CheckerSchemaScopeError
from generation.types import GenerationRequest, ModelConfig

QUESTION = "What is photosynthesis?"
POLICIES = dict(chat_checker_schema_policy="textbook_context_qualification_v1",
                chat_source_relation_policy="source_relation_contract_v2")


@pytest.fixture
def api(tmp_path):
    settings = Settings(_env_file=None, env="test",
                        database_url="sqlite:///" + str(tmp_path / "native129.db"),
                        jwt_secret="native129-isolated-testing-at-least-32-characters",
                        storage_root=str(tmp_path / "storage"),
                        chat_query_preparation_policy="recorded", **POLICIES)
    app = create_app(settings)
    Base.metadata.create_all(app.state.engine)
    factory = sessionmaker(bind=app.state.engine, expire_on_commit=False)
    with factory() as db:
        seed(db)
    with TestClient(app) as client:
        login = client.post("/api/v1/auth/login", json={"email": "student@example.com",
                                                      "password": "Passw0rd!"})
        assert login.status_code == 200
        headers = {"Authorization": "Bearer " + login.json()["data"]["access_token"]}
        session = client.post("/api/v1/sessions", json={"title": "Isolated transport"}, headers=headers)
        assert session.status_code == 200, session.text
        sid = session.json()["data"]["id"]
        yield client, settings, factory, headers, sid
    app.state.engine.dispose()


def bind(settings, sid):
    # The normal API creates the isolated session before the experiment binds it.
    values = settings.model_dump()
    values.update(chat_qualification_source_transport="ordinary_qa_compact_v2",
                  chat_qualification_transport_session_id=sid,
                  chat_qualification_transport_question_sha256=question_hash(QUESTION))
    validated = Settings(_env_file=None, **values)
    for key in values:
        setattr(settings, key, getattr(validated, key))


def send(api, content=QUESTION, **extra):
    client, _, _, headers, sid = api
    with patch("generation.adapters.LLMAdapter.generate", side_effect=AssertionError("No model call")):
        return client.post(f"/api/v1/sessions/{sid}/messages",
                           json={"content": content, "use_profile": False, **extra},
                           headers={**headers, "Idempotency-Key": "native129-one"})


def native_request(command, sid):
    return GenerationRequest(request_id="isolated", mode="interactive_chat", condition="E1",
        question=command["question"], answer_mode=command["answer_mode"],
        config=ModelConfig.from_dict(command["model_config"]),
        checker_config=ModelConfig.from_dict(command["checker_config"]),
        reliability_policy=command["reliability_policy"],
        checker_schema_policy=command["checker_schema_policy"],
        source_relation_policy=command["source_relation_policy"],
        joint_checker_policy=command["joint_checker_policy"],
        teaching_context=command["teaching_context"], **generation_fields(command, sid))


def test_normal_api_freezes_exact_binding_and_native_consumer_survives_settings_change(api):
    _, settings, factory, _, sid = api
    bind(settings, sid)
    response = send(api)
    assert response.status_code == 202, response.text
    with factory() as db:
        command = deepcopy(db.get(AnswerRequest, response.json()["data"]["request_id"]).command)
    assert command["qualification_source_transport"] == "ordinary_qa_compact_v2"
    assert command["qualification_transport_binding"]["question_sha256"] == question_hash(QUESTION)
    settings.chat_qualification_source_transport = None
    request = native_request(command, sid)
    assert request.qualification_source_transport == "ordinary_qa_compact_v2"
    validate_checker_schema_request(request)
    for changed in (dict(question="Different question"),
                    dict(qualification_source_transport="unknown")):
        with pytest.raises(AppError):
            generation_fields({**command, **changed}, sid)
    with pytest.raises(AppError):
        generation_fields(command, "another-session")
    missing_transport = deepcopy(command)
    del missing_transport["qualification_source_transport"]
    with pytest.raises(AppError):
        generation_fields(missing_transport, sid)


def test_default_normal_api_preserves_absent_command_and_legacy_native_default(api):
    _, _, factory, _, sid = api
    response = send(api)
    assert response.status_code == 202, response.text
    with factory() as db:
        command = db.get(AnswerRequest, response.json()["data"]["request_id"]).command
        assert "qualification_source_transport" not in command
        assert "qualification_transport_binding" not in command
        assert native_request(command, sid).qualification_source_transport == "legacy_origin_v2"


@pytest.mark.parametrize("extra,question", [({}, "Different question"),
    ({"answer_mode": "general"}, QUESTION), ({"teaching_mode": "hint"}, QUESTION)])
def test_bound_api_rejects_out_of_scope_without_dispatch(api, extra, question):
    bind(api[1], api[4])
    response = send(api, question, **extra)
    assert response.status_code in {409, 422}, response.text
    with api[2]() as db:
        from sqlalchemy import select
        assert db.scalar(select(AnswerRequest.id)) is None


def test_other_session_keeps_legacy(api):
    bind(api[1], "another-session")
    response = send(api)
    assert response.status_code == 202, response.text
    with api[2]() as db:
        command = db.get(AnswerRequest, response.json()["data"]["request_id"]).command
        assert "qualification_source_transport" not in command


def test_real_worker_constructs_bound_generation_request_without_provider_dispatch(api):
    from app.worker import run_once
    from generation.types import GenerationOutcome

    client, settings, factory, _, sid = api
    bind(settings, sid)
    response = send(api)
    assert response.status_code == 202, response.text
    seen = []

    def stop_at_generation(service, request, budget, **kwargs):
        seen.append(request)
        validate_checker_schema_request(request)
        return GenerationOutcome(error={"code": "FREE_CONTROL_STOP", "message": "Authored stop",
                                        "retryable": False, "details": {}},
                                 budget=budget.to_dict())

    with patch("app.modules.answering.service.GenerationService.generate", stop_at_generation):
        assert run_once(client.app.state.engine, settings)
    assert len(seen) == 1
    assert seen[0].qualification_source_transport == "ordinary_qa_compact_v2"
    with factory() as db:
        frozen = db.get(AnswerRequest, response.json()["data"]["request_id"])
        assert frozen.command["qualification_transport_binding"]["session_id"] == sid
        from app.modules.answering.models import Job
        job = db.get(Job, response.json()["data"]["job_id"])
        assert job.error["code"] == "FREE_CONTROL_STOP"


@pytest.mark.parametrize("values", [
    dict(chat_qualification_source_transport="ordinary_qa_compact_v2"),
    dict(chat_qualification_transport_session_id="x"),
    dict(chat_qualification_source_transport="ordinary_qa_compact_v2",
         chat_qualification_transport_session_id="x",
         chat_qualification_transport_question_sha256="bad"),
    dict(chat_qualification_source_transport="ordinary_qa_compact_v2",
         chat_qualification_transport_session_id="x",
         chat_qualification_transport_question_sha256=question_hash(QUESTION),
         chat_checker_schema_policy=None),
])
def test_settings_reject_incomplete_or_incompatible_binding(values):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{**POLICIES, **values})


@pytest.mark.parametrize("change", [dict(condition="E0"), dict(answer_mode="general"),
    dict(reading_context={"selection": "x"}),
    dict(teaching_context={"teaching_mode": "hint", "help_level": 1}),
    dict(teaching_context={"teaching_mode": "direct", "help_level": 0, "control_evidence": True})])
def test_existing_engine_guard_still_rejects_invalid_native_scope(change):
    request = GenerationRequest(request_id="control", mode="interactive_chat", condition="E1",
        question=QUESTION, config=ModelConfig(structured_output_mode="json_object"),
        reliability_policy="evidence_reliability_v5", source_relation_policy="source_relation_contract_v2",
        checker_schema_policy="textbook_context_qualification_v1",
        qualification_source_transport="ordinary_qa_compact_v2",
        teaching_context={"teaching_mode": "direct", "help_level": 0})
    for key, value in change.items():
        setattr(request, key, value)
    with pytest.raises(CheckerSchemaScopeError):
        validate_checker_schema_request(request)
