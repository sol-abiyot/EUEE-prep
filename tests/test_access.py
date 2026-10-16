import pytest

from app import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setitem(app.config, "REQUIRE_LOGIN", True)
    return app.test_client()


def register(client, username="dawit", password="secret123"):
    return client.post(
        "/register",
        data={
            "username": username,
            "display_name": "",
            "email": f"{username}@example.com",
            "phone": "",
            "password": password,
            "confirm": password,
        },
    )


def test_home_and_subject_pages_stay_public(client):
    assert client.get("/").status_code == 200
    assert client.get("/subject/Physics").status_code == 200


def test_quiz_page_sends_visitors_to_the_login_page(client):
    response = client.get("/quiz/Physics?limit=5")
    assert response.status_code == 302
    location = response.headers["Location"]
    assert "/login" in location
    assert "next=" in location


def test_submitting_without_login_is_refused(client):
    response = client.post("/submit", data={"question_id": ["phys-kin-001"]})
    assert response.status_code == 302
    location = response.headers["Location"]
    assert "/login" in location
    assert "next=" not in location


def test_quiz_opens_after_registering(client):
    register(client)
    assert client.get("/quiz/Physics").status_code == 200


def test_login_returns_the_student_to_the_page_they_wanted(client):
    register(client)
    other = app.test_client()
    response = other.post(
        "/login",
        data={
            "username": "dawit",
            "password": "secret123",
            "next": "/quiz/Physics?limit=5",
        },
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/quiz/Physics?limit=5")


@pytest.mark.parametrize(
    "unsafe", ["https://evil.example/x", "//evil.example", "/\\evil.example"]
)
def test_login_never_redirects_to_another_website(client, unsafe):
    register(client)
    other = app.test_client()
    response = other.post(
        "/login",
        data={"username": "dawit", "password": "secret123", "next": unsafe},
    )
    assert response.status_code == 302
    assert "evil" not in response.headers["Location"]


def test_logging_out_locks_the_quiz_again(client):
    register(client)
    client.post("/logout")
    response = client.get("/quiz/Physics")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]