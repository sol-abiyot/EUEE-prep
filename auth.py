import re

from werkzeug.security import check_password_hash, generate_password_hash

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,30}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_PATTERN = re.compile(r"^\+?\d{9,15}$")
MIN_PASSWORD_LENGTH = 8


def normalize_email(email):
    return email.strip().lower()


def normalize_phone(phone):
    return re.sub(r"[\s\-()]", "", phone.strip())


def validate_registration(username, password, confirm, email, phone=""):
    """Return a list of problems (an empty list means the input is acceptable)."""
    errors = []
    if not USERNAME_PATTERN.match(username):
        errors.append("Username must be 3 to 30 letters, numbers or underscores.")
    email = normalize_email(email)
    if not EMAIL_PATTERN.match(email) or len(email) > 120:
        errors.append("Please enter a valid email address.")
    phone = normalize_phone(phone)
    if phone and not PHONE_PATTERN.match(phone):
        errors.append("Phone number must be 9 to 15 digits, optionally starting with +.")
    if len(password) < MIN_PASSWORD_LENGTH:
        errors.append(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if password != confirm:
        errors.append("The two passwords do not match.")
    return errors


def create_user(conn, username, password, display_name=None, email=None, phone=None,
                role="student"):
    """Add a user. Returns (user_id, problem); problem is None when it worked."""
    if conn.execute(
        "SELECT 1 FROM users WHERE lower(username) = lower(?)", (username,)
    ).fetchone():
        return None, "That username is already taken."
    if email and conn.execute(
        "SELECT 1 FROM users WHERE email = ?", (email,)
    ).fetchone():
        return None, "That email address is already registered."
    cursor = conn.execute(
        "INSERT INTO users (username, display_name, email, phone, password_hash, role) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            username,
            display_name or None,
            email or None,
            phone or None,
            generate_password_hash(password),
            role,
        ),
    )
    conn.commit()
    return cursor.lastrowid, None


def check_login(conn, username, password):
    """Return the user row if the username and password are right, otherwise None."""
    user = conn.execute(
        "SELECT * FROM users WHERE lower(username) = lower(?)", (username,)
    ).fetchone()
    if user is not None and check_password_hash(user["password_hash"], password):
        return user
    return None


def record_login(conn, user_id):
    """Remember that this user logged in (used later for usage statistics)."""
    conn.execute("INSERT INTO login_events (user_id) VALUES (?)", (user_id,))
    conn.execute(
        "UPDATE users SET last_login_at = datetime('now') WHERE id = ?", (user_id,)
    )
    conn.commit()


def get_user(conn, user_id):
    return conn.execute(
        "SELECT id, username, display_name, role FROM users WHERE id = ?", (user_id,)
    ).fetchone()