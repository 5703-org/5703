"""Private API responses have consistent browser and cache protections."""

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_api_responses_disable_cache_and_browser_content_execution(tmp_path):
    app = create_app(
        Settings(
            _env_file=None,
            env="test",
            database_url=f"sqlite:///{tmp_path / 'headers.db'}",
            jwt_secret="test-secret-at-least-thirty-two-characters",
        )
    )
    with TestClient(app) as client:
        public = client.get("/api/v1/health/live")
        private = client.get("/api/v1/users/me")
    for response in (public, private):
        assert response.headers["Cache-Control"] == "no-store"
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["Referrer-Policy"] == "no-referrer"
        assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
        assert response.headers["X-Request-Id"]
    assert public.status_code == 200
    assert private.status_code == 401
