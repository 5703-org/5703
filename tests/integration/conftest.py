"""Disposable PostgreSQL application fixtures with real migrations and worker."""

from contextlib import contextmanager
import os
from pathlib import Path
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from alembic.config import Config
from alembic import command
from app.core.config import Settings
from app.main import create_app
from app.cli import seed
from app.worker import run_once

ROOT = Path(__file__).resolve().parents[2]


@contextmanager
def disposable_postgres_url():
    """Create, migrate and dispose one randomly named test database."""
    base = os.environ["TEST_DATABASE_SERVER"]
    admin = create_engine(base + "/postgres", isolation_level="AUTOCOMMIT")
    name = "cs30_test_" + uuid4().hex[:12]
    created = False
    try:
        with admin.connect() as db:
            db.execute(text(f"CREATE DATABASE {name}"))
        created = True
        url = base + "/" + name
        previous = os.environ.get("DATABASE_URL")
        try:
            os.environ["DATABASE_URL"] = url
            command.upgrade(Config(str(ROOT / "backend/alembic.ini")), "head")
        finally:
            if previous is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = previous
        yield url
    finally:
        try:
            if created:
                with admin.connect() as db:
                    db.execute(
                        text(
                            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=:name AND pid<>pg_backend_pid()"
                        ),
                        {"name": name},
                    )
                    db.execute(text(f"DROP DATABASE {name}"))
        finally:
            admin.dispose()


@pytest.fixture(scope="session")
def postgres_url():
    with disposable_postgres_url() as url:
        yield url


@pytest.fixture
def runtime(postgres_url, tmp_path):
    settings = Settings(
        _env_file=None,
        env="test",
        database_url=postgres_url,
        model_mode="mock",
        llm_provider="mock",
        llm_api_key=None,
        jwt_secret="independent-test-secret-at-least-thirty-two-characters",
        storage_root=str(tmp_path / "storage"),
        mock_delay_seconds=0,
        local_model_device="recorded",
        chat_relevance_gate=False,
        chat_retrieval_cache=False,
        chat_query_preparation_policy="recorded",
    )
    app = create_app(settings)
    factory = sessionmaker(bind=app.state.engine, expire_on_commit=False)
    with factory() as db:
        seed(db)
    client = TestClient(app)

    def headers(email="student@example.com"):
        result = client.post("/api/v1/auth/login", json={"email": email, "password": "Passw0rd!"})
        assert result.status_code == 200, result.text
        return {"Authorization": "Bearer " + result.json()["data"]["access_token"]}

    class Runtime:
        pass

    value = Runtime()
    value.client = client
    value.engine = app.state.engine
    value.db = factory
    value.settings = settings
    value.headers = headers
    value.work = lambda: run_once(app.state.engine, settings)
    yield value
    client.close()
    app.state.engine.dispose()


@pytest.fixture
def scripted_semantic_checker(monkeypatch):
    """Explicit authored checker for positive teaching-lifecycle tests, not model quality.

    Actual readiness/configuration and publication guards execute unchanged.
    Only the named checker transport is scripted; every other real transport
    is rejected before network I/O. Current admission-negative tests do not opt in. Historical worker-negative
    tests explicitly replace their own frozen checker after valid admission.
    """
    import json
    from app.modules.model_settings import service as model_settings
    from app.modules.learning_product import practice_capability
    from pathlib import Path

    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "unit"))
    from test_answer_core_v5 import checker
    from test_teaching_plan_v8 import pending_checker, data_from
    from generation.adapters import LLMAdapter
    from generation.types import ModelConfig, ProviderResult

    config = ModelConfig(
        provider="openai_compatible",
        model="authored-semantic-checker-local",
        base_url="http://127.0.0.1:9/v1",
        configuration_id="authored-checker-local",
        tokenizer_provider="estimate",
        window_tokens=32000,
        max_tokens=4096,
    )
    for module in (model_settings, practice_capability):
        monkeypatch.setattr(module, "resolve_active_checker_model_config", lambda *args: config)
    original = LLMAdapter.generate
    calls = []

    def generate(adapter, messages, **kwargs):
        if adapter.config.model != config.model:
            assert adapter.config.provider == "mock", "Unscripted external transport is forbidden"
            return original(adapter, messages, **kwargs)
        context = kwargs.get("request_context") or {}
        calls.append(context.get("mode"))
        payload = (
            pending_checker(messages)
            if "PENDING_ACTION_CONTEXT" in data_from(messages)
            else checker(messages)
        )
        return ProviderResult(
            raw_text=json.dumps(payload),
            provider=config.provider,
            model=config.model,
            request_submitted=True,
            finish_reason="stop",
        )

    def forbidden(*args, **kwargs):
        raise AssertionError("Teaching lifecycle fixtures cannot use external transport")

    monkeypatch.setattr(LLMAdapter, "generate", generate)
    monkeypatch.setattr(LLMAdapter, "_call", forbidden)
    return calls


def freeze_legacy_mock_checker(runtime, receipt):
    """Owned historical-command fixture for the worker's independent mock-hint guard.

    New API admission uses a valid authored checker. This deliberate fixture
    mutation reproduces a previously saved mock command, not a real model result.
    """
    from app.modules.answering.models import AnswerRequest
    from generation.types import ModelConfig

    with runtime.db() as db:
        row = db.get(AnswerRequest, receipt["request_id"])
        row.command = {**row.command, "checker_config": ModelConfig().to_dict()}
        db.commit()
