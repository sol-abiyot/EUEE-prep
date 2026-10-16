import pytest

from app import app
from auth import validate_registration
from db import get_connection
from quiz import ensure_database


@pytest.fixture
def client():
    return app.test_client()


def register(client, username="dawit", password="secret123", confirm=None,
             email=None, phone=""):
    return client.post(
        "/register",
        data={
            "username": username,
            "display_name": "",
            "email": f"{username.lower()}@example.com" if email is None else email,
            "phone": phone,
            "password": password,
            "confirm": password if confirm is None else confirm,
        },
    )


def login(client, username="dawit", password="secret123"):
    return client.post("/login", data={"username": username, "password": password})


def count_rows(table):
    ensure_database()
    conn = get_connection()
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        conn.close()


def test_good_registration_has_no_errors():
    assert validate_registration("dawit_k", "secret123", "secret123", "dawit@example.com") == []


@pytest.mark.parametrize(
    "username, password, confirm",
    [
        ("ab", "secret123", "secret123"),
        ("bad name!", "secret123", "secret123"),
        ("dawit", "short", "short"),
        ("dawit", "secret123", "different123"),
    ],
)
def test_bad_registration_input_is_rejected(username, password, confirm):
    errors = validate_registration(username, password, confirm, "dawit@example.com")
    assert len(errors) >= 1


@pytest.mark.parametrize("email", ["", "no-at-sign", "a@b"])
def test_bad_email_is_rejected(email):
    errors = validate_registration("dawit", "secret123", "secret123", email)
    assert any("email" in e.lower() for e in errors)


@pytest.mark.parametrize("phone", ["abc123", "12345"])
def test_bad_phone_is_rejected(phone):
    errors = validate_registration("dawit", "secret123", "secret123", "d@example.com", phone)
    assert any("phone" in e.lower() for e in errors)


def test_phone_is_optional():
    assert validate_registration("dawit", "secret123", "secret123", "d@example.com", "") == []


def test_login_and_register_pages_load(client):
    for url in ("/login", "/register"):
        assert client.get(url).status_code == 200


def test_registering_logs_the_student_in(client):
    response = register(client)
    assert response.status_code == 302
    home = client.get("/")
    assert b"Log out" in home.data
    assert b"dawit" in home.data


def test_email_is_stored_in_lowercase_and_phone_is_normalised(client):
    register(client, email="Dawit@Example.COM", phone="+251 91-123 4567")
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT email, phone FROM users WHERE username = 'dawit'"
        ).fetchone()
    finally:
        conn.close()
    assert row["email"] == "dawit@example.com"
    assert row["phone"] == "+251911234567"


def test_password_is_never_stored_in_plain_text(client):
    register(client)
    conn = get_connection()
    try:
        stored = conn.execute(
            "SELECT password_hash FROM users WHERE username = 'dawit'"
        ).fetchone()[0]
    finally:
        conn.close()
    assert stored != "secret123"
    assert "secret123" not in stored


def test_duplicate_username_is_rejected_ignoring_case(client):
    register(client)
    other = app.test_client()
    response = register(other, username="DAWIT")
    assert response.status_code == 200
    assert b"already taken" in response.data
    assert count_rows("users") == 1


def test_duplicate_email_is_rejected(client):
    register(client)
    other = app.test_client()
    response = register(other, username="someone", email="dawit@example.com")
    assert response.status_code == 200
    assert b"already registered" in response.data
    assert count_rows("users") == 1


def test_mismatched_passwords_show_an_error(client):
    response = register(client, confirm="different123")
    assert response.status_code == 200
    assert b"do not match" in response.data
    assert count_rows("users") == 0


def test_wrong_password_is_rejected(client):
    register(client)
    other = app.test_client()
    response = login(other, password="wrongpass1")
    assert response.status_code == 200
    assert b"Wrong username or password" in response.data
    assert b"Log out" not in response.data


def test_successful_login_is_recorded(client):
    register(client)  # registering also logs the student in (1 login event)
    other = app.test_client()
    response = login(other)
    assert response.status_code == 302
    assert count_rows("login_events") == 2
    assert b"Log out" in other.get("/").data


def test_logout_needs_post_and_ends_the_session(client):
    register(client)
    assert client.get("/logout").status_code == 405
    assert b"Log out" in client.get("/").data
    assert client.post("/logout").status_code == 302
    assert b"Log in" in client.get("/").data