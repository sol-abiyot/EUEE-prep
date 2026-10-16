import pytest

import db
import quiz
from app import app


@pytest.fixture(autouse=True)
def fresh_database(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(quiz, "_database_ready", False)
    # Most tests are about quizzes, not logins, so they run with the login
    # requirement switched off. tests/test_access.py switches it back on.
    monkeypatch.setitem(app.config, "REQUIRE_LOGIN", False)