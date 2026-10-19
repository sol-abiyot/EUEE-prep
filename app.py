import os
import re
import secrets
from functools import wraps
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
    normalize_email,
    normalize_phone,
    record_login,
    validate_registration,
)
from attempts import get_attempt, list_attempts, save_attempt
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
app.config["REQUIRE_LOGIN"] = True

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


def safe_next(value):
    """Only allow redirects to pages inside this site."""
    if value and value.startswith("/") and not value.startswith("//") and "\\" not in value:
        return value
    return ""


def login_required(view):
    """Send visitors who are not logged in to the login page."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if app.config["REQUIRE_LOGIN"] and g.user is None:
            target = request.full_path.rstrip("?") if request.method == "GET" else None
            return redirect(url_for("login", next=target))
        return view(*args, **kwargs)

    return wrapped


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
@login_required
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
@login_required
def submit():
    # Remove duplicate ids but keep the original order.
    ids = list(dict.fromkeys(request.form.getlist("question_id")))
    questions = [q for q in (get_question_by_id(i) for i in ids) if q is not None]
    if not questions:
        return redirect(url_for("home"))

    answers = {q["id"]: request.form.get("answer_" + q["id"], "") for q in questions}
    result = mark_quiz(questions, answers)

    if g.user is None:
        # Only happens when REQUIRE_LOGIN is off (in tests): show the result, do not save it.
        return render_template(
            "results.html",
            result=result,
            subject=request.form.get("subject", ""),
            topic=request.form.get("topic") or None,
        )

    conn = database()
    try:
        attempt_id = save_attempt(
            conn, g.user["id"], questions, result, request.form.get("topic") or None
        )
    finally:
        conn.close()
    return redirect(url_for("attempt_detail", attempt_id=attempt_id))


@app.route("/attempt/<int:attempt_id>")
def attempt_detail(attempt_id):
    if g.user is None:
        return redirect(url_for("login", next=request.path))
    conn = database()
    try:
        attempt, rows = get_attempt(conn, attempt_id, g.user["id"])
    finally:
        conn.close()
    if attempt is None:
        abort(404)

    questions = [
        q for q in (get_question_by_id(r["question_id"]) for r in rows) if q is not None
    ]
    answers = {r["question_id"]: r["chosen"] or "" for r in rows}
    result = mark_quiz(questions, answers)
    return render_template(
        "results.html", result=result, subject=attempt["subject"], topic=attempt["topic"]
    )


@app.route("/history")
def history():
    if g.user is None:
        return redirect(url_for("login", next="/history"))
    conn = database()
    try:
        rows = list_attempts(conn, g.user["id"])
    finally:
        conn.close()
    attempts = [
        {
            **dict(r),
            "percentage": round(r["score"] / r["total"] * 100, 1) if r["total"] else 0.0,
        }
        for r in rows
    ]
    return render_template("history.html", attempts=attempts)

@app.route("/register", methods=["GET", "POST"])
def register():
    next_url = safe_next(request.values.get("next", ""))
    errors = []
    form = {"username": "", "display_name": "", "email": "", "phone": ""}
    if request.method == "POST":
        form["username"] = request.form.get("username", "").strip()
        form["display_name"] = request.form.get("display_name", "").strip()[:60]
        form["email"] = request.form.get("email", "").strip()
        form["phone"] = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        errors = validate_registration(
            form["username"], password, confirm, form["email"], form["phone"]
        )
        if not errors:
            conn = database()
            try:
                user_id, problem = create_user(
                    conn,
                    form["username"],
                    password,
                    form["display_name"],
                    normalize_email(form["email"]),
                    normalize_phone(form["phone"]) or None,
                )
                if problem:
                    errors.append(problem)
                else:
                    record_login(conn, user_id)
                    session.clear()
                    session["user_id"] = user_id
                    return redirect(next_url or url_for("home"))
            finally:
                conn.close()
    return render_template(
        "register.html", errors=errors, form=form, next_url=next_url
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    next_url = safe_next(request.values.get("next", ""))
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
                return redirect(next_url or url_for("home"))
        finally:
            conn.close()
    return render_template("login.html", error=error, next_url=next_url)


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