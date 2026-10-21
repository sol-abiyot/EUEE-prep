from app import app
from make_admin import make_admin


def register(username):
    client = app.test_client()
    client.post(
        "/register",
        data={
            "username": username,
            "display_name": "",
            "email": f"{username}@example.com",
            "phone": "",
            "password": "secret123",
            "confirm": "secret123",
        },
    )
    return client


def test_visitors_are_sent_to_the_login_page():
    response = app.test_client().get("/admin")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_students_cannot_open_the_dashboard():
    student = register("alice")
    assert student.get("/admin").status_code == 403


def test_admin_can_open_the_dashboard():
    boss = register("boss")
    assert make_admin("boss") is True
    response = boss.get("/admin")
    assert response.status_code == 200
    assert b"Usage dashboard" in response.data


def test_make_admin_reports_unknown_users():
    assert make_admin("nobody") is False


def test_admin_link_is_only_shown_to_admins():
    student = register("alice")
    assert b'href="/admin"' not in student.get("/").data
    boss = register("boss")
    make_admin("boss")
    assert b'href="/admin"' in boss.get("/").data


def test_dashboard_lists_the_students():
    register("alice")
    boss = register("boss")
    make_admin("boss")
    assert b"alice" in boss.get("/admin").data