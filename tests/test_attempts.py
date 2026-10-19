from app import app
from db import get_connection
from quiz import ensure_database

IDS = ["phys-kin-001", "phys-kin-002"]  # the correct answers are B and C


def register(username="dawit"):
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


def submit(client, answers, ids=IDS, topic="Kinematics"):
    data = {"question_id": ids, "subject": "Physics", "topic": topic}
    for question_id, letter in answers.items():
        data["answer_" + question_id] = letter
    return client.post("/submit", data=data)


def query(sql, params=()):
    ensure_database()
    conn = get_connection()
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def test_submitting_saves_the_attempt_and_shows_it():
    client = register()
    response = submit(client, {"phys-kin-001": "B", "phys-kin-002": "C"})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/attempt/1")

    page = client.get("/attempt/1")
    assert page.status_code == 200
    assert b"2 / 2" in page.data

    attempt = query("SELECT subject, topic, score, total FROM attempts")[0]
    assert tuple(attempt) == ("Physics", "Kinematics", 2, 2)
    answers = query(
        "SELECT question_id, chosen, is_correct FROM attempt_answers ORDER BY rowid"
    )
    assert [tuple(r) for r in answers] == [
        ("phys-kin-001", "B", 1),
        ("phys-kin-002", "C", 1),
    ]


def test_wrong_and_missing_answers_are_stored():
    client = register()
    submit(client, {"phys-kin-001": "A"})
    attempt = query("SELECT score, total FROM attempts")[0]
    assert tuple(attempt) == (0, 2)
    answers = query(
        "SELECT question_id, chosen, is_correct FROM attempt_answers ORDER BY rowid"
    )
    assert [tuple(r) for r in answers] == [
        ("phys-kin-001", "A", 0),
        ("phys-kin-002", None, 0),
    ]


def test_topic_is_dropped_when_it_does_not_match_the_questions():
    client = register()
    submit(client, {}, ids=["phys-kin-001", "phys-dyn-001"], topic="Kinematics")
    assert query("SELECT topic FROM attempts")[0][0] is None


def test_viewing_an_attempt_again_does_not_create_another():
    client = register()
    submit(client, {"phys-kin-001": "B"})
    client.get("/attempt/1")
    client.get("/attempt/1")
    assert query("SELECT COUNT(*) FROM attempts")[0][0] == 1


def test_students_cannot_open_each_others_attempts():
    owner = register("dawit")
    submit(owner, {"phys-kin-001": "B"})
    other = register("someone")
    assert other.get("/attempt/1").status_code == 404
    assert owner.get("/attempt/1").status_code == 200


def test_attempt_page_needs_login():
    response = app.test_client().get("/attempt/1")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_history_lists_only_my_attempts():
    owner = register("dawit")
    submit(owner, {"phys-kin-001": "B", "phys-kin-002": "C"})
    submit(owner, {})
    page = owner.get("/history")
    assert page.status_code == 200
    assert page.data.count(b"Review") == 2
    assert b"2 / 2" in page.data

    other = register("someone")
    assert b"You have not taken a quiz yet" in other.get("/history").data


def test_history_needs_login():
    response = app.test_client().get("/history")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_unknown_attempt_gives_404():
    client = register()
    assert client.get("/attempt/999").status_code == 404


def test_header_shows_my_results_link_when_logged_in():
    client = register()
    assert b"My results" in client.get("/").data