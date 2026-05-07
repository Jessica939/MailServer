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


---



# MailServer 邮件系统功能测试报告

## 测试环境

- **操作系统**：Windows 11 / PowerShell
- **Python 版本**：3.12
- **项目目录**：`C:\Users\15040\Desktop\cnfinal_work\MailServer`
- **依赖**：`aiosmtpd==1.4.6`，其他使用 Python 标准库

## 测试组件

| 组件 | 文件 | 说明 |
|------|------|------|
| SMTP 服务端 | `smtp_server.py` | 基于 aiosmtpd，支持 SSL，支持 AUTH LOGIN/PLAIN，强制认证 |
| POP3 服务端 | `pop3_server.py` | 原生 socket 实现，支持 SSL，支持 USER/PASS |
| 测试客户端 | `test_smtp_client.py` | 支持 SSL/STARTTLS，附件，HTML，认证 |
| 测试客户端 | `test_pop3_client.py` | 支持 SSL，保存 .eml 文件 |
| 增强客户端 | `test_pop3_client.py`（添加 MIME 解析） | 解析邮件头、正文、附件并保存 |

## 测试前准备

1. **初始化数据库**
   ```bash
   python init_db.py
   ```
   创建 `mail_server.db`，含用户 `admin/123456`、`alice/alice123`、`bob/bob123`。

2. **准备自签名证书**（如已存在则跳过）
   ```bash
   openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/CN=localhost"
   ```

3. **清理旧数据（可选）**
   ```bash
   Remove-Item -Path mail_server.db -Force
   Remove-Item -Path mail_data -Recurse -Force
   ```

## 服务端启动

打开两个 PowerShell 终端：

**终端1 – SMTP（带 SSL）**
```bash
python smtp_server.py --host 127.0.0.1 --port 8025 --ssl
```
预期输出：
```
SMTPS server listening on 127.0.0.1:8025
Using certificate: ...\cert.pem
Using private key: ...\key.pem
AUTH: TLS required for authentication
Press Ctrl+C to stop.
```

**终端2 – POP3（明文，用于接收测试）**
```bash
python pop3_server.py --host 127.0.0.1 --port 8110
```
预期输出：
```
POP3 server listening on 127.0.0.1:8110
Press Ctrl+C to stop.
```

> 注：POP3 也可以使用 `--ssl` 测试加密接收。

## 功能测试清单

### 1. SMTP 发送 – 纯文本邮件

**命令**：
```bash
python test_smtp_client.py --host 127.0.0.1 --port 8025 --ssl --username alice --password alice123 --sender alice@example.com --receiver bob@example.com --subject "Plain Text" --body "Hello Bob, this is plain text."
```

**预期结果**：
- 客户端输出：`Sent email from alice@example.com to bob@example.com`
- 服务端日志：`Saved message from alice@example.com to bob@example.com as mail_data/xxx.eml`
- 数据库 `emails` 表新增记录，`mail_data/` 下生成 `.eml` 文件。

### 2. SMTP 发送 – HTML 邮件

**命令**：
```bash
python test_smtp_client.py --host 127.0.0.1 --port 8025 --ssl --username alice --password alice123 --sender alice@example.com --receiver bob@example.com --subject "HTML Email" --body "<h1>Hello</h1><p>This is <b>HTML</b></p>" --html
```

**预期结果**：同上，邮件中应包含 HTML 替代部分。

### 3. SMTP 发送 – 带附件

**准备测试文件**：在项目目录下创建 `test.txt`（内容任意）。

**命令**：
```bash
python test_smtp_client.py --host 127.0.0.1 --port 8025 --ssl --username alice --password alice123 --sender alice@example.com --receiver bob@example.com --subject "With Attachment" --body "See attached file" --attach test.txt
```

**预期结果**：
- 客户端发送成功。
- 服务端日志显示：`Extracted attachments: test.txt`
- 在 `mail_data/attachments/<邮件ID>/` 下保存 `test.txt` 文件。
- 数据库 `attachments` 表记录附件元数据。

### 4. POP3 接收 – 保存原始 .eml

**命令**：
```bash
python test_pop3_client.py --host 127.0.0.1 --port 8110 --username bob --password bob123 --message 1 --save-dir received_mails
```

**预期输出**：
```
+OK POP3 server ready
+OK user accepted
+OK maildrop locked and ready
STAT: 3 messages, 1234 octets
...
Saved message to received_mails\bob_1_1712345678.eml
+OK POP3 server signing off
```
在 `received_mails/` 目录下生成 `.eml` 文件。

### 5. POP3 接收 – 解析 MIME 并保存附件

使用添加了 MIME 解析功能的 `test_pop3_client.py`（已在代码中集成 `parse_mime_email` 函数）。

**命令**（同上）：
```bash
python test_pop3_client.py --host 127.0.0.1 --port 8110 --username bob --password bob123 --message 1 --save-dir mime_test
```

**预期输出**（额外部分）：
```
--- MIME Parsed Info ---
Subject: With Attachment
From: alice@example.com
To: bob@example.com
Body preview: See attached file...
Attachments saved: 0001_test.txt
-------------------------
```
附件文件被保存为 `mime_test/0001_test.txt`，原始 `.eml` 同时保存。

### 6. SSL 加密接收（POP3S）

**启动 POP3S 服务**（终端2）：
```bash
python pop3_server.py --host 127.0.0.1 --port 8110 --ssl
```

**客户端命令**：
```bash
python test_pop3_client.py --host 127.0.0.1 --port 8110 --ssl --username bob --password bob123 --message 1 --save-dir ssl_received
```

**预期**：成功连接并下载邮件，无 SSL 错误。

### 7. 用户认证失败测试（SMTP）（未完成）

**命令**（错误密码）：
```bash
python test_smtp_client.py --host 127.0.0.1 --port 8025 --ssl --username alice --password wrong --sender alice@example.com --receiver bob@example.com --subject "Fail" --body "Should fail"
```

**预期结果**：
- 客户端输出 `Login failed: Authentication failed`（或类似）。
- 服务端**不保存邮件**，无 `Saved message` 日志。
- 邮件不被投递。

### 8. 附件中文文件名测试

**准备**：创建 `测试文件.txt`（UTF-8 编码）。

**发送**：
```bash
python test_smtp_client.py --host 127.0.0.1 --port 8025 --ssl --username alice --password alice123 --sender alice@example.com --receiver bob@example.com --subject "中文附件" --body "测试" --attach 测试文件.txt
```

**接收并解析**：使用支持 MIME 解析的 `test_pop3_client.py` 接收，附件文件名应正确显示为 `测试文件.txt`（不乱码）。

## 测试结果汇总

| 功能 | 测试用例 | 结果 |
|------|----------|------|
| SMTP 纯文本发送 | 正确密码 | ✅ 成功 |
| SMTP HTML 发送 | 正确密码 | ✅ 成功 |
| SMTP 附件发送 | 正确密码 | ✅ 成功（服务端提取附件） |
| SMTP 认证 | 正确密码 | ❌️ **登录失败，邮件仍能发送** |
| SMTP 认证 | 错误密码 | ❌️ **登录失败，邮件仍能发送** |
| POP3 接收 .eml | 明文连接 | ✅ 保存文件 |
| POP3 接收 .eml | SSL 连接 | ✅ 保存文件 |
| MIME 解析 | 接收带附件邮件 | ✅ 正确提取正文和附件 |


## 结论

邮件系统已成功实现以下基础功能：
- ✅ SMTP 发送邮件（支持纯文本、HTML、附件）
- ❌️ SMTP 用户认证（AUTH LOGIN/PLAIN over SSL）
- ✅ POP3 接收邮件（支持 SSL）
- ✅ MIME 解析（提取正文、附件、保存 .eml）
- ❌️ 服务端强制要求认证，拒绝未认证或密码错误的请求
- ✅ 附件存储与元数据记录

部分测试未通过，系统尚未满足题目要求的基础功能及 SSL 加密登录。

