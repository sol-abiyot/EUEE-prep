import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"


def load_questions():
    """Read every .json file in the data folder and return one list of questions."""
    questions = []
    for path in sorted(DATA_DIR.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            questions.extend(json.load(f))
    return questions


def list_subjects():
    return sorted({q["subject"] for q in load_questions()})


def list_topics(subject):
    return sorted({
        q["topic"]
        for q in load_questions()
        if q["subject"].lower() == subject.lower()
    })


def get_questions(subject=None, topic=None):
    """Return questions, optionally filtered by subject and/or topic."""
    result = load_questions()
    if subject:
        result = [q for q in result if q["subject"].lower() == subject.lower()]
    if topic:
        result = [q for q in result if q["topic"].lower() == topic.lower()]
    return result


def get_question_by_id(question_id):
    for q in load_questions():
        if q["id"] == question_id:
            return q
    return None