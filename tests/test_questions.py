import json
from pathlib import Path

import pytest

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
REQUIRED_FIELDS = {
    "id", "subject", "topic", "difficulty",
    "question", "choices", "answer", "explanation",
}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}


def load_all_questions():
    questions = []
    for path in sorted(DATA_DIR.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            questions.extend(json.load(f))
    return questions


QUESTIONS = load_all_questions()
IDS = [q.get("id", "missing-id") for q in QUESTIONS]


def test_questions_exist():
    assert len(QUESTIONS) > 0


def test_ids_are_unique():
    assert len(IDS) == len(set(IDS))


@pytest.mark.parametrize("q", QUESTIONS, ids=IDS)
def test_has_all_required_fields(q):
    assert REQUIRED_FIELDS.issubset(q.keys())


@pytest.mark.parametrize("q", QUESTIONS, ids=IDS)
def test_difficulty_is_valid(q):
    assert q["difficulty"] in VALID_DIFFICULTIES


@pytest.mark.parametrize("q", QUESTIONS, ids=IDS)
def test_has_exactly_choices_a_to_d(q):
    assert list(q["choices"].keys()) == ["A", "B", "C", "D"]


@pytest.mark.parametrize("q", QUESTIONS, ids=IDS)
def test_answer_is_one_of_the_choices(q):
    assert q["answer"] in q["choices"]


@pytest.mark.parametrize("q", QUESTIONS, ids=IDS)
def test_text_fields_are_not_empty(q):
    assert q["question"].strip() != ""
    assert q["explanation"].strip() != ""