from app import app

client = app.test_client()


def test_stylesheet_is_served():
    response = client.get("/static/style.css")
    assert response.status_code == 200
    assert b"--brand" in response.data


def test_home_page_links_the_stylesheet():
    response = client.get("/")
    assert b"/static/style.css" in response.data