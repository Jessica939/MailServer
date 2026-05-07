from __future__ import annotations

import argparse
import socket
import ssl
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path

from init_db import BASE_DIR, DB_PATH, init_database
from tls_config import CERT_PATH, KEY_PATH, create_server_ssl_context


CRLF = b"\r\n"
MAX_COMMAND_LENGTH = 1024


@dataclass(frozen=True)
class MailItem:
    email_id: int
    file_path: str
    absolute_path: Path
    size: int


class POP3Session:
    def __init__(
        self,
        connection: socket.socket,
        address: tuple[str, int],
        ssl_context: ssl.SSLContext | None = None,
    ) -> None:
        self.connection = connection
        self.address = address
        self.ssl_context = ssl_context
        self.stream = None
        self.pending_user: str | None = None
        self.username: str | None = None
        self.running = True

    def run(self) -> None:
        print(f"POP3 client connected: {self.address}", flush=True)
        try:
            if self.ssl_context is not None:
                self.connection = self.ssl_context.wrap_socket(
                    self.connection,
                    server_side=True,
                )
            self.stream = self.connection.makefile("rwb", buffering=0)
            self.send_line("+OK POP3 server ready")
            while self.running:
                raw_line = self.stream.readline(MAX_COMMAND_LENGTH + 1)
                if not raw_line:
                    break
                if len(raw_line) > MAX_COMMAND_LENGTH:
                    self.send_line("-ERR command line too long")
                    continue

                line = raw_line.decode("utf-8", errors="replace").strip("\r\n")
                if not line:
                    self.send_line("-ERR empty command")
                    continue

                command, argument = self.parse_command(line)
                self.handle_command(command, argument)
        except (ConnectionError, ssl.SSLError):
            pass
        finally:
            if self.stream is not None:
                try:
                    self.stream.close()
                except OSError:
                    pass
            self.connection.close()
            print(f"POP3 client disconnected: {self.address}", flush=True)

    def parse_command(self, line: str) -> tuple[str, str]:
        parts = line.split(maxsplit=1)
        command = parts[0].upper()
        argument = parts[1].strip() if len(parts) > 1 else ""
        return command, argument

    def handle_command(self, command: str, argument: str) -> None:
        if command == "QUIT":
            self.send_line("+OK POP3 server signing off")
            self.running = False
            return

        if command == "USER":
            self.handle_user(argument)
            return

        if command == "PASS":
            self.handle_pass(argument)
            return

        if not self.is_authenticated:
            self.send_line("-ERR please login with USER and PASS")
            return

        if command == "STAT":
            self.handle_stat()
        elif command == "LIST":
            self.handle_list(argument)
        elif command == "RETR":
            self.handle_retr(argument)
        elif command == "NOOP":
            self.send_line("+OK")
        else:
            self.send_line("-ERR unknown command")

    @property
    def is_authenticated(self) -> bool:
        return self.username is not None

    def handle_user(self, username: str) -> None:
        username = normalize_username(username)
        if not username:
            self.send_line("-ERR missing username")
            return

        if user_exists(username):
            self.pending_user = username
            self.username = None
            self.send_line("+OK user accepted")
        else:
            self.pending_user = None
            self.username = None
            self.send_line("-ERR no such user")

    def handle_pass(self, password: str) -> None:
        if self.pending_user is None:
            self.send_line("-ERR send USER first")
            return

        if verify_user(self.pending_user, password):
            self.username = self.pending_user
            self.pending_user = None
            self.send_line("+OK maildrop locked and ready")
        else:
            self.username = None
            self.send_line("-ERR invalid password")

    def handle_stat(self) -> None:
        mailbox = self.load_mailbox()
        total_size = sum(item.size for item in mailbox)
        self.send_line(f"+OK {len(mailbox)} {total_size}")

    def handle_list(self, argument: str) -> None:
        mailbox = self.load_mailbox()

        if argument:
            message_number = parse_message_number(argument)
            item = get_mail_item(mailbox, message_number)
            if item is None:
                self.send_line("-ERR no such message")
                return
            self.send_line(f"+OK {message_number} {item.size}")
            return

        total_size = sum(item.size for item in mailbox)
        self.send_line(f"+OK {len(mailbox)} messages ({total_size} octets)")
        for message_number, item in enumerate(mailbox, start=1):
            self.write_bytes(f"{message_number} {item.size}".encode("ascii") + CRLF)
        self.write_bytes(b"." + CRLF)

    def handle_retr(self, argument: str) -> None:
        message_number = parse_message_number(argument)
        item = get_mail_item(self.load_mailbox(), message_number)
        if item is None:
            self.send_line("-ERR no such message")
            return

        try:
            mail_bytes = item.absolute_path.read_bytes()
        except OSError:
            self.send_line("-ERR message file not available")
            return

        self.send_line(f"+OK {item.size} octets")
        self.send_multiline_payload(mail_bytes)

    def load_mailbox(self) -> list[MailItem]:
        if self.username is None:
            return []
        return load_mailbox(self.username)

    def send_line(self, line: str) -> None:
        self.write_bytes(line.encode("utf-8") + CRLF)

    def send_multiline_payload(self, payload: bytes) -> None:
        for line in payload.splitlines():
            if line.startswith(b"."):
                line = b"." + line
            self.write_bytes(line + CRLF)
        self.write_bytes(b"." + CRLF)

    def write_bytes(self, data: bytes) -> None:
        self.stream.write(data)


class POP3Server:
    def __init__(self, host: str, port: int, use_ssl: bool = False) -> None:
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.ssl_context = create_server_ssl_context() if use_ssl else None
        self.should_stop = threading.Event()
        self.threads: list[threading.Thread] = []

    def serve_forever(self) -> None:
        init_database()

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((self.host, self.port))
            server_socket.listen()
            server_socket.settimeout(1.0)

            protocol = "POP3S" if self.use_ssl else "POP3"
            print(f"{protocol} server listening on {self.host}:{self.port}", flush=True)
            if self.use_ssl:
                print(f"Using certificate: {CERT_PATH}", flush=True)
                print(f"Using private key: {KEY_PATH}", flush=True)
            print("Press Ctrl+C to stop.", flush=True)

            while not self.should_stop.is_set():
                try:
                    connection, address = server_socket.accept()
                except socket.timeout:
                    continue

                thread = threading.Thread(
                    target=POP3Session(connection, address, self.ssl_context).run,
                    name=f"POP3Client-{address[0]}:{address[1]}",
                    daemon=True,
                )
                thread.start()
                self.threads.append(thread)

    def stop(self) -> None:
        self.should_stop.set()


def normalize_username(raw_username: str) -> str:
    username = raw_username.strip()
    if "@" in username:
        username = username.split("@", 1)[0]
    return username


def user_exists(username: str) -> bool:
    username = normalize_username(username)
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT 1 FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    return row is not None


def verify_user(username: str, password: str) -> bool:
    username = normalize_username(username)
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT 1
            FROM users
            WHERE username = ? AND password = ?
            """,
            (username, password),
        ).fetchone()
    return row is not None


def load_mailbox(username: str) -> list[MailItem]:
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT id, file_path
            FROM emails
            WHERE lower(receiver) = lower(?)
               OR (
                    instr(receiver, '@') > 1
                    AND lower(substr(receiver, 1, instr(receiver, '@') - 1)) = lower(?)
               )
            ORDER BY id
            """,
            (username, username),
        ).fetchall()

    mailbox: list[MailItem] = []
    for email_id, file_path in rows:
        absolute_path = resolve_mail_path(file_path)
        try:
            size = absolute_path.stat().st_size
        except OSError:
            size = 0
        mailbox.append(
            MailItem(
                email_id=email_id,
                file_path=file_path,
                absolute_path=absolute_path,
                size=size,
            )
        )
    return mailbox


def resolve_mail_path(file_path: str) -> Path:
    path = Path(file_path)
    if path.is_absolute():
        return path
    return BASE_DIR / path


def parse_message_number(argument: str) -> int | None:
    try:
        message_number = int(argument)
    except (TypeError, ValueError):
        return None
    if message_number < 1:
        return None
    return message_number


def get_mail_item(mailbox: list[MailItem], message_number: int | None) -> MailItem | None:
    if message_number is None or message_number > len(mailbox):
        return None
    return mailbox[message_number - 1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local POP3 mail server.")
    parser.add_argument("--host", default="127.0.0.1", help="POP3 bind address")
    parser.add_argument("--port", default=8110, type=int, help="POP3 bind port")
    parser.add_argument(
        "--ssl",
        action="store_true",
        help="Enable implicit SSL/TLS for POP3 connections",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    server = POP3Server(args.host, args.port, use_ssl=args.ssl)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping POP3 server...", flush=True)
        server.stop()


if __name__ == "__main__":
    main()
