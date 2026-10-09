"""Error envelope contract (Spec A13)."""


def test_unknown_route_uses_envelope(client):
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["meta"]["trace_id"]


def test_validation_error_is_422_with_details(client, student_headers):
    response = client.patch(
        "/api/v1/sessions/whatever",
        json={"title": "", "version": 0},
        headers=student_headers,
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_FAILED"
    assert body["error"]["details"]


def test_profile_enum_validation(client, student_headers):
    response = client.put("/api/v1/profiles/me", json={"level": "wizard"}, headers=student_headers)
    assert response.status_code == 422


def test_profile_update_and_reset(client, student_headers):
    updated = client.put(
        "/api/v1/profiles/me",
        json={"level": "advanced", "topics": ["databases", "rag"]},
        headers=student_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["level"] == "advanced"
    reset = client.post("/api/v1/profiles/me/reset", headers=student_headers)
    assert reset.status_code == 200
    assert reset.json()["data"]["level"] == "beginner"
    assert reset.json()["data"]["version"] > updated.json()["data"]["version"]
