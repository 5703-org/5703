"""Trace propagation (Spec A10)."""


def test_trace_header_matches_envelope(client, student_headers):
    response = client.get("/api/v1/users/me", headers=student_headers)
    assert response.headers["X-Request-Id"]
    assert response.json()["meta"]["trace_id"] == response.headers["X-Request-Id"]


def test_inbound_request_id_is_honoured(client):
    response = client.get("/live", headers={"X-Request-Id": "trace-from-frontend-123"})
    assert response.headers["X-Request-Id"] == "trace-from-frontend-123"


def test_capabilities_reflects_registry(client, student_headers):
    response = client.get("/api/v1/capabilities", headers=student_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    provider_types = {p["capability_type"] for p in data["providers"]}
    assert {"parser", "retriever", "generator"} <= provider_types
    assert data["feature_flags"]["multi_workspace"] is False
