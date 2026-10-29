"""Bulk-import questions from a CSV file.

    python import_questions.py my_questions.csv           check only, saves nothing
    python import_questions.py my_questions.csv --apply   check, back up, then save

Every row is checked with the same rules as the admin form. Nothing is saved
unless every row is valid. Missing subjects and topics are created.
"""
import csv
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from content import (
    add_question,
    add_subject,
    add_topic,
    clean_text,
    validate_name,
    validate_question,
)
from db import get_connection, init_db

COLUMNS = [
    "subject", "topic", "difficulty", "question",
    "choice_a", "choice_b", "choice_c", "choice_d",
    "correct", "explanation",
]


def read_rows(path):
    """Read the CSV. Returns (rows, problems); each row is (line_number, dict)."""
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return [], ["The file is empty."]
        reader.fieldnames = [clean_text(name).lower() for name in reader.fieldnames]
        missing = [name for name in COLUMNS if name not in reader.fieldnames]
        if missing:
            return [], ["Missing column(s): " + ", ".join(missing)]
        rows = []
        for number, row in enumerate(reader, start=2):
            row = {key: (value or "") for key, value in row.items() if key}
            if any(clean_text(value) for value in row.values()):
                rows.append((number, row))
    return rows, []


def find_id(conn, sql, params):
    found = conn.execute(sql, params).fetchone()
    return found[0] if found else None


def check_rows(conn, rows):
    """Check every row without saving. Returns (plan, problems)."""
    plan, problems, seen = [], [], set()
    for number, row in rows:
        subject, bad_subject = validate_name(row["subject"], "Subject")
        topic, bad_topic = validate_name(row["topic"], "Topic")
        values = {
            "question": row["question"],
            "choice_A": row["choice_a"],
            "choice_B": row["choice_b"],
            "choice_C": row["choice_c"],
            "choice_D": row["choice_d"],
            "answer": row["correct"],
            "difficulty": row["difficulty"],
            "explanation": row["explanation"],
            "topic_id": 0,  # the real topic is found when saving
        }
        data, errors = validate_question(values)
        errors = [e for e in errors if e != "Choose a topic."]
        if bad_subject:
            errors.append(bad_subject)
        if bad_topic:
            errors.append(bad_topic)
        if not errors:
            key = (subject.lower(), topic.lower(), data["question"].lower())
            if key in seen:
                errors.append("The same question appears earlier in this file.")
            seen.add(key)
            subject_id = find_id(
                conn, "SELECT id FROM subjects WHERE lower(name) = lower(?)", (subject,)
            )
            if subject_id is not None:
                topic_id = find_id(
                    conn,
                    "SELECT id FROM topics WHERE subject_id = ? AND lower(name) = lower(?)",
                    (subject_id, topic),
                )
                if topic_id is not None and find_id(
                    conn,
                    "SELECT 1 FROM questions WHERE topic_id = ? AND lower(question_text) = lower(?)",
                    (topic_id, data["question"]),
                ):
                    errors.append("That question already exists in this topic.")
        for error in errors:
            problems.append(f"Row {number}: {error}")
        if not errors:
            plan.append((number, subject, topic, data))
    return plan, problems


def backup_database(conn, folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"before-import-{datetime.now():%Y%m%d-%H%M%S}.db"
    copy = sqlite3.connect(target)
    conn.backup(copy)
    copy.close()
    return target


def save_plan(conn, plan):
    """Save checked rows. Returns (questions_saved, problems)."""
    saved, problems = 0, []
    for number, subject, topic, data in plan:
        subject_id = find_id(
            conn, "SELECT id FROM subjects WHERE lower(name) = lower(?)", (subject,)
        )
        if subject_id is None:
            subject_id, problem = add_subject(conn, subject)
            if problem:
                problems.append(f"Row {number}: {problem}")
                continue
        topic_id = find_id(
            conn,
            "SELECT id FROM topics WHERE subject_id = ? AND lower(name) = lower(?)",
            (subject_id, topic),
        )
        if topic_id is None:
            topic_id, problem = add_topic(conn, subject_id, topic)
            if problem:
                problems.append(f"Row {number}: {problem}")
                continue
        data["topic_id"] = topic_id
        _, problem = add_question(conn, data)
        if problem:
            problems.append(f"Row {number}: {problem}")
        else:
            saved += 1
    return saved, problems


def run(csv_path, apply=False, backup_folder=None):
    """Returns (exit_code, report_lines)."""
    report = []
    rows, problems = read_rows(csv_path)
    if problems:
        return 1, problems
    conn = get_connection()
    init_db(conn)
    try:
        plan, problems = check_rows(conn, rows)
        if problems:
            report.extend(problems)
            report.append(f"{len(problems)} problem(s) found. Nothing was saved.")
            return 1, report
        if not plan:
            return 1, ["The file has no questions."]
        counts = {}
        for _, subject, topic, _ in plan:
            counts[(subject, topic)] = counts.get((subject, topic), 0) + 1
        for (subject, topic), amount in sorted(counts.items()):
            report.append(f"  {subject} / {topic}: {amount}")
        if not apply:
            report.append(f"All {len(plan)} question(s) are valid. Nothing saved yet.")
            report.append("Run again with --apply to save them.")
            return 0, report
        folder = backup_folder or Path(__file__).resolve().parent / "backups"
        report.append("Backup saved: " + str(backup_database(conn, folder)))
        saved, problems = save_plan(conn, plan)
        report.extend(problems)
        report.append(f"Saved {saved} of {len(plan)} question(s).")
        return (0 if not problems else 1), report
    finally:
        conn.close()


if __name__ == "__main__":
    arguments = [a for a in sys.argv[1:] if a != "--apply"]
    if len(arguments) != 1:
        print("Usage: python import_questions.py FILE.csv [--apply]")
        sys.exit(2)
    code, lines = run(arguments[0], apply="--apply" in sys.argv)
    print("\n".join(lines))
    sys.exit(code)
