from __future__ import annotations

import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "mail_server.db"
MAIL_DATA_DIR = BASE_DIR / "mail_data"

TEST_USERS = [
    ("admin", "123456"),
    ("alice", "alice123"),
    ("bob", "bob123"),
]


def init_database() -> None:
    MAIL_DATA_DIR.mkdir(exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                receiver TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                file_path TEXT NOT NULL
            )
            """
        )

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_emails_receiver ON emails (receiver)"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_emails_sender ON emails (sender)")

        conn.executemany(
            """
            INSERT OR IGNORE INTO users (username, password)
            VALUES (?, ?)
            """,
            TEST_USERS,
        )


if __name__ == "__main__":
    init_database()
    print(f"Database initialized: {DB_PATH}")
    print(f"Mail data directory ready: {MAIL_DATA_DIR}")
