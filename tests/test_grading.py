from grading import mark_quiz
from quiz import get_questions

QUESTIONS = [
    {"id": "q1", "question": "Pick B", "choices": {"A": "a", "B": "b", "C": "c", "D": "d"},
     "answer": "B", "explanation": "B is right."},
    {"id": "q2", "question": "Pick C", "choices": {"A": "a", "B": "b", "C": "c", "D": "d"},
     "answer": "C", "explanation": "C is right."},
    {"id": "q3", "question": "Pick A", "choices": {"A": "a", "B": "b", "C": "c", "D": "d"},
     "answer": "A", "explanation": "A is right."},
    {"id": "q4", "question": "Pick D", "choices": {"A": "a", "B": "b", "C": "c", "D": "d"},
     "answer": "D", "explanation": "D is right."},
]


def test_all_correct():
    result = mark_quiz(QUESTIONS, {"q1": "B", "q2": "C", "q3": "A", "q4": "D"})
    assert result["score"] == 4
    assert result["total"] == 4
    assert result["percentage"] == 100.0


def test_all_wrong():
    result = mark_quiz(QUESTIONS, {"q1": "A", "q2": "A", "q3": "B", "q4": "A"})
    assert result["score"] == 0
    assert result["percentage"] == 0.0


def test_mixed_with_unanswered_and_invalid():
    answers = {"q1": "B", "q2": "A", "q4": "E"}  # q3 missing on purpose
    result = mark_quiz(QUESTIONS, answers)
    statuses = [r["status"] for r in result["results"]]
    assert statuses == ["correct", "incorrect", "unanswered", "invalid"]
    assert result["score"] == 1
    assert result["percentage"] == 25.0


def test_lowercase_and_spaces_are_accepted():
    result = mark_quiz(QUESTIONS, {"q1": " b "})
    assert result["results"][0]["status"] == "correct"


def test_no_questions_does_not_crash():
    result = mark_quiz([], {})
    assert result["total"] == 0
    assert result["percentage"] == 0.0


def test_result_shows_the_real_answer_key_and_explanation():
    result = mark_quiz(QUESTIONS, {"q1": "A"})
    first = result["results"][0]
    assert first["correct_answer"] == "B"
    assert first["explanation"] == "B is right."


def test_answering_every_real_question_with_the_key_gives_full_marks():
    questions = get_questions()
    answers = {q["id"]: q["answer"] for q in questions}
    result = mark_quiz(questions, answers)
    assert result["score"] == result["total"] == len(questions)
    assert result["percentage"] == 100.0