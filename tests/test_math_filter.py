from app import app, math_filter

client = app.test_client()


def test_superscript():
    assert math_filter("x^2 - 5x + 6") == "x<sup>2</sup> - 5x + 6"


def test_units_squared():
    assert math_filter("4 m/s^2") == "4 m/s<sup>2</sup>"


def test_degrees():
    assert math_filter("sin 30 degrees") == "sin 30°"


def test_ohm():
    assert math_filter("a 4 ohm resistor") == "a 4 Ω resistor"


def test_square_root():
    assert math_filter("sqrt(3)/2") == "√(3)/2"


def test_pi():
    assert math_filter("pi x r^2") == "π x r<sup>2</sup>"


def test_html_in_text_is_escaped():
    assert math_filter("<script>alert(1)</script>") == "&lt;script&gt;alert(1)&lt;/script&gt;"


def test_quiz_page_uses_the_filter():
    response = client.get("/quiz/Mathematics?topic=Geometry&limit=50")
    assert b"cm<sup>2</sup>" in response.data