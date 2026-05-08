from __future__ import annotations

import argparse
import os
import time
import poplib
from pathlib import Path
from email import policy
from email.parser import BytesParser

from tls_config import create_test_client_ssl_context


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read test mail from the POP3 server.")
    parser.add_argument("--host", default="127.0.0.1", help="POP3 server address")
    parser.add_argument("--port", default=8110, type=int, help="POP3 server port")
    parser.add_argument("--username", default="alice", help="POP3 username")
    parser.add_argument("--password", default="alice123", help="POP3 password")
    parser.add_argument("--message", default=1, type=int, help="Message number to retrieve")
    parser.add_argument("--ssl", action="store_true", help="Use implicit SSL/TLS to connect to the POP3 server")
    parser.add_argument("--save-dir", default="downloaded_emails", help="Directory to save retrieved .eml files")
    parser.add_argument("--parse", action="store_true", help="Parse and display MIME structure and attachments")
    return parser.parse_args()


def save_message_lines_as_eml(lines: list[bytes], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("wb") as fh:
        fh.write(b"\r\n".join(lines) + b"\r\n")


def parse_mime_email(eml_path: Path) -> None:
    """解析 .eml 文件并显示 MIME 结构与附件"""
    try:
        msg = BytesParser(policy=policy.default).parsebytes(eml_path.read_bytes())
        
        print("\n=== MIME 结构分析 ===")
        print(f"邮件类型: {msg.get_content_type()}")
        print(f"发件人: {msg.get('From', 'N/A')}")
        print(f"收件人: {msg.get('To', 'N/A')}")
        print(f"主题: {msg.get('Subject', 'N/A')}")
        print(f"时间: {msg.get('Date', 'N/A')}")
        
        print("\n邮件部分:")
        part_index = 0
        for part in msg.walk():
            if part.is_multipart():
                print(f"  [{part_index}] 容器: {part.get_content_type()}")
            else:
                content_type = part.get_content_type()
                filename = part.get_filename()
                disposition = part.get_content_disposition()
                
                if filename:
                    size = len(part.get_payload(decode=True) or b"")
                    print(f"  [{part_index}] 附件: {filename}")
                    print(f"        类型: {content_type}, 大小: {size} 字节")
                else:
                    print(f"  [{part_index}] 正文: {content_type}")
                    if content_type in ("text/plain", "text/html"):
                        payload = part.get_payload(decode=True)
                        if payload:
                            text = payload.decode("utf-8", errors="replace")
                            preview = text[:100].replace("\n", " ")
                            print(f"        预览: {preview}...")
            part_index += 1
        
        print("\n=== 附件列表 ===")
        attachments = []
        for part in msg.walk():
            if not part.is_multipart() and part.get_content_disposition() == "attachment":
                filename = part.get_filename()
                content_type = part.get_content_type()
                size = len(part.get_payload(decode=True) or b"")
                attachments.append((filename, content_type, size))
                print(f"  • {filename} ({content_type}, {size} 字节)")
        
        if not attachments:
            print("  (无附件)")
        
    except Exception as e:
        print(f"MIME 解析失败: {e}")


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

        if message_count:
            response, lines, octets = pop3.retr(args.message)
            print(response.decode("utf-8", errors="replace"))
            print(f"RETR: received {len(lines)} lines, {octets} octets")

            timestamp = int(time.time())
            filename = f"{args.username}_{args.message}_{timestamp}.eml"
            out_path = Path(args.save_dir) / filename
            save_message_lines_as_eml(lines, out_path)
            print(f"Saved message to {out_path}")
            
            if args.parse:
                parse_mime_email(out_path)

        print(pop3.quit().decode("utf-8", errors="replace"))
    finally:
        try:
            pop3.close()
        except OSError:
            pass


if __name__ == "__main__":
    main()
