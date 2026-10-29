import csv
import sqlite3

import import_questions
from db import get_connection, init_db

HEADER = [
    "subject", "topic", "difficulty", "question",
    "choice_a", "choice_b", "choice_c", "choice_d", "correct", "explanation",
]


def good_row(question="What is 2 + 2?", **changes):
    row = {
        "subject": "Chemistry", "topic": "Atoms", "difficulty": "easy",
        "question": question, "choice_a": "3", "choice_b": "4", "choice_c": "5",
        "choice_d": "6", "correct": "B", "explanation": "Two plus two is four.",
    }
    row.update(changes)
    return row


def write_csv(tmp_path, rows, header=HEADER):
    path = tmp_path / "q.csv"
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)
    return path


def count_questions():
    conn = get_connection()
    init_db(conn)
    try:
        return conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    finally:
        conn.close()


def test_check_only_saves_nothing(tmp_path):
    path = write_csv(tmp_path, [good_row()])
    code, report = import_questions.run(path)
    assert code == 0
    assert count_questions() == 0
    assert "Nothing saved yet" in " ".join(report)


def test_apply_saves_questions_creates_topic_and_backs_up(tmp_path):
    path = write_csv(tmp_path, [good_row(), good_row("What is 3 + 3?", correct="D")])
    code, report = import_questions.run(path, apply=True, backup_folder=tmp_path / "bk")
    assert code == 0
    assert count_questions() == 2
    assert len(list((tmp_path / "bk").glob("before-import-*.db"))) == 1
    conn = get_connection()
    row = conn.execute(
        "SELECT s.name, t.name FROM topics t JOIN subjects s ON s.id = t.subject_id"
    ).fetchone()
    conn.close()
    assert (row[0], row[1]) == ("Chemistry", "Atoms")


def test_one_bad_row_saves_nothing(tmp_path):
    path = write_csv(tmp_path, [good_row(), good_row("Second question?", correct="E")])
    code, report = import_questions.run(path, apply=True, backup_folder=tmp_path / "bk")
    assert code == 1
    assert count_questions() == 0
    assert any(line.startswith("Row 3:") for line in report)


def test_duplicate_inside_file_is_rejected(tmp_path):
    path = write_csv(tmp_path, [good_row(), good_row()])
    code, report = import_questions.run(path)
    assert code == 1
    assert any("earlier in this file" in line for line in report)


def test_duplicate_of_saved_question_is_rejected(tmp_path):
    path = write_csv(tmp_path, [good_row()])
    import_questions.run(path, apply=True, backup_folder=tmp_path / "bk")
    code, report = import_questions.run(path)
    assert code == 1
    assert any("already exists" in line for line in report)
    assert count_questions() == 1


def test_missing_column_is_reported(tmp_path):
    path = write_csv(tmp_path, [{"subject": "Chemistry"}], header=["subject"])
    code, report = import_questions.run(path)
    assert code == 1
    assert "Missing column" in report[0]


def test_capital_headers_and_blank_rows_are_accepted(tmp_path):
    path = tmp_path / "q.csv"
    path.write_text(
        "﻿Subject,Topic,Difficulty,Question,Choice_A,Choice_B,Choice_C,Choice_D,Correct,Explanation\n"
        "Chemistry,Atoms,easy,What is 2 + 2?,3,4,5,6,b,Two plus two is four.\n"
        ",,,,,,,,,\n",
        encoding="utf-8",
    )
    code, report = import_questions.run(path, apply=True, backup_folder=tmp_path / "bk")
    assert code == 0
    assert count_questions() == 1
