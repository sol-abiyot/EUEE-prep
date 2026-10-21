import pytest

from app import app
from content import (
    add_question,
    add_subject,
    add_topic,
    validate_name,
    validate_question,
)
from db import get_connection
from make_admin import make_admin
from quiz import ensure_database, get_question_by_id


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


def admin_client():
    client = register("boss")
    make_admin("boss")
    return client


def valid_question(**overrides):
    values = {
        "topic_id": "1",
        "difficulty": "easy",
        "question": "What is 2 + 2?",
        "choice_A": "3",
        "choice_B": "4",
        "choice_C": "5",
        "choice_D": "6",
        "answer": "B",
        "explanation": "Adding two and two gives four.",
    }
    values.update(overrides)
    return values


def count_questions():
    ensure_database()
    connection = get_connection()
    try:
        return connection.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    finally:
        connection.close()


def test_a_normal_name_is_cleaned_and_accepted():
    assert validate_name("  Work   and Energy ", "Topic") == ("Work and Energy", None)


@pytest.mark.parametrize("bad", ["", "1abc", "a", "x" * 61, "<script>"])
def test_bad_names_are_rejected(bad):
    name, problem = validate_name(bad, "Topic")
    assert name is None
    assert problem


def test_a_good_question_has_no_problems():
    data, errors = validate_question(valid_question())
    assert errors == []
    assert data["answer"] == "B"
    assert data["choices"] == {"A": "3", "B": "4", "C": "5", "D": "6"}


@pytest.mark.parametrize(
    "override",
    [
        {"question": ""},
        {"choice_C": ""},
        {"choice_C": "4"},
        {"answer": "E"},
        {"difficulty": "extreme"},
        {"explanation": "no"},
        {"topic_id": "abc"},
    ],
    ids=[
        "empty-question",
        "empty-choice",
        "duplicate-choices",
        "bad-answer-letter",
        "bad-difficulty",
        "short-explanation",
        "bad-topic",
    ],
)
def test_bad_questions_are_rejected(override):
    _, errors = validate_question(valid_question(**override))
    assert len(errors) >= 1


def test_duplicate_subjects_are_rejected_ignoring_case(conn):
    subject_id, problem = add_subject(conn, "Chemistry")
    assert subject_id is not None and problem is None
    assert add_subject(conn, "chemistry") == (None, "That subject already exists.")


def test_topic_names_can_repeat_across_subjects_but_not_within_one(conn):
    chemistry, _ = add_subject(conn, "Chemistry")
    biology, _ = add_subject(conn, "Biology")
    assert add_topic(conn, chemistry, "Basics")[1] is None
    assert add_topic(conn, chemistry, "basics")[1] is not None
    assert add_topic(conn, biology, "Basics")[1] is None


def test_a_topic_needs_an_existing_subject(conn):
    assert add_topic(conn, 9999, "Basics")[1] is not None
    assert add_topic(conn, "abc", "Basics")[1] is not None


def test_add_question_stores_everything(conn):
    data, errors = validate_question(valid_question())
    assert errors == []
    question_id, problem = add_question(conn, data)
    assert (question_id, problem) == ("adm-0001", None)
    stored = get_question_by_id(question_id)
    assert stored["question"] == "What is 2 + 2?"
    assert stored["answer"] == "B"
    assert stored["choices"] == {"A": "3", "B": "4", "C": "5", "D": "6"}


def test_question_ids_count_up(conn):
    first, _ = validate_question(valid_question())
    second, _ = validate_question(valid_question(question="What is 3 + 3?"))
    assert add_question(conn, first)[0] == "adm-0001"
    assert add_question(conn, second)[0] == "adm-0002"


def test_the_same_question_cannot_be_added_twice_to_a_topic(conn):
    data, _ = validate_question(valid_question())
    assert add_question(conn, data)[1] is None
    assert add_question(conn, data)[1] == "That question already exists in this topic."


def test_an_unknown_topic_is_rejected(conn):
    data, errors = validate_question(valid_question(topic_id="9999"))
    assert errors == []
    assert add_question(conn, data) == (None, "That topic does not exist.")


def test_content_pages_need_an_admin():
    assert app.test_client().get("/admin/content").status_code == 302
    assert register("alice").get("/admin/content").status_code == 403
    assert admin_client().get("/admin/content").status_code == 200


def test_students_cannot_post_to_the_admin_forms():
    student = register("alice")
    before = count_questions()
    assert student.post("/admin/subjects", data={"name": "Chemistry"}).status_code == 403
    assert student.post("/admin/topics", data={"subject_id": "1", "name": "Atoms"}).status_code == 403
    assert student.post("/admin/questions", data=valid_question()).status_code == 403
    assert count_questions() == before


def test_admin_adds_a_subject_a_topic_and_a_question():
    boss = admin_client()
    assert boss.post("/admin/subjects", data={"name": "Chemistry"}).status_code == 302
    assert b"Chemistry" in boss.get("/admin/content").data

    connection = get_connection()
    try:
        subject_id = connection.execute(
            "SELECT id FROM subjects WHERE name = 'Chemistry'"
        ).fetchone()[0]
    finally:
        connection.close()
    boss.post("/admin/topics", data={"subject_id": subject_id, "name": "Atoms"})

    connection = get_connection()
    try:
        topic_id = connection.execute(
            "SELECT id FROM topics WHERE name = 'Atoms'"
        ).fetchone()[0]
    finally:
        connection.close()

    # A subject with no questions yet is not shown to students.
    assert b"Chemistry" not in app.test_client().get("/").data

    response = boss.post("/admin/questions", data=valid_question(topic_id=str(topic_id)))
    assert response.status_code == 302
    assert b"Chemistry" in app.test_client().get("/").data
    assert boss.get("/quiz/Chemistry").status_code == 200


def test_an_invalid_question_shows_errors_and_saves_nothing():
    boss = admin_client()
    before = count_questions()
    response = boss.post("/admin/questions", data=valid_question(answer="E"))
    assert response.status_code == 400
    assert b"Choose which answer" in response.data
    assert b"What is 2 + 2?" in response.data
    assert count_questions() == before


def test_a_duplicate_subject_shows_a_message():
    boss = admin_client()
    response = boss.post(
        "/admin/subjects", data={"name": "Physics"}, follow_redirects=True
    )
    assert b"already exists" in response.data


def test_the_content_page_lists_the_question_bank():
    page = admin_client().get("/admin/content")
    assert b"Physics" in page.data
    assert b"Kinematics" in page.data