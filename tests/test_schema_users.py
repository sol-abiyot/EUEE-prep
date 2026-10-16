import sqlite3

import pytest

from db import get_connection, init_db


@pytest.fixture
def conn(tmp_path):
    connection = get_connection(tmp_path / "test.db")
    init_db(connection)
    yield connection
    connection.close()


def add_user(conn, username="student1", role="student"):
    conn.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
        (username, "not-a-real-hash", role),
    )
    return conn.execute(
        "SELECT id FROM users WHERE username = ?", (username,)
    ).fetchone()["id"]


def test_new_tables_exist(conn):
    names = {
        row["name"]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    assert {"users", "login_events", "attempts", "attempt_answers"} <= names


def test_usernames_must_be_unique(conn):
    add_user(conn, "dawit")
    with pytest.raises(sqlite3.IntegrityError):
        add_user(conn, "dawit")


def test_invalid_role_is_rejected(conn):
    with pytest.raises(sqlite3.IntegrityError):
        add_user(conn, "hacker", role="superuser")


def test_attempt_needs_an_existing_user(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO attempts (user_id, subject, score, total) VALUES (999, 'Physics', 1, 2)"
        )


def test_is_correct_must_be_zero_or_one(conn):
    user_id = add_user(conn)
    conn.execute(
        "INSERT INTO attempts (user_id, subject, score, total) VALUES (?, 'Physics', 0, 1)",
        (user_id,),
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO attempt_answers (attempt_id, question_id, chosen, is_correct) "
            "VALUES (1, 'x', 'A', 5)"
        )


def test_a_full_record_can_be_stored_and_joined(conn):
    conn.execute("INSERT INTO subjects (name) VALUES ('Physics')")
    conn.execute("INSERT INTO topics (subject_id, name) VALUES (1, 'Kinematics')")
    conn.execute(
        "INSERT INTO questions (id, topic_id, difficulty, question_text, explanation, correct_choice) "
        "VALUES ('q1', 1, 'easy', 'Q?', 'Because.', 'B')"
    )
    user_id = add_user(conn)
    conn.execute(
        "INSERT INTO attempts (user_id, subject, score, total) VALUES (?, 'Physics', 1, 1)",
        (user_id,),
    )
    conn.execute(
        "INSERT INTO attempt_answers (attempt_id, question_id, chosen, is_correct) "
        "VALUES (1, 'q1', 'B', 1)"
    )
    row = conn.execute(
        "SELECT u.username, a.score, aa.is_correct FROM attempt_answers aa "
        "JOIN attempts a ON a.id = aa.attempt_id "
        "JOIN users u ON u.id = a.user_id"
    ).fetchone()
    assert (row["username"], row["score"], row["is_correct"]) == ("student1", 1, 1)