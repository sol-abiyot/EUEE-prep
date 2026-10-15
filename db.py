import json
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = BASE_DIR / "instance" / "euee.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL REFERENCES subjects(id),
    name TEXT NOT NULL,
    UNIQUE (subject_id, name)
);

CREATE TABLE IF NOT EXISTS questions (
    id TEXT PRIMARY KEY,
    topic_id INTEGER NOT NULL REFERENCES topics(id),
    difficulty TEXT NOT NULL CHECK (difficulty IN ('easy', 'medium', 'hard')),
    question_text TEXT NOT NULL,
    explanation TEXT NOT NULL,
    correct_choice TEXT NOT NULL CHECK (correct_choice IN ('A', 'B', 'C', 'D'))
);

CREATE TABLE IF NOT EXISTS choices (
    question_id TEXT NOT NULL REFERENCES questions(id),
    letter TEXT NOT NULL CHECK (letter IN ('A', 'B', 'C', 'D')),
    choice_text TEXT NOT NULL,
    PRIMARY KEY (question_id, letter)
);
"""


def get_connection(db_path=DB_PATH):
    """Open the database (creating its folder if needed)."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn):
    """Create the tables if they do not exist yet."""
    conn.executescript(SCHEMA)
    conn.commit()


def seed_from_json(conn, data_dir=DATA_DIR):
    """Load every JSON question file into the database.

    Safe to run again: existing rows are updated, not duplicated.
    Returns the number of questions processed.
    """
    count = 0
    for path in sorted(Path(data_dir).glob("*.json")):
        with open(path, encoding="utf-8") as f:
            questions = json.load(f)

        for q in questions:
            conn.execute(
                "INSERT OR IGNORE INTO subjects (name) VALUES (?)",
                (q["subject"],),
            )
            subject_id = conn.execute(
                "SELECT id FROM subjects WHERE name = ?", (q["subject"],)
            ).fetchone()["id"]

            conn.execute(
                "INSERT OR IGNORE INTO topics (subject_id, name) VALUES (?, ?)",
                (subject_id, q["topic"]),
            )
            topic_id = conn.execute(
                "SELECT id FROM topics WHERE subject_id = ? AND name = ?",
                (subject_id, q["topic"]),
            ).fetchone()["id"]

            conn.execute(
                """
                INSERT INTO questions
                    (id, topic_id, difficulty, question_text, explanation, correct_choice)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    topic_id = excluded.topic_id,
                    difficulty = excluded.difficulty,
                    question_text = excluded.question_text,
                    explanation = excluded.explanation,
                    correct_choice = excluded.correct_choice
                """,
                (
                    q["id"],
                    topic_id,
                    q["difficulty"],
                    q["question"],
                    q["explanation"],
                    q["answer"],
                ),
            )

            for letter, text in q["choices"].items():
                conn.execute(
                    "INSERT OR REPLACE INTO choices (question_id, letter, choice_text) "
                    "VALUES (?, ?, ?)",
                    (q["id"], letter, text),
                )
            count += 1

    conn.commit()
    return count

def fetch_all_questions(conn):
    """Return every question as a dictionary, in the same shape as the JSON files."""
    rows = conn.execute(
        """
        SELECT q.id, s.name AS subject, t.name AS topic, q.difficulty,
               q.question_text, q.explanation, q.correct_choice
        FROM questions q
        JOIN topics t ON t.id = q.topic_id
        JOIN subjects s ON s.id = t.subject_id
        ORDER BY s.name, q.id
        """
    ).fetchall()

    choices = {}
    for row in conn.execute(
        "SELECT question_id, letter, choice_text FROM choices "
        "ORDER BY question_id, letter"
    ):
        choices.setdefault(row["question_id"], {})[row["letter"]] = row["choice_text"]

    return [
        {
            "id": row["id"],
            "subject": row["subject"],
            "topic": row["topic"],
            "difficulty": row["difficulty"],
            "question": row["question_text"],
            "choices": choices.get(row["id"], {}),
            "answer": row["correct_choice"],
            "explanation": row["explanation"],
        }
        for row in rows
    ]
if __name__ == "__main__":
    connection = get_connection()
    init_db(connection)
    total = seed_from_json(connection)
    connection.close()
    print(total, "questions loaded into", DB_PATH)