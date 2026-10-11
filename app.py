from flask import Flask, abort, redirect, render_template, request, url_for
import re

from markupsafe import Markup, escape
from grading import mark_quiz
from quiz import (
    generate_quiz,
    get_question_by_id,
    get_questions,
    list_subjects,
    list_topics,
)

app = Flask(__name__)
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

DEFAULT_QUIZ_LENGTH = 5
MAX_QUIZ_LENGTH = 50


def find_subject(name):
    """Return the properly capitalised subject name, or None if it does not exist."""
    return next((s for s in list_subjects() if s.lower() == name.lower()), None)


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


@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)