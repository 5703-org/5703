"""The closed loop: session CRUD + authz + optimistic locking."""


def _create(client, headers, title="Demo chat"):
    response = client.post("/api/v1/sessions", json={"title": title}, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_full_session_lifecycle(client, student_headers):
    created = _create(client, student_headers)
    assert created["status"] == "active"
    session_id = created["id"]

    # Read back: server state, not a frontend illusion.
    fetched = client.get(f"/api/v1/sessions/{session_id}", headers=student_headers)
    assert fetched.status_code == 200
    assert fetched.json()["data"]["title"] == "Demo chat"

    # Rename with the correct version.
    renamed = client.patch(
        f"/api/v1/sessions/{session_id}",
        json={"title": "Renamed chat", "version": created["version"]},
        headers=student_headers,
    )
    assert renamed.status_code == 200
    assert renamed.json()["data"]["version"] == created["version"] + 1

    # Stale version is rejected with 409, never silently overwritten.
    stale = client.patch(
        f"/api/v1/sessions/{session_id}",
        json={"title": "Stale write", "version": created["version"]},
        headers=student_headers,
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "CONFLICT"

    # Archive removes it from the active list.
    assert client.post(f"/api/v1/sessions/{session_id}/archive", headers=student_headers).status_code == 200
    active = client.get("/api/v1/sessions?status=active", headers=student_headers).json()["data"]
    assert all(s["id"] != session_id for s in active)
    archived = client.get("/api/v1/sessions?status=archived", headers=student_headers).json()["data"]
    assert any(s["id"] == session_id for s in archived)

    # Restore brings it back.
    assert client.post(f"/api/v1/sessions/{session_id}/restore", headers=student_headers).status_code == 200

    # Soft delete: gone from lists and direct reads afterwards.
    assert client.delete(f"/api/v1/sessions/{session_id}", headers=student_headers).status_code == 200
    assert client.get(f"/api/v1/sessions/{session_id}", headers=student_headers).status_code == 404


def test_cross_user_isolation(client, student_headers, student2_headers):
    created = _create(client, student_headers, title="Private chat")
    session_id = created["id"]
    # Another user gets 404, not 403: the API does not confirm existence.
    assert client.get(f"/api/v1/sessions/{session_id}", headers=student2_headers).status_code == 404
    assert client.delete(f"/api/v1/sessions/{session_id}", headers=student2_headers).status_code == 404
    other_list = client.get("/api/v1/sessions?status=all", headers=student2_headers).json()["data"]
    assert all(s["id"] != session_id for s in other_list)


def test_archive_twice_is_idempotent(client, student_headers):
    created = _create(client, student_headers)
    session_id = created["id"]
    first = client.post(f"/api/v1/sessions/{session_id}/archive", headers=student_headers)
    second = client.post(f"/api/v1/sessions/{session_id}/archive", headers=student_headers)
    assert first.status_code == second.status_code == 200


def test_session_created_event_lands_in_outbox(client, admin_headers, student_headers):
    created = _create(client, student_headers, title="Event check")
    events = client.get("/api/v1/admin/events", headers=admin_headers).json()["data"]
    match = [e for e in events if e["event_type"] == "learning.session.created"]
    assert match, "session creation must publish a domain event"
