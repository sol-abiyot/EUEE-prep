import app as app_module
from app import app

client = app.test_client()


def test_opening_submit_directly_shows_a_friendly_page():
    response = client.get("/submit")
    assert response.status_code == 405
    assert b"Not allowed" in response.data


def test_unexpected_error_shows_a_friendly_page(monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(app_module, "list_subjects", broken)
    response = client.get("/")
    assert response.status_code == 500
    assert b"Something went wrong" in response.data