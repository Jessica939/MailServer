from __future__ import annotations

import argparse
import poplib

from tls_config import create_test_client_ssl_context


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read test mail from the POP3 server.")
    parser.add_argument("--host", default="127.0.0.1", help="POP3 server address")
    parser.add_argument("--port", default=8110, type=int, help="POP3 server port")
    parser.add_argument("--username", default="alice", help="POP3 username")
    parser.add_argument("--password", default="alice123", help="POP3 password")
    parser.add_argument(
        "--message", default=1, type=int, help="Message number to retrieve"
    )
    parser.add_argument(
        "--ssl",
        action="store_true",
        help="Use implicit SSL/TLS to connect to the POP3 server",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.ssl:
        ssl_context = create_test_client_ssl_context()
        pop3 = poplib.POP3_SSL(
            args.host,
            args.port,
            timeout=10,
            context=ssl_context,
        )
    else:
        pop3 = poplib.POP3(args.host, args.port, timeout=10)
    try:
        print(pop3.getwelcome().decode("utf-8", errors="replace"))
        print(pop3.user(args.username).decode("utf-8", errors="replace"))
        print(pop3.pass_(args.password).decode("utf-8", errors="replace"))

        message_count, total_size = pop3.stat()
        print(f"STAT: {message_count} messages, {total_size} octets")

        response, listings, octets = pop3.list()
        print(response.decode("utf-8", errors="replace"))
        for listing in listings:
            print("LIST:", listing.decode("utf-8", errors="replace"))

        if message_count:
            response, lines, octets = pop3.retr(args.message)
            print(response.decode("utf-8", errors="replace"))
            print(f"RETR: received {len(lines)} lines, {octets} octets")

        print(pop3.quit().decode("utf-8", errors="replace"))
    finally:
        try:
            pop3.close()
        except OSError:
            pass


if __name__ == "__main__":
    main()
