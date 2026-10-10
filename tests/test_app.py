from app import app

client = app.test_client()


def test_home_page_loads():
    response = client.get("/")
    assert response.status_code == 200


def test_home_page_lists_both_subjects():
    response = client.get("/")
    assert b"Mathematics" in response.data
    assert b"Physics" in response.data


def test_subject_page_lists_topics():
    response = client.get("/subject/Physics")
    assert response.status_code == 200
    assert b"Kinematics" in response.data


def test_unknown_subject_gives_404_page_not_a_crash():
    response = client.get("/subject/Astrology")
    assert response.status_code == 404
    assert b"Page not found" in response.data


def test_unknown_url_gives_404_page_not_a_crash():
    response = client.get("/no-such-page")
    assert response.status_code == 404