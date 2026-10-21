import re

CHOICE_LETTERS = ["A", "B", "C", "D"]
DIFFICULTIES = ["easy", "medium", "hard"]
NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9 &'/-]{1,59}$")


def clean_text(value):
    """Trim the text and collapse repeated spaces."""
    return " ".join(str(value).split())


def validate_name(value, what):
    """Check a subject or topic name. Returns (clean_name, problem)."""
    name = clean_text(value)
    if not NAME_PATTERN.match(name):
        return None, f"{what} must be 2 to 60 characters and start with a letter."
    return name, None


def add_subject(conn, name):
    """Returns (subject_id, problem)."""
    if conn.execute(
        "SELECT 1 FROM subjects WHERE lower(name) = lower(?)", (name,)
    ).fetchone():
        return None, "That subject already exists."
    cursor = conn.execute("INSERT INTO subjects (name) VALUES (?)", (name,))
    conn.commit()
    return cursor.lastrowid, None


def add_topic(conn, subject_id, name):
    """Returns (topic_id, problem)."""
    try:
        subject_id = int(subject_id)
    except (TypeError, ValueError):
        return None, "Choose a subject."
    if conn.execute("SELECT 1 FROM subjects WHERE id = ?", (subject_id,)).fetchone() is None:
        return None, "That subject does not exist."
    if conn.execute(
        "SELECT 1 FROM topics WHERE subject_id = ? AND lower(name) = lower(?)",
        (subject_id, name),
    ).fetchone():
        return None, "That topic already exists in this subject."
    cursor = conn.execute(
        "INSERT INTO topics (subject_id, name) VALUES (?, ?)", (subject_id, name)
    )
    conn.commit()
    return cursor.lastrowid, None


def validate_question(values):
    """Check the question form. Returns (clean_data, list_of_problems)."""
    errors = []

    question = clean_text(values.get("question", ""))
    if not 5 <= len(question) <= 500:
        errors.append("The question must be 5 to 500 characters.")

    choices = {}
    for letter in CHOICE_LETTERS:
        text = clean_text(values.get("choice_" + letter, ""))
        if not 1 <= len(text) <= 200:
            errors.append(f"Choice {letter} must be 1 to 200 characters.")
        choices[letter] = text
    filled = [text.lower() for text in choices.values() if text]
    if len(set(filled)) != len(filled):
        errors.append("The four choices must all be different.")

    answer = str(values.get("answer", "")).strip().upper()
    if answer not in CHOICE_LETTERS:
        errors.append("Choose which answer (A to D) is correct.")

    difficulty = str(values.get("difficulty", "")).strip().lower()
    if difficulty not in DIFFICULTIES:
        errors.append("Choose a difficulty.")

    explanation = clean_text(values.get("explanation", ""))
    if not 5 <= len(explanation) <= 1000:
        errors.append("The explanation must be 5 to 1000 characters.")

    try:
        topic_id = int(values.get("topic_id", ""))
    except (TypeError, ValueError):
        topic_id = None
        errors.append("Choose a topic.")

    data = {
        "topic_id": topic_id,
        "difficulty": difficulty,
        "question": question,
        "choices": choices,
        "answer": answer,
        "explanation": explanation,
    }
    return data, errors


def add_question(conn, data):
    """Store a checked question. Returns (question_id, problem)."""
    if conn.execute("SELECT 1 FROM topics WHERE id = ?", (data["topic_id"],)).fetchone() is None:
        return None, "That topic does not exist."
    if conn.execute(
        "SELECT 1 FROM questions WHERE topic_id = ? AND lower(question_text) = lower(?)",
        (data["topic_id"], data["question"]),
    ).fetchone():
        return None, "That question already exists in this topic."

    row = conn.execute(
        "SELECT MAX(CAST(substr(id, 5) AS INTEGER)) FROM questions WHERE id LIKE 'adm-%'"
    ).fetchone()
    question_id = f"adm-{(row[0] or 0) + 1:04d}"

    conn.execute(
        "INSERT INTO questions "
        "(id, topic_id, difficulty, question_text, explanation, correct_choice) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            question_id,
            data["topic_id"],
            data["difficulty"],
            data["question"],
            data["explanation"],
            data["answer"],
        ),
    )
    for letter, text in data["choices"].items():
        conn.execute(
            "INSERT INTO choices (question_id, letter, choice_text) VALUES (?, ?, ?)",
            (question_id, letter, text),
        )
    conn.commit()
    return question_id, None


def subject_summary(conn):
    """Each subject with its number of topics and questions."""
    return conn.execute(
        """
        SELECT s.id AS id, s.name AS name,
               COUNT(DISTINCT t.id) AS topics, COUNT(q.id) AS questions
        FROM subjects s
        LEFT JOIN topics t ON t.subject_id = s.id
        LEFT JOIN questions q ON q.topic_id = t.id
        GROUP BY s.id
        ORDER BY s.name
        """
    ).fetchall()


def topic_summary(conn):
    """Each topic with its subject and number of questions."""
    return conn.execute(
        """
        SELECT t.id AS id, s.name AS subject, t.name AS topic, COUNT(q.id) AS questions
        FROM topics t
        JOIN subjects s ON s.id = t.subject_id
        LEFT JOIN questions q ON q.topic_id = t.id
        GROUP BY t.id
        ORDER BY s.name, t.name
        """
    ).fetchall()