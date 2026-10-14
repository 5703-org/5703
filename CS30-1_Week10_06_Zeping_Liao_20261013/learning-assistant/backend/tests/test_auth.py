"""Auth, RBAC and isolation basics (Spec C04-C08)."""


def test_login_success(client):
    response = client.post("/api/v1/auth/login", json={"email": "student@example.com", "password": "Passw0rd!"})
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["token_type"] == "bearer"
    assert body["meta"]["trace_id"]


def test_login_wrong_password_is_stable_error(client):
    response = client.post("/api/v1/auth/login", json={"email": "student@example.com", "password": "wrong-password"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "BAD_CREDENTIALS"


def test_login_unknown_email_same_error(client):
    """No account enumeration: unknown email and bad password look identical."""
    response = client.post("/api/v1/auth/login", json={"email": "ghost@example.com", "password": "wrong-password"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "BAD_CREDENTIALS"


def test_me_requires_token(client):
    assert client.get("/api/v1/users/me").status_code == 401


def test_me_with_token(client, student_headers):
    response = client.get("/api/v1/users/me", headers=student_headers)
    assert response.status_code == 200
    assert response.json()["data"]["email"] == "student@example.com"
    assert response.json()["data"]["role"] == "student"


def test_garbage_token_rejected(client):
    response = client.get("/api/v1/users/me", headers={"Authorization": "Bearer not-a-token"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "TOKEN_INVALID"


def test_admin_route_forbidden_for_student(client, student_headers):
    response = client.get("/api/v1/admin/users", headers=student_headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_admin_route_ok_for_admin(client, admin_headers):
    response = client.get("/api/v1/admin/users", headers=admin_headers)
    assert response.status_code == 200
    emails = {u["email"] for u in response.json()["data"]}
    assert {"admin@example.com", "student@example.com"} <= emails
