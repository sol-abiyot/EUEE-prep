import re

import pytest

from app import app
from grading import mark_quiz
from quiz import get_question_by_id, get_questions

client = app.test_client()
ALL = get_questions()


def test_full_journey_from_home_to_perfect_score():
    assert client.get("/").status_code == 200
    assert client.get("/subject/Mathematics").status_code == 200

    page = client.get("/quiz/Mathematics?limit=5").data.decode()
    ids = re.findall(r'name="question_id" value="([^"]+)"', page)
    assert len(ids) == 5

    data = {"question_id": ids, "subject": "Mathematics", "topic": ""}
    for question_id in ids:
        data["answer_" + question_id] = get_question_by_id(question_id)["answer"]

    response = client.post("/submit", data=data)
    assert response.status_code == 200
    assert b"5 / 5" in response.data
    assert b"100.0%" in response.data


@pytest.mark.parametrize("q", ALL, ids=[q["id"] for q in ALL])
def test_only_the_keyed_answer_scores_and_explanation_matches(q):
    for letter in q["choices"]:
        result = mark_quiz([q], {q["id"]: letter})
        expected = 1 if letter == q["answer"] else 0
        assert result["score"] == expected
        assert result["results"][0]["explanation"] == q["explanation"]


def test_results_page_offers_restart_and_navigation_links():
    data = {"question_id": ["phys-kin-001"], "subject": "Physics", "topic": ""}
    response = client.post("/submit", data=data)
    assert b'href="/quiz/Physics"' in response.data
    assert b'href="/subject/Physics"' in response.data
    assert b'href="/"' in response.data


def test_duplicate_question_ids_are_counted_once():
    data = {
        "question_id": ["phys-kin-001", "phys-kin-001"],
        "answer_phys-kin-001": "B",
        "subject": "Physics",
    }
    response = client.post("/submit", data=data)
    assert b"1 / 1" in response.data


@pytest.mark.parametrize(
    "url",
    [
        "/quiz",
        "/quiz/",
        "/subject/",
        "/subject/%20",
        "/quiz/Physics?topic=%3Cscript%3E",
        "/results",
        "/static/missing.css",
    ],
)
def test_odd_urls_never_crash(url):
    assert client.get(url).status_code in (404, 405)