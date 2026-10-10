from app import app

client = app.test_client()

# Known questions from the Physics bank (answers: phys-kin-001 = B, phys-kin-002 = C).
IDS = ["phys-kin-001", "phys-kin-002"]


def submit(answers, ids=IDS):
    data = {"question_id": ids, "subject": "Physics"}
    for question_id, letter in answers.items():
        data["answer_" + question_id] = letter
    return client.post("/submit", data=data)


def test_quiz_page_shows_five_questions_with_four_choices_each():
    response = client.get("/quiz/Physics")
    assert response.status_code == 200
    assert response.data.count(b'type="radio"') == 20


def test_topic_quiz_shows_only_that_topic():
    response = client.get("/quiz/Physics?topic=Kinematics")
    assert response.status_code == 200
    assert response.data.count(b'type="radio"') == 8


def test_unknown_subject_quiz_gives_404():
    assert client.get("/quiz/Astrology").status_code == 404


def test_unknown_topic_quiz_gives_404():
    assert client.get("/quiz/Physics?topic=Nothing").status_code == 404


def test_all_correct_gives_full_marks():
    response = submit({"phys-kin-001": "B", "phys-kin-002": "C"})
    assert response.status_code == 200
    assert b"2 / 2" in response.data
    assert b"100.0%" in response.data


def test_all_wrong_gives_zero():
    response = submit({"phys-kin-001": "A", "phys-kin-002": "A"})
    assert b"0 / 2" in response.data
    assert b"Incorrect" in response.data


def test_empty_submission_is_handled_without_crashing():
    response = submit({})
    assert response.status_code == 200
    assert b"0 / 2" in response.data
    assert b"Unanswered" in response.data


def test_invalid_choice_is_handled_without_crashing():
    response = submit({"phys-kin-001": "Z"}, ids=["phys-kin-001"])
    assert response.status_code == 200
    assert b"0 / 1" in response.data
    assert b"Invalid" in response.data


def test_submission_without_questions_redirects_home():
    response = client.post("/submit", data={})
    assert response.status_code == 302


def test_submission_with_unknown_question_ids_redirects_home():
    response = client.post("/submit", data={"question_id": ["fake-id"]})
    assert response.status_code == 302


def test_submit_page_cannot_be_opened_directly():
    assert client.get("/submit").status_code == 405


def test_results_show_the_matching_explanation():
    response = submit({"phys-kin-001": "A"}, ids=["phys-kin-001"])
    assert b"distance = speed x time" in response.data