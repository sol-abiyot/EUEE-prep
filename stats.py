def _count(conn, sql):
    return conn.execute(sql).fetchone()[0]


def overview(conn):
    """Headline numbers. Administrator accounts are never counted."""
    return {
        "students": _count(
            conn, "SELECT COUNT(*) FROM users WHERE role = 'student'"
        ),
        "active_students": _count(
            conn,
            "SELECT COUNT(DISTINCT a.user_id) FROM attempts a "
            "JOIN users u ON u.id = a.user_id WHERE u.role = 'student'",
        ),
        "logins": _count(
            conn,
            "SELECT COUNT(*) FROM login_events le "
            "JOIN users u ON u.id = le.user_id WHERE u.role = 'student'",
        ),
        "quizzes": _count(
            conn,
            "SELECT COUNT(*) FROM attempts a "
            "JOIN users u ON u.id = a.user_id WHERE u.role = 'student'",
        ),
        "questions": _count(conn, "SELECT COUNT(*) FROM questions"),
    }


def logins_per_day(conn, days=14):
    """Logins and distinct students per day (dates are in UTC), newest first."""
    return conn.execute(
        """
        SELECT date(le.logged_in_at) AS day,
               COUNT(*) AS logins,
               COUNT(DISTINCT le.user_id) AS students
        FROM login_events le
        JOIN users u ON u.id = le.user_id
        WHERE u.role = 'student' AND le.logged_in_at >= datetime('now', ?)
        GROUP BY day
        ORDER BY day DESC
        """,
        (f"-{days} days",),
    ).fetchall()


def subject_scores(conn):
    """Number of quizzes and the average percentage for each subject."""
    return conn.execute(
        """
        SELECT a.subject AS subject,
               COUNT(*) AS attempts,
               ROUND(AVG(100.0 * a.score / a.total), 1) AS avg_percent
        FROM attempts a
        JOIN users u ON u.id = a.user_id
        WHERE u.role = 'student' AND a.total > 0
        GROUP BY a.subject
        ORDER BY a.subject
        """
    ).fetchall()


def most_missed_questions(conn, limit=10):
    """The questions students get wrong most often."""
    return conn.execute(
        """
        SELECT q.id AS id,
               q.question_text AS question_text,
               COUNT(*) AS times_answered,
               SUM(1 - aa.is_correct) AS times_wrong,
               ROUND(100.0 * SUM(1 - aa.is_correct) / COUNT(*), 1) AS wrong_percent
        FROM attempt_answers aa
        JOIN attempts a ON a.id = aa.attempt_id
        JOIN users u ON u.id = a.user_id
        JOIN questions q ON q.id = aa.question_id
        WHERE u.role = 'student'
        GROUP BY q.id
        ORDER BY wrong_percent DESC, times_answered DESC, q.id
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def recent_students(conn, limit=50):
    """Newest students first, with how many quizzes each has taken."""
    return conn.execute(
        """
        SELECT u.username AS username,
               u.display_name AS display_name,
               u.created_at AS created_at,
               u.last_login_at AS last_login_at,
               COUNT(a.id) AS quizzes
        FROM users u
        LEFT JOIN attempts a ON a.user_id = u.id
        WHERE u.role = 'student'
        GROUP BY u.id
        ORDER BY u.id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()