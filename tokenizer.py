import jieba
import re
from pathlib import Path


STOPWORDS = set()
stopwords_file = Path(__file__).parent / "stopwords_zh.txt"
if stopwords_file.exists():
    text = stopwords_file.read_text(encoding="utf-8")
    for line in text.splitlines():
        word = line.strip()
        if word:
            STOPWORDS.add(word)


def tokenize(text: str) -> list[str]:
    text = re.sub(r"http\S+", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[^\u4e00-\u9fa5a-zA-Z]", " ", text)

    words = jieba.cut(text)

    result = []
    for word in words:
        word = word.strip()
        if not word:
            continue
        if word in STOPWORDS:
            continue
        if word.isdigit():
            continue
        result.append(word)

    return result
