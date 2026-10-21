import pytest

import db
import quiz
from app import app


@pytest.fixture(autouse=True)
def fresh_database(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(quiz, "_database_ready", False)
    # Most tests are about quizzes, not logins or form tokens, so they run with
    # those protections switched off. test_access.py and test_csrf.py switch them on.
    monkeypatch.setitem(app.config, "REQUIRE_LOGIN", False)
    monkeypatch.setitem(app.config, "CSRF_ENABLED", False)