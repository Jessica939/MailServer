
from pathlib import Path
from classifier import NaiveBayesClassifier


def main():
    model_path = Path(__file__).parent / "bayes_model.json"

    nbc = NaiveBayesClassifier()
    nbc.load(model_path)
    print(f"已从 {model_path.name} 加载模型")
    print(f"spam 邮件数：{nbc.spam_count}，ham 邮件数：{nbc.ham_count}")
    
    test_emails = [
        "恭喜您中奖了！请点击链接领取奖金。",
        "小王，下午三点会议室见，记得带笔记本。",
        "限时秒杀，加微信抢购，错过等一年！",
        "妈，我下周回家，您不用接我。",
        "您好，附件是合同初稿，请查收。",
    ]
    
    print("\n=== predict 测试 ===")
    for email in test_emails:
        label, score = nbc.predict(email)
        print(f"[{label:4}] (score={score:+.2f})  {email}")


if __name__ == "__main__":
    main()