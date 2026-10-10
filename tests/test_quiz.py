from quiz import (
    get_question_by_id,
    get_questions,
    list_subjects,
    list_topics,
)


def test_list_subjects():
    assert {"Mathematics", "Physics"}.issubset(set(list_subjects()))


def test_list_topics():
    assert "Algebra" in list_topics("Mathematics")


def test_get_questions_by_subject():
    result = get_questions("Mathematics")
    assert len(result) > 0
    assert all(q["subject"] == "Mathematics" for q in result)


def test_subject_is_case_insensitive():
    assert len(get_questions("physics")) == len(get_questions("Physics"))


def test_get_questions_by_topic():
    result = get_questions("Physics", "Kinematics")
    assert len(result) == 2
    assert all(q["topic"] == "Kinematics" for q in result)


def test_unknown_subject_returns_empty_list():
    assert get_questions("Astrology") == []


def test_get_question_by_id():
    assert get_question_by_id("math-alg-001")["answer"] == "B"


def test_unknown_id_returns_none():
    assert get_question_by_id("does-not-exist") is None