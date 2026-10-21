import pytest

from app import app
from db import get_connection
from make_admin import make_admin
from quiz import ensure_database
from stats import (
    logins_per_day,
    most_missed_questions,
    overview,
    recent_students,
    subject_scores,
)

IDS = ["phys-kin-001", "phys-kin-002"]  # the correct answers are B and C


@pytest.fixture
def conn():
    ensure_database()
    connection = get_connection()
    yield connection
    connection.close()


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


def submit(client, answers):
    data = {"question_id": IDS, "subject": "Physics", "topic": "Kinematics"}
    for question_id, letter in answers.items():
        data["answer_" + question_id] = letter
    client.post("/submit", data=data)


def test_an_empty_database_gives_zeros_and_empty_lists(conn):
    data = overview(conn)
    assert data["students"] == 0
    assert data["active_students"] == 0
    assert data["quizzes"] == 0
    assert data["logins"] == 0
    assert data["questions"] > 0
    assert list(logins_per_day(conn)) == []
    assert list(subject_scores(conn)) == []
    assert list(most_missed_questions(conn)) == []
    assert list(recent_students(conn)) == []


def test_overview_counts_students_not_admins(conn):
    register("alice")
    register("bob")
    register("boss")
    make_admin("boss")
    data = overview(conn)
    assert data["students"] == 2
    assert data["logins"] == 2


def test_overview_counts_quizzes_and_active_students(conn):
    alice = register("alice")
    register("bob")
    submit(alice, {"phys-kin-001": "B", "phys-kin-002": "C"})
    submit(alice, {})
    data = overview(conn)
    assert data["quizzes"] == 2
    assert data["active_students"] == 1


def test_subject_scores_average(conn):
    alice = register("alice")
    submit(alice, {"phys-kin-001": "B", "phys-kin-002": "C"})  # 100 percent
    submit(alice, {})  # 0 percent
    rows = subject_scores(conn)
    assert [(r["subject"], r["attempts"], r["avg_percent"]) for r in rows] == [
        ("Physics", 2, 50.0)
    ]


def test_most_missed_questions_are_ranked(conn):
    alice = register("alice")
    bob = register("bob")
    submit(alice, {"phys-kin-001": "B", "phys-kin-002": "A"})
    submit(bob, {"phys-kin-001": "A", "phys-kin-002": "A"})
    rows = most_missed_questions(conn)
    assert rows[0]["id"] == "phys-kin-002"
    assert rows[0]["wrong_percent"] == 100.0
    assert rows[1]["id"] == "phys-kin-001"
    assert rows[1]["wrong_percent"] == 50.0


def test_logins_per_day(conn):
    register("alice")
    register("bob")
    rows = logins_per_day(conn)
    assert len(rows) == 1
    assert (rows[0]["logins"], rows[0]["students"]) == (2, 2)


def test_student_list_shows_quiz_counts_and_leaves_out_admins(conn):
    alice = register("alice")
    register("bob")
    register("boss")
    make_admin("boss")
    submit(alice, {})
    rows = recent_students(conn)
    assert [(r["username"], r["quizzes"]) for r in rows] == [("bob", 0), ("alice", 1)]