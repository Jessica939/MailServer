from __future__ import annotations

import argparse
import os
import time
import poplib
from pathlib import Path
from email.parser import BytesParser
from email.policy import default
from email.header import decode_header

from tls_config import create_test_client_ssl_context

def parse_mime_email(raw_email: bytes, save_dir: Path, msg_num: int, username: str):
    """
    解析 MIME 邮件，提取正文和附件，并保存附件到磁盘。
    同时返回邮件的基本信息供打印。
    """
    parser = BytesParser(policy=default)
    msg = parser.parsebytes(raw_email)

    # 提取常见头字段
    subject_raw = msg.get('Subject', '')
    subject = decode_header_str(subject_raw)
    from_ = decode_header_str(msg.get('From', '未知发件人'))
    to = decode_header_str(msg.get('To', ''))
    date = msg.get('Date', '')

    # 正文（优先纯文本，否则取第一个 html）
    body_text = ""
    attachments = []

    if msg.is_multipart():
        for part in msg.walk():
            content_disposition = part.get("Content-Disposition", "")
            content_type = part.get_content_type()
            # 附件处理
            if "attachment" in content_disposition.lower():
                filename_raw = part.get_filename()
                if filename_raw:
                    filename = decode_header_str(filename_raw)
                else:
                    filename = f"unnamed_attachment_{len(attachments)+1}"
                payload = part.get_payload(decode=True)
                if payload:
                    # 保存附件
                    attach_path = save_dir / f"{msg_num:04d}_{filename}"
                    # 避免文件名冲突
                    counter = 1
                    while attach_path.exists():
                        stem = attach_path.stem
                        suffix = attach_path.suffix
                        attach_path = save_dir / f"{stem}_{counter}{suffix}"
                        counter += 1
                    attach_path.write_bytes(payload)
                    attachments.append(str(attach_path.name))
                continue
            # 正文处理：优先纯文本，若未找到纯文本则取 HTML（转换为文本简单显示）
            if content_type == "text/plain" and not body_text:
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or "utf-8"
                try:
                    body_text = payload.decode(charset, errors="replace")
                except LookupError:
                    body_text = payload.decode("utf-8", errors="replace")
            elif content_type == "text/html" and not body_text:
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or "utf-8"
                try:
                    html_text = payload.decode(charset, errors="replace")
                    # 简单去除 HTML 标签，仅用于显示预览
                    import re
                    body_text = re.sub(r'<[^>]+>', '', html_text)
                except LookupError:
                    body_text = "无法解码 HTML"
    else:
        # 非 multipart 邮件
        content_type = msg.get_content_type()
        payload = msg.get_payload(decode=True)
        charset = msg.get_content_charset() or "utf-8"
        try:
            body_text = payload.decode(charset, errors="replace")
        except LookupError:
            body_text = payload.decode("utf-8", errors="replace")
        if content_type == "text/html":
            import re
            body_text = re.sub(r'<[^>]+>', '', body_text)

    return {
        "subject": subject,
        "from": from_,
        "to": to,
        "date": date,
        "body": body_text.strip(),
        "attachments": attachments,
    }

def decode_header_str(header_value: str) -> str:
    """解码可能包含 RFC 2047/2231 编码的字符串"""
    if not header_value:
        return ""
    decoded_parts = decode_header(header_value)
    result_parts = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            try:
                charset = charset or "utf-8"
                part = part.decode(charset, errors="replace")
            except LookupError:
                part = part.decode("utf-8", errors="replace")
        result_parts.append(part)
    return " ".join(result_parts)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read test mail from the POP3 server.")
    parser.add_argument("--host", default="127.0.0.1", help="POP3 server address")
    parser.add_argument("--port", default=8110, type=int, help="POP3 server port")
    parser.add_argument("--username", default="alice", help="POP3 username")
    parser.add_argument("--password", default="alice123", help="POP3 password")
    parser.add_argument("--message", default=1, type=int, help="Message number to retrieve")
    parser.add_argument("--ssl", action="store_true", help="Use implicit SSL/TLS to connect to the POP3 server")
    parser.add_argument("--save-dir", default="downloaded_emails", help="Directory to save retrieved .eml files")
    return parser.parse_args()


def save_message_lines_as_eml(lines: list[bytes], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("wb") as fh:
        fh.write(b"\r\n".join(lines) + b"\r\n")


def main() -> None:
    args = parse_args()

    if args.ssl:
        ssl_context = create_test_client_ssl_context()
        pop3 = poplib.POP3_SSL(args.host, args.port, timeout=10, context=ssl_context)
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

        if message_count <= message_count :
            response, lines, octets = pop3.retr(args.message)
            print(response.decode("utf-8", errors="replace"))
            print(f"RETR: received {len(lines)} lines, {octets} octets")

            timestamp = int(time.time())
            eml_filename = f"{args.username}_{args.message}_{timestamp}.eml"
            out_path = Path(args.save_dir) / eml_filename
            save_message_lines_as_eml(lines, out_path)
            print(f"Saved raw email to {out_path}")

            # 解析 MIME 并提取附件
            raw_email = b"\r\n".join(lines)
            parsed_info = parse_mime_email(raw_email, Path(args.save_dir), args.message, args.username)
            print("\n--- MIME Parsed Info ---")
            print(f"Subject: {parsed_info['subject']}")
            print(f"From: {parsed_info['from']}")
            print(f"To: {parsed_info['to']}")
            print(f"Date: {parsed_info['date']}")
            print(f"Body preview: {parsed_info['body'][:200]}...")
            if parsed_info['attachments']:
                print(f"Attachments saved: {', '.join(parsed_info['attachments'])}")
            else:
                print("No attachments found.")
            print("-------------------------\n")
        else:
            print(f"No message {args.message} (only {message_count} messages)")


        print(pop3.quit().decode("utf-8", errors="replace"))
    finally:
        try:
            pop3.close()
        except OSError:
            pass


if __name__ == "__main__":
    main()
