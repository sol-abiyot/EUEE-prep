def save_attempt(conn, user_id, questions, result, topic=None):
    """Store one submitted quiz and the student's answer to each question."""
    subjects = {q["subject"] for q in questions}
    subject = subjects.pop() if len(subjects) == 1 else "Mixed"
    if not (topic and all(q["topic"] == topic for q in questions)):
        topic = None

    cursor = conn.execute(
        "INSERT INTO attempts (user_id, subject, topic, score, total) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, subject, topic, result["score"], result["total"]),
    )
    attempt_id = cursor.lastrowid

    for r in result["results"]:
        conn.execute(
            "INSERT INTO attempt_answers (attempt_id, question_id, chosen, is_correct) "
            "VALUES (?, ?, ?, ?)",
            (attempt_id, r["id"], r["chosen"], 1 if r["status"] == "correct" else 0),
        )
    conn.commit()
    return attempt_id


def list_attempts(conn, user_id, limit=100):
    """Return this student's attempts, newest first."""
    return conn.execute(
        "SELECT id, subject, topic, score, total, taken_at FROM attempts "
        "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()


def get_attempt(conn, attempt_id, user_id):
    """Return (attempt, answers) if the attempt belongs to this student, else (None, [])."""
    attempt = conn.execute(
        "SELECT * FROM attempts WHERE id = ? AND user_id = ?", (attempt_id, user_id)
    ).fetchone()
    if attempt is None:
        return None, []
    rows = conn.execute(
        "SELECT question_id, chosen FROM attempt_answers "
        "WHERE attempt_id = ? ORDER BY rowid",
        (attempt_id,),
    ).fetchall()
    return attempt, rows