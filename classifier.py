import math
import json
from collections import Counter
from pathlib import Path

from tokenizer import tokenize


class NaiveBayesClassifier:
    """朴素贝叶斯垃圾邮件分类器"""

    def __init__(self) -> None:
        self.spam_freq = Counter()
        self.ham_freq = Counter()
        self.spam_count = 0
        self.ham_count = 0

    def train(self, spam_texts, ham_texts) -> None:
        """根据垃圾邮件和正常邮件语料训练分类器。"""
        for text in spam_texts:
            words = tokenize(text)
            self.spam_freq.update(words)
            self.spam_count += 1

        for text in ham_texts:
            words = tokenize(text)
            self.ham_freq.update(words)
            self.ham_count += 1

    def predict(self, text: str) -> tuple[str, float]:
        if self.spam_count <= 0 or self.ham_count <= 0:
            raise ValueError("classifier must be trained with both spam and ham samples")

        words = tokenize(text)
        prior_log_ratio = math.log(self.spam_count / self.ham_count)

        alpha = 1
        vocab_size = len(set(self.spam_freq) | set(self.ham_freq))
        if vocab_size == 0:
            raise ValueError("classifier vocabulary is empty")

        spam_total = sum(self.spam_freq.values())
        ham_total = sum(self.ham_freq.values())

        likelihood_log_sum = 0.0
        for word in words:
            p_w_given_spam = (self.spam_freq[word] + alpha) / (
                spam_total + alpha * vocab_size
            )
            p_w_given_ham = (self.ham_freq[word] + alpha) / (
                ham_total + alpha * vocab_size
            )
            likelihood_log_sum += math.log(p_w_given_spam / p_w_given_ham)

        score = prior_log_ratio + likelihood_log_sum
        label = "spam" if score > 0 else "ham"
        return label, score

    def save(self, path) -> None:
        model = {
            "spam_freq": dict(self.spam_freq),
            "ham_freq": dict(self.ham_freq),
            "spam_count": self.spam_count,
            "ham_count": self.ham_count,
        }
        Path(path).write_text(
            json.dumps(model, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load(self, path) -> None:
        text = Path(path).read_text(encoding="utf-8")
        model = json.loads(text)
        self.spam_freq = Counter(model["spam_freq"])
        self.ham_freq = Counter(model["ham_freq"])
        self.spam_count = model["spam_count"]
        self.ham_count = model["ham_count"]
