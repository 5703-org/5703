"""The admin worker observation reads actual PostgreSQL lock state."""

from sqlalchemy import text

from app.platform_core.worker_locks import QUEUE_LOCKS


def test_admin_sees_observed_worker_lanes_and_student_cannot_read(runtime):
    endpoint = "/api/v1/admin/operations/overview"
    assert runtime.client.get(endpoint, headers=runtime.headers()).status_code == 403
    admin_headers = runtime.headers("admin@example.com")

    with runtime.engine.connect() as lock:
        assert lock.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": QUEUE_LOCKS["all"]})
        try:
            response = runtime.client.get(endpoint, headers=admin_headers)
            assert response.status_code == 200, response.text
            observed = response.json()["data"]["worker_locks"]
            assert observed == {
                "observation": "postgres_advisory_lock",
                "layout": "all",
                "interactive": {"lock_observed": True},
                "background": {"lock_observed": True},
            }
        finally:
            assert lock.scalar(text("SELECT pg_advisory_unlock(:key)"), {"key": QUEUE_LOCKS["all"]})

    response = runtime.client.get(endpoint, headers=admin_headers)
    assert response.status_code == 200, response.text
    assert response.json()["data"]["worker_locks"]["layout"] == "none"

    with runtime.engine.connect() as lock:
        assert lock.scalar(
            text("SELECT pg_try_advisory_lock_shared(:key)"), {"key": QUEUE_LOCKS["all"]}
        )
        assert lock.scalar(
            text("SELECT pg_try_advisory_lock(:key)"), {"key": QUEUE_LOCKS["interactive"]}
        )
        assert lock.scalar(
            text("SELECT pg_try_advisory_lock(:key)"), {"key": QUEUE_LOCKS["background"]}
        )
        try:
            response = runtime.client.get(endpoint, headers=admin_headers)
            assert response.status_code == 200, response.text
            assert response.json()["data"]["worker_locks"]["layout"] == "split"
            assert lock.scalar(
                text("SELECT pg_advisory_unlock(:key)"), {"key": QUEUE_LOCKS["background"]}
            )
            response = runtime.client.get(endpoint, headers=admin_headers)
            assert response.status_code == 200, response.text
            observed = response.json()["data"]["worker_locks"]
            assert observed["layout"] == "partial"
            assert observed["interactive"]["lock_observed"] is True
            assert observed["background"]["lock_observed"] is False
        finally:
            assert lock.scalar(
                text("SELECT pg_advisory_unlock(:key)"), {"key": QUEUE_LOCKS["interactive"]}
            )
            assert lock.scalar(
                text("SELECT pg_advisory_unlock_shared(:key)"), {"key": QUEUE_LOCKS["all"]}
            )
