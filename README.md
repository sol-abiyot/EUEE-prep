# EUEE Prep

EUEE Prep is a web application that helps Ethiopian students practise for the Ethiopian University Entrance Examination (EUEE). Students register, choose a subject and topic, take a multiple-choice quiz, and get an automatic score with an explanation for every answer. An administrator can see how many students use the platform and can add or change subjects, topics and questions.

**Important:** all practice questions are original EUEE-style questions written for this project. They are **not** official past-paper questions.

## Project team and roles

| Name | Role | Responsibilities |
|------|------|------------------|
| Solomon Getachew Habte | Project owner and sole developer | Requirements and design, back-end (Flask, SQLite), front-end (templates, CSS), writing the original questions, automated and manual testing, documentation |

## Features implemented

- Student registration (username, email, optional phone number) with hashed passwords, login and logout
- Quizzes require login; visitors are sent to the login page and returned to their quiz afterwards
- Subject and topic selection, with a chosen number of questions per quiz
- Multiple-choice questions, automatic marking, score and percentage
- Results page with the correct answer and an explanation for every question
- "My results" page: each student's past quizzes, with a review of each one
- Readable maths notation (powers, units, square roots, pi)
- Responsive layout for phones and computers
- Administrator dashboard: registered students, logins per day, quizzes taken, average score per subject, most-missed questions
- Administrator tools: add subjects, topics and questions; edit questions; delete questions that no student has answered
- Form protection against cross-site request forgery (CSRF), friendly error pages
- Automated tests (pytest) and a manual test log

## Technology

| Part | Choice |
|------|--------|
| Language | Python |
| Web framework | Flask (server-rendered pages with Jinja templates) |
| Database | SQLite |
| Styling | Plain CSS |
| Tests | pytest |
| Version control | Git and GitHub |

## How to run it (Windows PowerShell)

```powershell
git clone https://github.com/sol-abiyot/EUEE-prep.git
cd EUEE-prep
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Then open **http://127.0.0.1:5000** in a browser. On the first run the app creates its database in `instance/euee.db` and loads the starter questions from the `data/` folder.

### Create an administrator

1. Register a normal account on the website.
2. Stop the app (Ctrl+C), then run: `python make_admin.py <username>`
3. Start the app again and log in. An **Admin** link appears in the header.

There is deliberately no way to become an administrator through the website.

### Run the tests

```powershell
python -m pytest -q
```

Manual test results are recorded in `docs/manual_tests.md`.

### Back up the database

Stop the app and copy `instance/euee.db` somewhere safe. It contains accounts, quiz history and every question added through the admin pages. Do not run `python db.py` unless you want to reload the original questions from the JSON files; it asks for confirmation first.

## Project structure

| Path | Purpose |
|------|---------|
| `app.py` | Flask routes, login and admin checks, error pages |
| `db.py` | Database schema and loading of the starter questions |
| `quiz.py` | Reading questions and creating quizzes |
| `grading.py` | Marking and score calculation |
| `auth.py` | Registration checks, password hashing, login |
| `attempts.py` | Saving and reading quiz attempts |
| `stats.py` | Usage statistics for the dashboard |
| `content.py` | Admin checks and changes for subjects, topics and questions |
| `make_admin.py` | Gives an account the admin role |
| `data/` | Starter questions (one JSON file per subject) |
| `templates/`, `static/` | Pages and stylesheet |
| `tests/` | Automated tests |
| `docs/` | Manual test log and project documents |

## Database design

SQLite, with these tables: `subjects`, `topics` (belong to a subject), `questions` (belong to a topic), `choices` (four per question), `users` (role is student or admin), `login_events`, `attempts` (one per submitted quiz) and `attempt_answers` (one row per question answered). Rules such as valid answer letters, unique usernames and linked records are enforced by the database itself.

## Security measures

- Passwords are stored only as salted hashes
- Session cookies are marked HttpOnly and SameSite
- Every form that changes data carries a CSRF token
- Administrator pages refuse everyone else, and students can only open their own quiz results
- The secret key is kept in the `instance/` folder (or the `EUEE_SECRET_KEY` environment variable), which is not committed to Git
- Database queries use parameters, not text joined into SQL

## Known limitations

- Email addresses are checked for format only; there is no email verification and no password reset
- No limit on repeated login attempts
- Runs on Flask's development server over plain HTTP; it has not been deployed
- Small starter question bank (Mathematics and Physics only); equations are plain text
- SQLite suits a single computer or a small number of users, not heavy simultaneous use
- Questions cannot be hidden, only edited or (if unanswered) deleted

## Planned improvements

Email verification and password reset, more subjects (Chemistry, Biology, English) and many more questions, timed mock exams, PostgreSQL for deployment, and proper maths rendering.

## Screenshots

<!-- Add screenshots here after capturing them, for example: ![Home page](docs/screenshots/home.png) -->

## Development approach and AI assistance

This project was built with the help of an AI assistant (Claude, by Anthropic) for guidance, code drafting and review. The author ran, tested and revised the application step by step, and wrote the original practice questions with the assistant's help in checking them.