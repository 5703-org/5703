"""Health endpoints (Spec A16, A17)."""


def test_live(client):
    response = client.get("/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_ready(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["checks"]["database"] == "up"


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["env"] == "test"
