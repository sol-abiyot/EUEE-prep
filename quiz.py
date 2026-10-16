import json
import random
from pathlib import Path

from db import fetch_all_questions, get_connection, init_db, seed_from_json

DATA_DIR = Path(__file__).resolve().parent / "data"

_database_ready = False


def load_questions_from_json():
    """Read every .json file in the data folder (the source the database is built from)."""
    questions = []
    for path in sorted(DATA_DIR.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            questions.extend(json.load(f))
    return questions


def ensure_database():
    """Create the tables, and load the JSON questions only if the database has none."""
    global _database_ready
    if not _database_ready:
        conn = get_connection()
        try:
            init_db(conn)
            if conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0] == 0:
                seed_from_json(conn)
        finally:
            conn.close()
        _database_ready = True

def load_questions():
    """Return all questions, read from the SQLite database."""
    ensure_database()
    conn = get_connection()
    try:
        return fetch_all_questions(conn)
    finally:
        conn.close()


def list_subjects():
    return sorted({q["subject"] for q in load_questions()})


def list_topics(subject):
    return sorted({
        q["topic"]
        for q in load_questions()
        if q["subject"].lower() == subject.lower()
    })


def get_questions(subject=None, topic=None):
    """Return questions, optionally filtered by subject and/or topic."""
    result = load_questions()
    if subject:
        result = [q for q in result if q["subject"].lower() == subject.lower()]
    if topic:
        result = [q for q in result if q["topic"].lower() == topic.lower()]
    return result


def get_question_by_id(question_id):
    for q in load_questions():
        if q["id"] == question_id:
            return q
    return None


def generate_quiz(subject=None, topic=None, limit=None, seed=None):
    """Pick questions for a quiz, in random order.

    subject, topic: optional filters.
    limit: maximum number of questions (None means all that match).
    seed: optional number that makes the shuffle repeatable (used in tests).
    """
    pool = get_questions(subject, topic)
    random.Random(seed).shuffle(pool)
    if limit is not None and limit > 0:
        pool = pool[:limit]
    return pool