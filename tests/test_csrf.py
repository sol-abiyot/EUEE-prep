import re

import pytest

from app import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setitem(app.config, "CSRF_ENABLED", True)
    return app.test_client()


def token_from(client, url="/login"):
    page = client.get(url).data.decode()
    return re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)


def registration(token):
    return {
        "username": "dawit",
        "display_name": "",
        "email": "dawit@example.com",
        "phone": "",
        "password": "secret123",
        "confirm": "secret123",
        "csrf_token": token,
    }


def test_post_without_a_token_is_rejected(client):
    response = client.post("/login", data={"username": "a", "password": "b"})
    assert response.status_code == 400


def test_post_with_a_wrong_token_is_rejected(client):
    token_from(client)
    response = client.post(
        "/login", data={"username": "a", "password": "b", "csrf_token": "wrong"}
    )
    assert response.status_code == 400


def test_post_with_the_right_token_is_accepted(client):
    token = token_from(client)
    response = client.post(
        "/login", data={"username": "a", "password": "b", "csrf_token": token}
    )
    assert response.status_code == 200
    assert b"Wrong username or password" in response.data


def test_registration_works_with_a_token(client):
    token = token_from(client, "/register")
    response = client.post("/register", data=registration(token))
    assert response.status_code == 302


def test_logout_needs_a_token(client):
    client.post("/register", data=registration(token_from(client, "/register")))
    assert client.post("/logout").status_code == 400
    token = token_from(client, "/")
    assert client.post("/logout", data={"csrf_token": token}).status_code == 302


def test_get_requests_are_not_affected(client):
    assert client.get("/").status_code == 200


def test_forms_contain_the_token(client):
    for url in ("/login", "/register"):
        assert b'name="csrf_token"' in client.get(url).data