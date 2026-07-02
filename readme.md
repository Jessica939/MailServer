MailServer — 教学用简易邮件服务器与客户端

概要
本仓库实现了一个用于教学的邮件系统原型，包含：
- SMTP 服务端（接收并保存邮件为 .eml）
- POP3 服务端（提供 mailbox 列表与检索，支持正常邮件/垃圾邮件视图）
- 简易客户端脚本（发送/接收测试用）
- MIME 附件支持与 TLS（测试用 self-signed 证书）
- 基于朴素贝叶斯的垃圾邮件识别

主要文件
- [init_db.py](init_db.py) — 初始化数据库与测试用户（admin / alice / bob）
- [smtp_server.py](smtp_server.py) — SMTP 服务端（使用 aiosmtpd），保存邮件到 `mail_data/` 并记录到 SQLite，可选加载垃圾邮件分类模型
- [pop3_server.py](pop3_server.py) — 简易 POP3 服务端（可选隐式 SSL），支持 `+spam` 后缀查看垃圾邮件
- [tls_config.py](tls_config.py) — 创建服务器/客户端测试用 SSLContext（使用 `cert.pem` / `key.pem`）
- [test_smtp_client.py](test_smtp_client.py) — SMTP 测试客户端（支持 HTML、附件、STARTTLS/SSL、登录）
- [test_pop3_client.py](test_pop3_client.py) — POP3 测试客户端（支持保存为 `.eml`）
- [classifier.py](classifier.py) / [tokenizer.py](tokenizer.py) — 垃圾邮件分类器和分词清洗逻辑
- [process_trec06c.py](process_trec06c.py) / [train.py](train.py) / [classifier_evaluator.py](classifier_evaluator.py) — 数据集预处理、训练和评估脚本

核心功能实现

**邮件发送（SMTP）**
- 支持 SMTP 认证：`AUTH PLAIN` 与 `AUTH LOGIN` 机制，基于 SQLite 用户数据库验证
- 可选 TLS 支持：隐式 SMTPS 或 STARTTLS（默认强制 TLS 后才允许 AUTH，可通过 `--no-auth-require-tls` 禁用）
- MIME 邮件处理：支持纯文本、HTML 格式、以及 multipart/mixed 附件
- 附件自动提取：解析 MIME 边界与编码，自动提取附件到 `mail_data/attachments/<eml-id>/` 目录
- 邮件持久化：所有邮件保存为 `.eml` 格式，同时在 SQLite 中记录元数据（发件人、收件人、时间戳、附件列表）
- 若当前目录存在 `bayes_model.json`，收到邮件时自动分类并写入 `emails.is_spam`；没有模型时分类功能自动禁用

**邮件接收（POP3）**
- 支持基本 POP3 命令：`STAT`、`LIST`、`RETR`、`QUIT`
- 用户认证：`USER` / `PASS` 明文认证，支持两种用户名格式（`alice` 或 `alice@example.com`）
- 可选隐式 SSL：POP3S 支持（`--ssl` 启动）
- 邮件检索：按用户邮箱地址本地部分（local-part）过滤邮件
- 使用 `alice+spam` 或 `alice+spam@example.com` 登录时，只返回被标记为垃圾邮件的邮件

**客户端功能**
- `test_smtp_client.py`：支持 HTML 正文、多文件附件（逗号分隔）、用户认证、STARTTLS 与隐式 SSL
- `test_pop3_client.py`：下载邮件并保存为 `.eml` 格式（可指定保存目录），支持隐式 POP3S
- `test_pop3_classify.py`：分别用普通账号和 `+spam` 账号查看两种邮箱视图

快速开始

### 1. 初始化环境
```bash
pip install -r requirements.txt
```

```bash
python3 init_db.py
```
这会创建 SQLite 数据库和测试用户（admin / alice / bob）。

### 2. 训练垃圾邮件分类器（可选）

仓库不提交训练语料和 `bayes_model.json`。如果需要启用分类功能，请先准备 TREC06C 数据集或整理好的 `corpus/spam`、`corpus/ham` 目录，然后运行：

```bash
python3 process_trec06c.py
python3 train.py
```

训练完成后会生成 `bayes_model.json`。SMTP 服务启动时如果找到该文件，会自动加载模型；否则邮件仍正常收发，只是默认按非垃圾邮件入库。

### 3. 启动 SMTP 服务

允许在明文上进行 AUTH（测试用）：
```bash
python3 smtp_server.py --host 127.0.0.1 --port 8025 --no-auth-require-tls
```

隐式 SMTPS（允许在该加密通道内直接进行身份验证）：
```bash
python3 smtp_server.py --host 127.0.0.1 --port 8465 --ssl --no-auth-require-tls
```

### 4. 发送测试邮件

**纯文本邮件**：
```bash
python3 test_smtp_client.py \
  --host 127.0.0.1 --port 8025 \
  --username alice --password alice123 \
  --subject "Test" \
  --body "Hello World"
```

**HTML 邮件 + 附件**：
```bash
echo "这是附件内容" > /tmp/test.txt
python3 test_smtp_client.py \
  --host 127.0.0.1 --port 8025 \
  --username alice --password alice123 \
  --html \
  --attach /tmp/test.txt \
  --subject "MIME 测试" \
  --body "这是带附件的邮件"
```

**使用 STARTTLS 与隐式 SSL**（注意：需要 `--no-auth-require-tls` 以允许 AUTH）：
```bash
python3 test_smtp_client.py --host 127.0.0.1 --port 8465 --ssl --username alice --password alice123 --html --attach /tmp/test.txt --subject "Encrypted" --body "Test"
```

**明文SMTP**
```bash
python3 test_smtp_client.py --host 127.0.0.1 --port 8025 --username alice --password alice123 --html --attach /tmp/test.txt --subject "Encrypted" --body "Test"
```

### 5. 启动 POP3 服务
```bash
python3 pop3_server.py --host 127.0.0.1 --port 8110
```

隐式 POP3S：
```bash
python3 pop3_server.py --ssl
```

### 6. 接收邮件

下载并保存为 `.eml`：
```bash
python3 test_pop3_client.py \
  --host 127.0.0.1 --port 8110 \
  --username alice \
  --password alice123 \
  --message 1 \
  --save-dir downloaded_emails
```

支持两种用户名格式：
```bash
python3 test_pop3_client.py --username alice  # 本地部分
python3 test_pop3_client.py --username alice@example.com  # 完整邮箱地址
python3 test_pop3_client.py --username alice+spam  # 垃圾邮件视图
```

## 验证 MIME 结构

生成的 `.eml` 文件是合法 MIME 邮件。可用 Python 验证：
```python
from email import policy
from email.parser import BytesParser
from pathlib import Path

msg = BytesParser(policy=policy.default).parsebytes(Path("mail_data/xxx.eml").read_bytes())
for part in msg.walk():
    print(f"类型: {part.get_content_type()}, 附件: {part.get_filename()}")
    if part.get_content_disposition() == "attachment":
        print(f"内容: {part.get_payload(decode=True)[:100]}")
```

## 实现细节

### SMTP 协议支持
- **认证机制**：`AUTH PLAIN`、`AUTH LOGIN`（通过 aiosmtpd 自动协商）
- **加密**：STARTTLS（SMTP）或隐式 SMTPS
- **MIME 处理**：
  - 使用标准库 `email.parser.BytesParser` 解析邮件
  - 支持 `multipart/alternative`（纯文本 + HTML）
  - 支持 `multipart/mixed`（正文 + 附件）
  - 自动处理 Base64、Quoted-Printable 编码
  - 附件文件名清理与去重
- **垃圾邮件识别**：
  - 启动时加载 `bayes_model.json`
  - 提取纯文本和 HTML 正文后调用 `NaiveBayesClassifier.predict`
  - 分类失败或模型不存在时降级为正常邮件，不影响收信

### POP3 协议支持
- **命令**：USER、PASS、STAT、LIST、RETR、QUIT
- **加密**：隐式 POP3S
- **用户映射**：自动规范化用户名（去掉 `@example.com` 后缀）
- **邮箱过滤**：按用户本地部分（local-part）过滤邮件
- **分类视图**：用户名带 `+spam` 后缀时查询 `is_spam=1`，否则查询 `is_spam=0`

### 垃圾邮件过滤
- 使用 jieba 分词、停用词过滤、URL/HTML/标点清洗构建词袋特征
- 使用拉普拉斯平滑的朴素贝叶斯分类器
- 模型文件 `bayes_model.json` 是训练产物，已通过 `.gitignore` 排除

### 数据库设计
```sql
users           # 用户名、密码（明文存储）
emails          # 邮件元数据（发件人、收件人、时间、.eml 路径、is_spam 标记）
attachments     # 附件记录（所属邮件、文件名、MIME 类型、文件路径、大小）
```

## 文件结构

```
mail_server.db              # SQLite 数据库（用户、邮件、附件元数据）
bayes_model.json            # 训练生成的分类模型（不提交到 Git）
cert.pem / key.pem          # TLS 自签证书与密钥
mail_data/                  # 邮件存储目录
  └── *.eml                 # 原始 MIME 邮件文件
  └── attachments/          # 提取的附件
      └── <eml-id>/         # 按邮件 ID 分目录存放
          └── *.txt|*.pdf|...
```

## 教学用途说明

本项目适合用于以下课程与实验：
- **计算机网络**：SMTP / POP3 协议深入理解
- **应用层协议**：邮件传输的完整工作流
- **MIME 与编码**：多部分邮件结构与附件处理
- **网络安全**：TLS/SSL 加密通信、用户认证
- **机器学习**：文本预处理、朴素贝叶斯分类、模型评估

代码注释与模块化设计便于学生修改与扩展。
