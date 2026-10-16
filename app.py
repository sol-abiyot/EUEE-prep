import os
import re
import secrets
from pathlib import Path

from flask import (
    Flask,
    abort,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from markupsafe import Markup, escape

from auth import (
    check_login,
    create_user,
    get_user,
    record_login,
    validate_registration,
)
from db import get_connection
from grading import mark_quiz
from quiz import (
    ensure_database,
    generate_quiz,
    get_question_by_id,
    get_questions,
    list_subjects,
    list_topics,
)

app = Flask(__name__)


def load_secret_key():
    """Use EUEE_SECRET_KEY if set; otherwise create and reuse a random key in instance/."""
    key = os.environ.get("EUEE_SECRET_KEY")
    if key:
        return key
    key_file = Path(app.instance_path) / "secret_key"
    if not key_file.exists():
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_text(secrets.token_hex(32))
    return key_file.read_text().strip()


app.secret_key = load_secret_key()
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

DEFAULT_QUIZ_LENGTH = 5
MAX_QUIZ_LENGTH = 50


@app.template_filter("math")
def math_filter(text):
    """Make plain-text maths readable: x^2 -> x<sup>2</sup>, pi -> the pi symbol, etc."""
    safe = str(escape(text))
    safe = re.sub(r"\^(-?\w+)", r"<sup>\1</sup>", safe)
    safe = safe.replace("sqrt(", "√(")
    safe = re.sub(r"\bpi\b", "π", safe)
    safe = re.sub(r"(?<=\d) degrees?\b", "°", safe)
    safe = re.sub(r"(?<=\d) ohm\b", " Ω", safe)
    return Markup(safe)


@app.template_filter("plural")
def plural(count, word="question"):
    """Return '1 question' or '5 questions'."""
    return f"{count} {word}" + ("" if count == 1 else "s")


def database():
    """Open the database, making sure the tables exist first."""
    ensure_database()
    return get_connection()


def find_subject(name):
    """Return the properly capitalised subject name, or None if it does not exist."""
    return next((s for s in list_subjects() if s.lower() == name.lower()), None)


@app.before_request
def load_current_user():
    g.user = None
    if request.endpoint == "static":
        return
    user_id = session.get("user_id")
    if user_id is None:
        return
    conn = database()
    try:
        g.user = get_user(conn, user_id)
    finally:
        conn.close()
    if g.user is None:
        session.pop("user_id", None)


@app.context_processor
def inject_current_user():
    return {"current_user": getattr(g, "user", None)}


@app.route("/")
def home():
    subjects = [
        {"name": s, "count": len(get_questions(s))} for s in list_subjects()
    ]
    return render_template("index.html", subjects=subjects)


@app.route("/subject/<name>")
def subject(name):
    match = find_subject(name)
    if match is None:
        abort(404)
    topics = [
        {"name": t, "count": len(get_questions(match, t))}
        for t in list_topics(match)
    ]
    return render_template(
        "subject.html",
        subject=match,
        topics=topics,
        total=len(get_questions(match)),
    )


@app.route("/quiz/<name>")
def quiz_page(name):
    match = find_subject(name)
    if match is None:
        abort(404)

    topic = request.args.get("topic") or None
    limit = request.args.get("limit", default=DEFAULT_QUIZ_LENGTH, type=int)
    if limit < 1 or limit > MAX_QUIZ_LENGTH:
        limit = DEFAULT_QUIZ_LENGTH

    questions = generate_quiz(match, topic, limit)
    if not questions:
        abort(404)
    return render_template(
        "quiz.html", subject=match, topic=topic, questions=questions
    )


@app.route("/submit", methods=["POST"])
def submit():
    # Remove duplicate ids but keep the original order.
    ids = list(dict.fromkeys(request.form.getlist("question_id")))
    questions = [q for q in (get_question_by_id(i) for i in ids) if q is not None]
    if not questions:
        return redirect(url_for("home"))

    answers = {q["id"]: request.form.get("answer_" + q["id"], "") for q in questions}
    result = mark_quiz(questions, answers)
    return render_template(
        "results.html",
        result=result,
        subject=request.form.get("subject", ""),
        topic=request.form.get("topic") or None,
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    errors = []
    username = ""
    display_name = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        display_name = request.form.get("display_name", "").strip()[:60]
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        errors = validate_registration(username, password, confirm)
        if not errors:
            conn = database()
            try:
                user_id = create_user(conn, username, password, display_name)
                if user_id is None:
                    errors.append("That username is already taken.")
                else:
                    record_login(conn, user_id)
                    session.clear()
                    session["user_id"] = user_id
                    return redirect(url_for("home"))
            finally:
                conn.close()
    return render_template(
        "register.html", errors=errors, username=username, display_name=display_name
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        conn = database()
        try:
            user = check_login(conn, username, password)
            if user is None:
                error = "Wrong username or password."
            else:
                record_login(conn, user["id"])
                session.clear()
                session["user_id"] = user["id"]
                return redirect(url_for("home"))
        finally:
            conn.close()
    return render_template("login.html", error=error)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404


@app.errorhandler(405)
def method_not_allowed(error):
    return render_template(
        "error.html",
        title="Not allowed",
        message="That page cannot be opened this way. Please start from the home page.",
    ), 405


@app.errorhandler(500)
def server_error(error):
    return render_template(
        "error.html",
        title="Something went wrong",
        message="An unexpected error occurred. Please go back and try again.",
    ), 500


if __name__ == "__main__":
    app.run(debug=True)