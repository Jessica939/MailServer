from __future__ import annotations

import argparse
import smtplib
from email.message import EmailMessage

from tls_config import create_test_client_ssl_context


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send a test email to the SMTP server.")
    parser.add_argument("--host", default="127.0.0.1", help="SMTP server address")
    parser.add_argument("--port", default=8025, type=int, help="SMTP server port")
    parser.add_argument("--sender", default="admin@example.com", help="Envelope sender")
    parser.add_argument(
        "--receiver", default="alice@example.com", help="Envelope receiver"
    )
    parser.add_argument(
        "--ssl",
        action="store_true",
        help="Use implicit SSL/TLS to connect to the SMTP server",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    message = EmailMessage()
    message["From"] = args.sender
    message["To"] = args.receiver
    message["Subject"] = "Local SMTP test"
    message.set_content("Hello from the MailServer SMTP test client.")

    if args.ssl:
        ssl_context = create_test_client_ssl_context()
        smtp = smtplib.SMTP_SSL(args.host, args.port, context=ssl_context)
    else:
        smtp = smtplib.SMTP(args.host, args.port)

    with smtp:
        smtp.send_message(message)

    print(f"Sent test email from {args.sender} to {args.receiver}")


if __name__ == "__main__":
    main()
