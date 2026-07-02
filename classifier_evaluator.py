"""评估贝叶斯分类器"""

import random
from pathlib import Path
from classifier import NaiveBayesClassifier


# === 配置 ===
CORPUS_DIR = Path(__file__).parent / "corpus"
TEST_RATIO = 0.2         # 测试集占比 20%
RANDOM_SEED = 42         # 固定随机种子
# ============


def load_and_split(corpus_dir: Path, test_ratio: float, seed: int):
    """从 corpus_dir 加载所有邮件，按 test_ratio 随机拆分 train/test
    
    返回 (train_spam, train_ham, test_spam, test_ham)——每个都是 list[str]
    """
    rng = random.Random(seed)
    
    spam_paths = list((corpus_dir / "spam").glob("*.txt"))
    ham_paths = list((corpus_dir / "ham").glob("*.txt"))

    if not spam_paths or not ham_paths:
        raise SystemExit("语料不足：需要 corpus/spam 和 corpus/ham 下都包含 .txt 文件")

    rng.shuffle(spam_paths)
    rng.shuffle(ham_paths)
    
    spam_split = int(len(spam_paths) * (1 - test_ratio))
    ham_split  = int(len(ham_paths)  * (1 - test_ratio))
    
    train_spam = [p.read_text(encoding="utf-8") for p in spam_paths[:spam_split]]
    test_spam  = [p.read_text(encoding="utf-8") for p in spam_paths[spam_split:]]
    train_ham  = [p.read_text(encoding="utf-8") for p in ham_paths[:ham_split]]
    test_ham   = [p.read_text(encoding="utf-8") for p in ham_paths[ham_split:]]
    
    return train_spam, train_ham, test_spam, test_ham

def evaluate(classifier, test_spam, test_ham, threshold=0.0):
    """预测测试集，返回 (tp, tn, fp, fn) + 错误样本"""
    tp = tn = fp = fn = 0
    errors = []   # 收集错误样本：(true_label, pred_label, score, text)
    
    # 测试 spam：真实 = spam
    for text in test_spam:
        _, score = classifier.predict(text)
        pred_is_spam = score > threshold
        if pred_is_spam:
            tp += 1
        else:
            fn += 1
            errors.append(("spam", "ham", score, text))
    
    # 测试 ham：真实 = ham
    for text in test_ham:
        _, score = classifier.predict(text)
        pred_is_spam = score > threshold
        if pred_is_spam:
            fp += 1
            errors.append(("ham", "spam", score, text))
        else:
            tn += 1
    
    return tp, tn, fp, fn, errors


def print_metrics(tp, tn, fp, fn, threshold):
    """打印 4 个指标 + 混淆矩阵"""
    total = tp + tn + fp + fn
    accuracy  = (tp + tn) / total if total else 0
    precision = tp / (tp + fp) if (tp + fp) else 0
    recall    = tp / (tp + fn) if (tp + fn) else 0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) else 0
    
    print(f"\n=== 阈值 = {threshold:+.1f} ===")
    print(f"混淆矩阵：")
    print(f"              预测 spam   预测 ham")
    print(f"真实 spam  │   {tp:>6}   │   {fn:>6}   │")
    print(f"真实 ham   │   {fp:>6}   │   {tn:>6}   │")
    print()
    print(f"Accuracy:  {accuracy:.4f}  ({tp+tn}/{total} 判对)")
    print(f"Precision: {precision:.4f}  ")
    print(f"Recall:    {recall:.4f}  ")
    print(f"F1:        {f1:.4f}")

def show_errors(errors, max_show=5):
    """展示一些错误样本"""
    if not errors:
        print("\n  没有错误样本！")
        return

    sorted_errors = sorted(errors, key=lambda x: abs(x[2]), reverse=True)
    
    print(f"\n=== 最严重的 {min(max_show, len(errors))} 个错误样本 ===")
    for i, (true_label, pred_label, score, text) in enumerate(sorted_errors[:max_show], 1):
        preview = text.replace("\n", " ")[:100]
        print(f"\n错误 {i}: 真实={true_label}，预测={pred_label}，score={score:+.2f}")
        print(f"  正文前 100 字: {preview}...")


def main():
    print(f"加载语料：{CORPUS_DIR}")
    train_spam, train_ham, test_spam, test_ham = load_and_split(
        CORPUS_DIR, TEST_RATIO, RANDOM_SEED
    )
    print(f"训练集：{len(train_spam)} spam + {len(train_ham)} ham = {len(train_spam) + len(train_ham)} 封")
    print(f"测试集：{len(test_spam)} spam + {len(test_ham)} ham = {len(test_spam) + len(test_ham)} 封")
    
    print("\n开始训练...")
    nbc = NaiveBayesClassifier()
    nbc.train(train_spam, train_ham)
    print(f"训练完成。词表：spam={len(nbc.spam_freq)}, ham={len(nbc.ham_freq)}")

    tp, tn, fp, fn, errors = evaluate(nbc, test_spam, test_ham, threshold=0.0)
    print_metrics(tp, tn, fp, fn, threshold=0.0)
    
    show_errors(errors, max_show=5)

if __name__ == "__main__":
    main()
