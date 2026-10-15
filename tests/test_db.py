import sqlite3

import pytest

from db import get_connection, init_db, seed_from_json
from quiz import load_questions_from_json as load_questions


@pytest.fixture
def conn(tmp_path):
    connection = get_connection(tmp_path / "test.db")
    init_db(connection)
    seed_from_json(connection)
    yield connection
    connection.close()


def count(conn, table):
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_all_questions_are_seeded(conn):
    assert count(conn, "questions") == len(load_questions())


def test_seeding_twice_does_not_duplicate_anything(conn):
    seed_from_json(conn)
    questions = load_questions()
    assert count(conn, "questions") == len(questions)
    assert count(conn, "subjects") == len({q["subject"] for q in questions})
    assert count(conn, "choices") == len(questions) * 4


def test_every_question_has_exactly_four_choices(conn):
    rows = conn.execute(
        "SELECT question_id, COUNT(*) AS n FROM choices GROUP BY question_id"
    ).fetchall()
    assert len(rows) == len(load_questions())
    assert all(row["n"] == 4 for row in rows)


def test_answer_keys_match_the_json_files(conn):
    for q in load_questions():
        row = conn.execute(
            "SELECT correct_choice FROM questions WHERE id = ?", (q["id"],)
        ).fetchone()
        assert row["correct_choice"] == q["answer"]


def test_topics_are_linked_to_their_subjects(conn):
    row = conn.execute(
        "SELECT s.name FROM topics t JOIN subjects s ON s.id = t.subject_id "
        "WHERE t.name = 'Kinematics'"
    ).fetchone()
    assert row["name"] == "Physics"


def test_database_rejects_an_invalid_answer_letter(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "UPDATE questions SET correct_choice = 'E' WHERE id = 'math-alg-001'"
        )