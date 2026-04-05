# 🤖 AI 核心技术简报

> 每天自动筛选 Agent、RAG、LLM 算法领域高价值论文与开源项目，提取核心创新点 + 架构思路，推送到邮箱。

---

## ⚡ 30 秒上手

### 1. 填写配置

打开 `run.py`，找到顶部【配置区】，填入 5 行：

```python
DASHSCOPE_API_KEY = "sk-xxxxxxxx"           # LLM的 API
SMTP_USERNAME     = "your@email.com"        # 发件邮箱
SMTP_PASSWORD     = "smtp_auth_code"       # SMTP 授权码（非登录密码）
recipients        = ["your@email.com"]      # 收件人
```

**QQ 邮箱授权码获取：** QQ邮箱 → 设置 → 账户 → POP3/SMTP服务 → 开启 → 生成授权码

### 2. 一键运行

```bash
pip install -r requirements.txt
python run.py
```

---

## 📋 使用方式

```bash
python run.py              # 完整流程：生成 + 邮件 + GitHub
python run.py --no-email   # 仅生成简报，不发邮件
python run.py --no-github  # 仅发邮件，不推 GitHub
```

---

## 🔧 配置说明（全部在 `run.py` 顶部）

| 变量 | 必须 | 说明 |
|------|------|------|
| `DASHSCOPE_API_KEY` | ✅ | LLM的 API |
| `SMTP_USERNAME` | 发邮件时必须 | 邮箱地址 |
| `SMTP_PASSWORD` | 发邮件时必须 | SMTP 授权码（不是登录密码）|
| `SMTP_HOST/PORT` | 否 | 邮箱服务器，默认 QQ 邮箱 |
| `recipients` | 发邮件时必须 | 收件人列表 |
| `GITHUB_TOKEN` | 推送 GitHub 时必须 | GitHub Personal Access Token |
| `GITHUB_REPO` | 推送 GitHub 时必须 | 仓库名，如 `YuDong21/ai-core-briefing` |

---

## 📁 项目结构

```
ai-core-briefing/
├── run.py                    # ⭐ 唯一入口（配置 + 全流程逻辑）
├── requirements.txt          # 依赖
├── fetchers/                # 数据抓取
├── analyzers/               # LLM 分析
├── briefing_generator/       # 简报生成
├── knowledge_base/           # 知识库（可选）
├── publish.py               # GitHub 发布
└── daily/                   # 生成的简报
```

---

## ⏰ 定时任务（Windows）

创建定时任务，每天 21:00 自动运行：

```
任务计划程序 → 创建基本任务
   → 触发器：每天 21:00
  → 操作：启动程序
  → 程序：py
  → 参数：C:\path\to\ai-core-briefing\run.py
```

---

## 📧 邮件效果

每晚 21:00 收到一封 HTML 邮件，包含：
- 本期概览（收录多少篇论文/项目）
- 技术热词统计
- 每篇论文的核心创新 + 架构思路 + 关键技术
- 每小时 GitHub Trending 精选项目的架构设计

---
