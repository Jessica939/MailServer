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
                file_path TEXT NOT NULL,
                is_spam INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        ensure_email_columns(conn)

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                mime_type TEXT,
                file_path TEXT NOT NULL,
                size INTEGER NOT NULL,
                FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE CASCADE
            )
            """
        )

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_emails_receiver ON emails (receiver)"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_emails_sender ON emails (sender)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_attachments_email_id ON attachments (email_id)")

        conn.executemany(
            """
            INSERT OR IGNORE INTO users (username, password)
            VALUES (?, ?)
            """,
            TEST_USERS,
        )


def ensure_email_columns(conn: sqlite3.Connection) -> None:
    columns = {
        row[1]
        for row in conn.execute("PRAGMA table_info(emails)").fetchall()
    }
    if "is_spam" not in columns:
        conn.execute("ALTER TABLE emails ADD COLUMN is_spam INTEGER NOT NULL DEFAULT 0")


if __name__ == "__main__":
    init_database()
    print(f"Database initialized: {DB_PATH}")
    print(f"Mail data directory ready: {MAIL_DATA_DIR}")
