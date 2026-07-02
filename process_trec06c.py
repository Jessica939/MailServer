import email
from email import policy
from pathlib import Path

from bs4 import BeautifulSoup


BASE_DIR = Path(__file__).resolve().parent
TREC06C_DIR = BASE_DIR / "trec06c"
OUTPUT_ROOT = BASE_DIR / "corpus"
MAX_EMAILS = None


def safe_decode(raw_bytes: bytes, charset_hint: str | None = None) -> str:
    for codec in [charset_hint, "gb18030", "gb2312", "utf-8", "latin-1"]:
        if not codec:
            continue
        try:
            return raw_bytes.decode(codec)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw_bytes.decode("utf-8", errors="ignore")


def extract_body(msg) -> str:
    body_parts: list[str] = []

    parts = msg.walk() if msg.is_multipart() else [msg]
    for part in parts:
        if part.is_multipart():
            continue
        content_type = part.get_content_type()
        if content_type not in ("text/plain", "text/html"):
            continue

        payload = part.get_payload(decode=True) or b" "
        text = safe_decode(payload, part.get_content_charset())
        if content_type == "text/html":
            text = BeautifulSoup(text, "html.parser").get_text(separator=" ")
        body_parts.append(text)

    return "\n".join(body_parts).strip()


def main() -> None:
    index_file = TREC06C_DIR / "full" / "index"
    if not index_file.exists():
        print(f"找不到 index 文件：{index_file}")
        print("请确认 trec06c 数据集已解压到项目目录，或修改 TREC06C_DIR")
        return

    spam_out = OUTPUT_ROOT / "spam"
    ham_out = OUTPUT_ROOT / "ham"
    spam_out.mkdir(parents=True, exist_ok=True)
    ham_out.mkdir(parents=True, exist_ok=True)

    print(f"读取索引：{index_file}")
    lines = index_file.read_text(encoding="utf-8").splitlines()
    print(f"索引共 {len(lines)} 行")

    spam_count = 0
    ham_count = 0
    skip_count = 0
    fail_count = 0

    for i, line in enumerate(lines):
        if MAX_EMAILS is not None and (spam_count + ham_count) >= MAX_EMAILS:
            break

        parts = line.strip().split()
        if len(parts) < 2:
            continue
        label, rel_path = parts[0], parts[1]

        email_path = (index_file.parent / rel_path).resolve()
        if not email_path.exists():
            skip_count += 1
            if skip_count <= 10:
                print(f"  跳过(文件不存在)：{email_path.name}")
            continue

        try:
            with email_path.open("rb") as file:
                msg = email.message_from_binary_file(file, policy=policy.compat32)
            body = extract_body(msg)

            if not body or len(body) < 10:
                skip_count += 1
                if skip_count <= 10:
                    print(f"  跳过(空邮件或正文太短)：{email_path.name}")
                continue

            if label == "spam":
                out_path = spam_out / f"spam_{spam_count:06d}.txt"
                out_path.write_text(body, encoding="utf-8")
                spam_count += 1
            elif label == "ham":
                out_path = ham_out / f"ham_{ham_count:06d}.txt"
                out_path.write_text(body, encoding="utf-8")
                ham_count += 1
        except Exception as exc:
            fail_count += 1
            if fail_count <= 10:
                print(f"  失败：{email_path.name}（{exc}）")
            continue

        if (i + 1) % 5000 == 0:
            print(
                f"  已处理 {i + 1} / {len(lines)}"
                f"（spam: {spam_count}, ham: {ham_count}, 失败: {fail_count}）"
            )

    print("\n=== 处理完成 ===")
    print(f"spam: {spam_count} 封 -> {spam_out}")
    print(f"ham:  {ham_count} 封 -> {ham_out}")
    print(f"失败: {fail_count} 封")
    print(f"跳过: {skip_count} 封")


if __name__ == "__main__":
    main()
