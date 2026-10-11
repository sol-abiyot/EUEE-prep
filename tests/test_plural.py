from app import app, plural

client = app.test_client()


def test_one_is_singular():
    assert plural(1) == "1 question"


def test_many_is_plural():
    assert plural(10) == "10 questions"


def test_zero_is_plural():
    assert plural(0) == "0 questions"


def test_custom_word():
    assert plural(1, "topic") == "1 topic"
    assert plural(7, "topic") == "7 topics"


def test_subject_page_uses_correct_grammar():
    response = client.get("/subject/Mathematics")
    assert b"1 questions" not in response.data
    assert b"1 question" in response.data