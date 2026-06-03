def test_login_success(client, manager_user):
    r = client.post("/api/auth/login", json={"email": "manager@test.com", "password": "password123"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_login_invalid_password(client, manager_user):
    r = client.post("/api/auth/login", json={"email": "manager@test.com", "password": "wrong"})
    assert r.status_code == 401


def test_login_unknown_email(client):
    r = client.post("/api/auth/login", json={"email": "nobody@test.com", "password": "password123"})
    assert r.status_code == 401


def test_get_me_authenticated(client, auth_headers_manager):
    r = client.get("/api/auth/me", headers=auth_headers_manager)
    assert r.status_code == 200
    assert r.json()["email"] == "manager@test.com"


def test_get_me_unauthenticated(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401
