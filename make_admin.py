import sys

from db import get_connection
from quiz import ensure_database


def make_admin(username):
    """Give an existing account the admin role. Returns True if the account was found."""
    ensure_database()
    conn = get_connection()
    try:
        cursor = conn.execute(
            "UPDATE users SET role = 'admin' WHERE lower(username) = lower(?)",
            (username,),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python make_admin.py <username>")
        sys.exit(1)
    if make_admin(sys.argv[1]):
        print(sys.argv[1], "is now an administrator.")
    else:
        print("No account called", sys.argv[1], "was found. Register it first.")
        sys.exit(1)