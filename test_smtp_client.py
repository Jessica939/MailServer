from __future__ import annotations

import argparse
import mimetypes
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable

from email.utils import formatdate


from tls_config import create_test_client_ssl_context


def iter_attachment_paths(raw: str | None) -> Iterable[Path]:
    if not raw:
        return []
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return [Path(p) for p in parts]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send a test email to the SMTP server.")
    parser.add_argument("--host", default="127.0.0.1", help="SMTP server address")
    parser.add_argument("--port", default=8025, type=int, help="SMTP server port")
    parser.add_argument("--sender", default="admin@example.com", help="Envelope sender")
    parser.add_argument("--receiver", default="alice@example.com", help="Envelope receiver")
    parser.add_argument("--subject", default="Local SMTP test", help="Email subject")
    parser.add_argument("--body", default="Hello from the MailServer SMTP test client.", help="Plain text body")
    parser.add_argument("--html", action="store_true", help="Also include an HTML alternative body")
    parser.add_argument("--attach", help="Comma-separated list of file paths to attach")
    parser.add_argument("--ssl", action="store_true", help="Use implicit SSL/TLS to connect to the SMTP server")
    parser.add_argument("--starttls", action="store_true", help="Use STARTTLS before authentication/sending")
    parser.add_argument("--username", help="SMTP username for authentication")
    parser.add_argument("--password", help="SMTP password for authentication")
    return parser.parse_args()


def add_attachments(message: EmailMessage, paths: Iterable[Path]) -> None:
    for path in paths:
        if not path.exists():
            print(f"Warning: attachment not found: {path}")
            continue
        ctype, encoding = mimetypes.guess_type(str(path))
        if ctype is None:
            ctype = "application/octet-stream"
        maintype, subtype = ctype.split("/", 1)
        with path.open("rb") as fh:
            data = fh.read()
        message.add_attachment(data, maintype=maintype, subtype=subtype, filename=path.name)


def main() -> None:
    args = parse_args()

    message = EmailMessage()
    message["From"] = args.sender
    message["To"] = args.receiver
    message["Subject"] = args.subject
    message['Date'] = formatdate()
    message.set_content(args.body)
    if args.html:
        html_body = f"<html><body><p>{args.body}</p></body></html>"
        message.add_alternative(html_body, subtype="html")

    attachment_paths = list(iter_attachment_paths(args.attach))
    if attachment_paths:
        add_attachments(message, attachment_paths)

    if args.ssl:
        ssl_context = create_test_client_ssl_context()
        smtp = smtplib.SMTP_SSL(args.host, args.port, context=ssl_context, timeout=10)
        smtp.ehlo()  # Send EHLO after SSL connection
    else:
        smtp = smtplib.SMTP(args.host, args.port, timeout=10)

    with smtp:
        if not args.ssl:  # Only send initial EHLO for non-SSL connections
            smtp.ehlo()
        if args.starttls:
            ctx = create_test_client_ssl_context()
            smtp.starttls(context=ctx)
            smtp.ehlo()

        if args.username and args.password:
            try:
                smtp.login(args.username, args.password)
            except Exception as exc:  # pragma: no cover - network
                print(f"Login failed: {exc}")

        smtp.send_message(message)

    print(f"Sent email from {args.sender} to {args.receiver}")


if __name__ == "__main__":
    main()
