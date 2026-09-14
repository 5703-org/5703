"""Test fixtures: isolated app + isolated database (Spec A02, A07)."""
from __future__ import annotations

import tempfile

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db import session as db_session
from app.db.base import Base
from app.main import create_app
from app.modules.identity import models as _identity_models  # noqa: F401
from app.modules.learning import models as _learning_models  # noqa: F401
from app.platform_core import models as _platform_models  # noqa: F401
from scripts.seed import seed


@pytest.fixture(scope="session")
def settings() -> Settings:
    tmp = tempfile.mkdtemp(prefix="ala-test-")
    return Settings(env="test", database_url=f"sqlite:///{tmp}/test.db", jwt_secret="test-secret")


@pytest.fixture(scope="session")
def app(settings):
    application = create_app(settings)
    Base.metadata.create_all(db_session.get_engine())
    with db_session.session_scope() as db:
        seed(db)
    return application


@pytest.fixture(scope="session")
def client(app):
    with TestClient(app) as test_client:
        yield test_client


def login_headers(client: TestClient, email: str, password: str = "Passw0rd!") -> dict:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def admin_headers(client) -> dict:
    return login_headers(client, "admin@example.com")


@pytest.fixture(scope="session")
def student_headers(client) -> dict:
    return login_headers(client, "student@example.com")


@pytest.fixture(scope="session")
def student2_headers(client) -> dict:
    return login_headers(client, "student2@example.com")
