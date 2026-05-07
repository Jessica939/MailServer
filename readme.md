MailServer — 教学用简易邮件服务器与客户端

概要
本仓库实现了一个用于教学的邮件系统原型，包含：
- SMTP 服务端（接收并保存邮件为 .eml）
- POP3 服务端（提供 mailbox 列表与检索）
- 简易客户端脚本（发送/接收测试用）
- MIME 附件支持与 TLS（测试用 self-signed 证书）

主要文件
- [init_db.py](init_db.py) — 初始化数据库与测试用户（admin / alice / bob）
- [smtp_server.py](smtp_server.py) — SMTP 服务端（使用 aiosmtpd），保存邮件到 `mail_data/` 并记录到 SQLite
- [pop3_server.py](pop3_server.py) — 简易 POP3 服务端（可选隐式 SSL）
- [tls_config.py](tls_config.py) — 创建服务器/客户端测试用 SSLContext（使用 `cert.pem` / `key.pem`）
- [test_smtp_client.py](test_smtp_client.py) — SMTP 测试客户端（支持 HTML、附件、STARTTLS/SSL、登录）
- [test_pop3_client.py](test_pop3_client.py) — POP3 测试客户端（支持保存为 `.eml`）

更新 / 功能补充（要点）
- 在 `smtp_server.py` 中添加了基于 SQLite 的 `AUTH` 校验回调，支持 `AUTH PLAIN` 与 `AUTH LOGIN`，并可通过命令行参数控制是否强制在 TLS 后允许 AUTH（默认要求 TLS）。
- 增强 `test_smtp_client.py`：支持 `--html` 添加 HTML 替代体、`--attach` 添加附件（逗号分隔）、`--starttls` 启用 STARTTLS、`--ssl` 隐式 SSL、`--username/--password` 登录并发送邮件。
- 增强 `test_pop3_client.py`：在检索后将邮件原始行保存为 `.eml` 文件（可通过 `--save-dir` 指定目录），仍支持隐式 SSL。

快速使用示例
- 初始化数据库（会在 `mail_server.db` 中创建测试用户）：
```
python3 init_db.py
```
- 启动 SMTP 服务（默认要求 TLS 才允许 AUTH）：
```
python3 smtp_server.py --host 127.0.0.1 --port 8025
```
隐式 SSL（SMTPS）：
```
python3 smtp_server.py --ssl
```
允许在明文连接上使用 AUTH（不建议，仅用于测试）：
```
python3 smtp_server.py --no-auth-require-tls
```
- 使用测试 SMTP 客户端发送邮件（使用 STARTTLS 并登录）：
```
python3 test_smtp_client.py --host 127.0.0.1 --port 8025 --starttls --username alice --password alice123 --attach /path/to/file.pdf --html
```
- 使用测试 POP3 客户端下载并保存第 1 封邮件：
```
python3 test_pop3_client.py --host 127.0.0.1 --port 8110 --username alice --password alice123 --message 1 --save-dir downloaded_emails
```
