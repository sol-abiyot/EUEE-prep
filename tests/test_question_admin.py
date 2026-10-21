from app import app
from db import get_connection
from make_admin import make_admin
from quiz import ensure_database, get_question_by_id


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


def topic_id(name):
    ensure_database()
    conn = get_connection()
    try:
        return conn.execute("SELECT id FROM topics WHERE name = ?", (name,)).fetchone()[0]
    finally:
        conn.close()


def question_form(**overrides):
    values = {
        "topic_id": str(topic_id("Kinematics")),
        "difficulty": "easy",
        "question": "A car travels at 20 m/s for 15 s. How far does it go?",
        "choice_A": "35 m",
        "choice_B": "300 m",
        "choice_C": "75 m",
        "choice_D": "1.33 m",
        "answer": "B",
        "explanation": "Distance equals speed times time, so 20 x 15 = 300 m.",
    }
    values.update(overrides)
    return values


def test_question_list_needs_an_admin():
    assert app.test_client().get("/admin/bank").status_code == 302
    assert register("alice").get("/admin/bank").status_code == 403
    page = admin_client().get("/admin/bank")
    assert page.status_code == 200
    assert b"phys-kin-001" in page.data


def test_question_list_can_be_filtered_by_topic():
    boss = admin_client()
    page = boss.get(f"/admin/bank?topic_id={topic_id('Kinematics')}")
    assert b"phys-kin-001" in page.data
    assert b"phys-dyn-001" not in page.data


def test_edit_page_shows_the_stored_question():
    page = admin_client().get("/admin/questions/phys-kin-001/edit")
    assert page.status_code == 200
    assert b"20 m/s for 15 s" in page.data


def test_editing_an_unknown_question_gives_404():
    assert admin_client().get("/admin/questions/nope/edit").status_code == 404


def test_editing_a_question_saves_the_changes():
    boss = admin_client()
    response = boss.post("/admin/questions/phys-kin-001/edit", data=question_form())
    assert response.status_code == 302
    q = get_question_by_id("phys-kin-001")
    assert q["question"] == "A car travels at 20 m/s for 15 s. How far does it go?"
    assert q["explanation"] == "Distance equals speed times time, so 20 x 15 = 300 m."


def test_an_invalid_edit_is_rejected_and_changes_nothing():
    boss = admin_client()
    original = get_question_by_id("phys-kin-001")
    response = boss.post(
        "/admin/questions/phys-kin-001/edit", data=question_form(answer="E")
    )
    assert response.status_code == 400
    assert b"Choose which answer" in response.data
    assert get_question_by_id("phys-kin-001") == original


def test_students_cannot_edit_or_delete():
    student = register("alice")
    original = get_question_by_id("phys-kin-001")
    assert student.post(
        "/admin/questions/phys-kin-001/edit", data=question_form()
    ).status_code == 403
    assert student.post("/admin/questions/phys-kin-001/delete").status_code == 403
    assert get_question_by_id("phys-kin-001") == original


def test_an_unanswered_question_can_be_deleted():
    boss = admin_client()
    boss.post("/admin/questions", data=question_form())
    assert get_question_by_id("adm-0001") is not None
    response = boss.post("/admin/questions/adm-0001/delete")
    assert response.status_code == 302
    assert get_question_by_id("adm-0001") is None


def test_an_answered_question_cannot_be_deleted():
    student = register("alice")
    student.post(
        "/submit",
        data={
            "question_id": ["phys-kin-001"],
            "subject": "Physics",
            "topic": "Kinematics",
            "answer_phys-kin-001": "B",
        },
    )
    boss = admin_client()
    response = boss.post("/admin/questions/phys-kin-001/delete", follow_redirects=True)
    assert b"cannot be deleted" in response.data
    assert get_question_by_id("phys-kin-001") is not None


def test_deleting_an_unknown_question_shows_a_message():
    response = admin_client().post(
        "/admin/questions/nope/delete", follow_redirects=True
    )
    assert b"does not exist" in response.data


def test_a_question_can_be_moved_to_another_topic():
    boss = admin_client()
    response = boss.post(
        "/admin/questions/phys-kin-001/edit",
        data=question_form(topic_id=str(topic_id("Dynamics"))),
    )
    assert response.status_code == 302
    assert get_question_by_id("phys-kin-001")["topic"] == "Dynamics"


def test_a_question_cannot_copy_the_text_of_another_in_its_topic():
    boss = admin_client()
    other_text = get_question_by_id("phys-kin-002")["question"]
    response = boss.post(
        "/admin/questions/phys-kin-001/edit", data=question_form(question=other_text)
    )
    assert response.status_code == 400
    assert b"already has that text" in response.data