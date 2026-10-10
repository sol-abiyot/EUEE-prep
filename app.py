from flask import Flask, abort, render_template

from quiz import get_questions, list_subjects, list_topics

app = Flask(__name__)


@app.route("/")
def home():
    subjects = [
        {"name": s, "count": len(get_questions(s))} for s in list_subjects()
    ]
    return render_template("index.html", subjects=subjects)


@app.route("/subject/<name>")
def subject(name):
    match = next((s for s in list_subjects() if s.lower() == name.lower()), None)
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


@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)