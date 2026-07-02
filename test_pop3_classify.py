"""测试 POP3 + 分类：分别用 'alice' 和 'alice+spam' 登录，看到不同邮件"""
import poplib
import argparse

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read test mail from the POP3 server.")
    parser.add_argument("--host", default="127.0.0.1", help="POP3 server address")
    parser.add_argument("--port", default=8110, type=int, help="POP3 server port")
    parser.add_argument("--username", default="alice", help="POP3 username")
    parser.add_argument("--password", default="alice123", help="POP3 password")
    return parser.parse_args()

def fetch_mailbox(host: str,port: int, login_name: str, password: str, tag: str) -> None:
    print(f"\n=== 用 [{login_name}] 登录（{tag}）===")
    
    pop = poplib.POP3(host, port, timeout=10)
    pop.user(login_name)
    pop.pass_(password)
    
    num_msgs, total_size = pop.stat()
    print(f"邮箱里有 {num_msgs} 封邮件，共 {total_size} 字节")
    
   # 用 LIST 命令列出每封邮件的编号和大小
    if num_msgs > 0:
        resp, items, octets = pop.list()
        print(f"  LIST 命令返回：{resp.decode('utf-8', errors='ignore')}")
        for item in items:
            print(f"    {item.decode('utf-8', errors='ignore')}")
    
    pop.quit()


def main() -> None:
    args = parse_args()

    # 模式 1：正常收件箱——只看到 is_spam=0
    fetch_mailbox(args.host,args.port,args.username, args.password, "正常收件箱模式")
    
    # 模式 2：垃圾箱模式——只看到 is_spam=1
    fetch_mailbox(args.host,args.port,args.username+"+spam", args.password, "垃圾箱模式")


if __name__ == "__main__":
    main()