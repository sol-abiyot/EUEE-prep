from db import fetch_all_questions, get_connection, init_db, seed_from_json
from quiz import get_questions, load_questions, load_questions_from_json


def test_database_returns_exactly_what_the_json_files_contain(tmp_path):
    conn = get_connection(tmp_path / "check.db")
    init_db(conn)
    seed_from_json(conn)
    from_db = {q["id"]: q for q in fetch_all_questions(conn)}
    conn.close()

    for q in load_questions_from_json():
        assert from_db[q["id"]] == q


def test_the_app_loads_every_question_from_the_database():
    assert len(load_questions()) == len(load_questions_from_json())


def test_filtering_still_works_through_the_database():
    assert len(get_questions("Physics", "Kinematics")) == 2