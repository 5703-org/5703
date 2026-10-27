from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.web import mount_application


@pytest.fixture
def client(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><title>Runtime application</title>")
    (dist / "assets").mkdir()
    (dist / "assets" / "app.js").write_text('console.log("application");')
    (tmp_path / ".env").write_text("PRIVATE_PLACEHOLDER_NOT_A_CREDENTIAL")
    app = FastAPI()

    @app.get("/api/v1/example")
    def example():
        return {"data": "native"}

    mount_application(app, dist)
    return TestClient(app)


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/login",
        "/chat/a-session",
        "/learn/library/a-book",
        "/learn/%invalid",
        "/unknown-route",
    ],
)
def test_client_routes_have_real_shell_and_security_headers(client, path):
    result = client.get(path)
    assert result.status_code == 200 and "Runtime application" in result.text
    assert result.headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in result.headers["Content-Security-Policy"]
    assert result.headers["Cache-Control"] == "no-cache"


@pytest.mark.parametrize(
    "path",
    [
        "/api/unknown",
        "/api/v1/unknown",
        "/assets/missing.js",
        "/missing.js",
        "/.env",
        "/%2e%2e/.env",
        "/assets/.env",
    ],
)
def test_api_missing_assets_and_private_paths_never_receive_shell(client, path):
    result = client.get(path)
    assert result.status_code == 404
    assert "PRIVATE_PLACEHOLDER" not in result.text and "Runtime application" not in result.text


def test_existing_api_and_asset_unchanged(client):
    assert client.get("/api/v1/example").json() == {"data": "native"}
    assert client.get("/assets/app.js").status_code == 200


def test_unsupported_write_method_not_spa_success(client):
    assert client.post("/chat").status_code == 405


def test_missing_dist_is_not_fake_healthy_site(tmp_path):
    app = FastAPI()
    mount_application(app, tmp_path / "missing")
    assert TestClient(app).get("/").status_code == 404
