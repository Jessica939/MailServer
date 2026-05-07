from __future__ import annotations

import argparse
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from email import policy
from email.parser import BytesParser
import os
import re

from aiosmtpd.controller import Controller

from init_db import DB_PATH, MAIL_DATA_DIR, init_database
from tls_config import CERT_PATH, KEY_PATH, create_server_ssl_context


BASE_DIR = Path(__file__).resolve().parent


class MailStoreHandler:
    async def handle_DATA(self, server, session, envelope) -> str:
        mail_bytes = envelope.original_content
        if mail_bytes is None:
            mail_bytes = envelope.content
        if isinstance(mail_bytes, str):
            mail_bytes = mail_bytes.encode("utf-8")

        # save raw message
        filename = f"{int(time.time())}_{uuid.uuid4().hex}.eml"
        message_path = MAIL_DATA_DIR / filename
        message_path.write_bytes(mail_bytes)

        relative_path = message_path.relative_to(BASE_DIR).as_posix()
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        sender = envelope.mail_from
        receivers = envelope.rcpt_tos or []

        # parse MIME parts and extract attachments by streaming from saved .eml file
        attachments_saved: list[tuple[str, str, Path, int]] = []

        def sanitize_filename(name: str) -> str:
            name = os.path.basename(name or "")
            name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
            if not name or name in {"", ".", ".."}:
                name = "attachment"
            if len(name) > 200:
                name = name[:200]
            return name

        def unique_path(directory: Path, name: str) -> Path:
            candidate = directory / name
            if not candidate.exists():
                return candidate
            base, ext = os.path.splitext(name)
            i = 1
            while True:
                candidate = directory / f"{base}_{i}{ext}"
                if not candidate.exists():
                    return candidate
                i += 1

        attachments_dir = MAIL_DATA_DIR / "attachments" / filename.replace(".eml", "")
        attachments_dir.mkdir(parents=True, exist_ok=True)
        attachments_saved: list[tuple[str, str, Path, int]] = []

        try:
            msg = BytesParser(policy=policy.default).parsebytes(mail_bytes)
            for part in msg.walk():
                if part.is_multipart():
                    continue

                filename_hdr = part.get_filename()
                content_disposition = part.get_content_disposition()
                if not filename_hdr and content_disposition != "attachment":
                    continue

                raw_fname = filename_hdr or f"attachment_{int(time.time())}_{uuid.uuid4().hex[:8]}"
                fname = sanitize_filename(raw_fname)
                att_path = unique_path(attachments_dir, fname)
                payload = part.get_payload(decode=True) or b""

                try:
                    with att_path.open("wb") as out_f:
                        out_f.write(payload)
                    size_written = att_path.stat().st_size
                    attachments_saved.append(
                        (
                            fname,
                            part.get_content_type() or "application/octet-stream",
                            att_path,
                            size_written,
                        )
                    )
                except OSError:
                    if att_path.exists():
                        try:
                            att_path.unlink(missing_ok=True)
                        except Exception:
                            pass
        except Exception:
            attachments_saved = []

        # insert email rows and attachments metadata
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            for receiver in receivers:
                cur.execute(
                    """
                    INSERT INTO emails (sender, receiver, timestamp, file_path)
                    VALUES (?, ?, ?, ?)
                    """,
                    (sender, receiver, timestamp, relative_path),
                )
                email_id = cur.lastrowid
                for fname, mime_type, att_path, size in attachments_saved:
                    try:
                        att_rel = att_path.relative_to(BASE_DIR).as_posix()
                    except Exception:
                        att_rel = str(att_path)
                    cur.execute(
                        """
                        INSERT INTO attachments (email_id, filename, mime_type, file_path, size)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (email_id, fname, mime_type, att_rel, size),
                    )

        recv_list_str = ", ".join(receivers) if receivers else "(no recipients)"
        print(
            f"Saved message from {sender} to {recv_list_str} as {relative_path}",
            flush=True,
        )
        if attachments_saved:
            saved_names = ", ".join(a[0] for a in attachments_saved)
            print(f"Extracted attachments: {saved_names}", flush=True)
        return "250 Message accepted for delivery"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local SMTP mail server.")
    parser.add_argument("--host", default="127.0.0.1", help="SMTP bind address")
    parser.add_argument("--port", default=8025, type=int, help="SMTP bind port")
    parser.add_argument(
        "--ssl",
        action="store_true",
        help="Enable implicit SSL/TLS for SMTP connections",
    )
    parser.add_argument(
        "--no-auth-require-tls",
        action="store_true",
        help="Allow AUTH over unencrypted connections (insecure)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    init_database()

    ssl_context = create_server_ssl_context() if args.ssl else None

    def auth_callback(mechanism: str, login: bytes, password: bytes) -> bool:
        try:
            username = login.decode("utf-8", errors="ignore")
        except Exception:
            username = str(login)
        # Accept either 'user' or 'user@domain' by taking local part
        if "@" in username:
            username = username.split("@", 1)[0]
        try:
            pwd = password.decode("utf-8", errors="ignore")
        except Exception:
            pwd = str(password)

        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute(
                "SELECT 1 FROM users WHERE username = ? AND password = ?",
                (username, pwd),
            ).fetchone()
        return row is not None

    # By default the SMTP implementation requires TLS for AUTH; allow disabling with flag
    auth_require_tls = not args.no_auth_require_tls

    controller = Controller(
        MailStoreHandler(),
        hostname=args.host,
        port=args.port,
        ssl_context=ssl_context,
        auth_callback=auth_callback,
        auth_require_tls=auth_require_tls,
        auth_exclude_mechanism=[],
    )
    controller.start()
    protocol = "SMTPS" if args.ssl else "SMTP"
    print(f"{protocol} server listening on {args.host}:{args.port}", flush=True)
    if args.ssl:
        print(f"Using certificate: {CERT_PATH}", flush=True)
        print(f"Using private key: {KEY_PATH}", flush=True)
    if auth_require_tls:
        print("AUTH: TLS required for authentication", flush=True)
    else:
        print("AUTH: Allowing authentication over plaintext (insecure)", flush=True)
    print("Press Ctrl+C to stop.", flush=True)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping SMTP server...", flush=True)
    finally:
        controller.stop()


if __name__ == "__main__":
    main()
