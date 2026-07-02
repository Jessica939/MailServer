from pathlib import Path
from classifier import NaiveBayesClassifier


def load_corpus(corpus_dir: Path) -> tuple[list[str], list[str]]:
    spam_texts = [
        p.read_text(encoding="utf-8") for p in (corpus_dir / "spam").glob("*.txt")
    ]
    ham_texts = [
        p.read_text(encoding="utf-8") for p in (corpus_dir / "ham").glob("*.txt")
    ]
    return spam_texts, ham_texts


def main() -> None:
    corpus_dir = Path(__file__).parent / "corpus"
    model_path = Path(__file__).parent / "bayes_model.json"

    print(f"扫描语料目录：{corpus_dir}")
    spam_texts, ham_texts = load_corpus(corpus_dir)
    print(f"语料中包含 {len(spam_texts)} 封垃圾邮件和 {len(ham_texts)} 封正常邮件")
    if not spam_texts or not ham_texts:
        raise SystemExit("语料不足：需要 corpus/spam 和 corpus/ham 下都包含 .txt 文件")

    print("开始训练...")
    nbc = NaiveBayesClassifier()
    nbc.train(spam_texts, ham_texts)
    print(f"训练完成。spam 词表 {len(nbc.spam_freq)} 词，ham 词表 {len(nbc.ham_freq)} 词")

    nbc.save(model_path)
    print(f"模型已保存到 {model_path}")


if __name__ == "__main__":
    main()
