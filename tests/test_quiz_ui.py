from app import app

client = app.test_client()


def test_subject_page_has_the_quiz_setup_form():
    response = client.get("/subject/Physics")
    assert b'name="limit"' in response.data
    assert b'name="topic"' in response.data


def test_limit_ten_gives_ten_questions():
    response = client.get("/quiz/Mathematics?limit=10")
    assert response.data.count(b'type="radio"') == 40


def test_quiz_page_has_jump_links():
    response = client.get("/quiz/Mathematics?limit=5")
    assert b'id="q1"' in response.data
    assert b'href="#q5"' in response.data


def test_quiz_page_has_progress_counter():
    response = client.get("/quiz/Mathematics")
    assert b'id="answered"' in response.data


def test_text_instead_of_a_number_falls_back_to_default():
    response = client.get("/quiz/Mathematics?limit=abc")
    assert response.status_code == 200
    assert response.data.count(b'type="radio"') == 20


def test_absurd_limit_falls_back_to_default():
    response = client.get("/quiz/Mathematics?limit=999")
    assert response.status_code == 200
    assert response.data.count(b'type="radio"') == 20