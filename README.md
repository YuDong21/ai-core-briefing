# 🤖 AI 核心技术简报

> **每天自动筛选 Agent、RAG、LLM 算法领域高价值论文与开源项目，逼迫自己和 Agent 一起保持对前沿架构的敏锐度。**

---

## 🎯 项目目标

- **输入流**：自动监控 ArXiv CS.AI/CL/LG、GitHub Trending、技术博客
- **过滤层**：基于个人知识库（种子论文 embedding）剔除水文
- **分析层**：通义千问提取核心创新点 + 架构思路
- **输出层**：每天自动生成 `AI核心技术简报_YYYY-MM-DD.md`，推送 GitHub

## 📡 监控数据源

| 来源 | 说明 |
|------|------|
| ArXiv | cs.AI, cs.CL, cs.LG, cs.MA, cs.RO 最新论文 |
| GitHub Trending | Python/Jupyter 高星 AI/ML 项目 |
| Tech Blogs | HuggingFace / OpenAI / Anthropic / DeepMind / Meta AI / Microsoft Research |

## 🔥 重点关注领域

```
Agent · Agentic RAG · Tool Use · Multi-Agent
RAG · Dense Retrieval · Hybrid Retrieval · Reranker · ColBERT
LLM 算法: MoE · Long Context · Quantization · LoRA/QLoRA
对齐: RLHF · DPO · PPO · Alignment
注意力: Flash Attention · Ring Attention · Paged Attention
多模态: Vision-Language · LLaVA · GPT-4V
架构: Transformer · Scaling Law · Speculative Decoding
```

## 🚀 快速开始

### 1. 克隆 + 安装

```bash
git clone https://github.com/YuDong21/ai-core-briefing.git
cd ai-core-briefing
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 通义千问 API（生成简报用）
export DASHSCOPE_API_KEY="sk-xxxxxxxx"

# GitHub Token（自动推送简报用）
export GITHUB_TOKEN="ghp_xxxxxx"

# 邮件发送（SMTP 方式，QQ/163/Gmail 均可）
export SMTP_USERNAME="your_email@example.com"
export SMTP_PASSWORD="your_smtp_auth_code"   # ⚠️ 不是登录密码，是授权码
#  QQ邮箱: 设置 → 账户 → POP3/SMTP服务 → 生成授权码
#  163邮箱: 设置 → POP3/SMTP/SMTP → 开启并获取授权码

# 或者用 SendGrid（更稳定）
export SENDGRID_API_KEY="SG.xxxx..."
```

### 3. 本地运行

```bash
# 生成今日简报（自动发送邮件）
python main.py

# 输出: daily/AI核心技术简报_2026-04-05.md
```

### 4. GitHub Actions（每天自动运行 + 邮件通知）

在 GitHub 仓库设置 Secrets：
| Secret 名称 | 说明 |
|-------------|------|
| `DASHSCOPE_API_KEY` | 通义千问 API Key |
| `SMTP_USERNAME` | 发件邮箱（如 `2601082764@qq.com`）|
| `SMTP_PASSWORD` | SMTP 授权码（不是登录密码）|
| `EMAIL_TO` | 收件人邮箱（如 `2601082764@qq.com`）|
| `GITHUB_TOKEN` | 自动提供，无需手动设置 |

以及 Repository Variables：
| Variable 名称 | 值 |
|--------------|---|
| `SMTP_HOST` | `smtp.qq.com`（QQ邮箱）或 `smtp.163.com` 等 |
| `SMTP_PORT` | `465`（SSL，推荐）|
| `EMAIL_FROM_NAME` | `AI 核心技术简报` |

Actions 将每天 UTC 00:00（北京时间 8:00）自动运行并推送简报到 GitHub，同时发送邮件到你的邮箱。

## 📂 项目结构

```
ai-core-briefing/
├── main.py                      # ⭐ 主入口
├── config.py                    # ⭐ 配置中心（API/邮件/SMTP）
├── notifier.py                  # ⭐ 邮件发送（SMTP / SendGrid）
├── publish.py                   # GitHub 自动发布
├── requirements.txt
├── README.md
├── .github/workflows/daily.yml  # ⭐ GitHub Actions 定时任务
│
├── fetchers/                    # 数据源抓取
│   ├── arxiv.py                 # ArXiv 论文抓取 + 关键词打分
│   ├── github_trending.py       # GitHub Trending 抓取
│   └── tech_blogs.py            # 技术博客抓取
│
├── knowledge_base/              # 个人知识库（过滤水文）
│   ├── knowledge_base.py        # BGE-M3 embedding + 相似度过滤
│   └── seed_papers.jsonl        # ⭐ 手工维护的高价值论文列表
│
├── analyzers/                   # LLM 深度分析
│   └── paper_analyzer.py        # 通义千问提取核心创新点 + 架构
│
├── briefing_generator/          # 简报生成
│   └── generator.py             # 《AI核心技术简报》Markdown 生成
│
└── daily/                       # 生成的简报（自动推送到 GitHub）
    └── AI核心技术简报_YYYY-MM-DD.md
```

## 🧠 知识库设计

`knowledge_base/seed_papers.jsonl` 是你个人维护的高价值论文锚点。

**维护方式**：每行一个 JSON，示例：

```jsonl
{"title": "Attention Is All You Need", "abstract": "Transformer架构...", "keywords": ["transformer", "attention", "NLP"]}
{"title": "GPT-4 Technical Report", "abstract": "Large multimodal model...", "keywords": ["LLM", "multimodal", "GPT-4"]}
{"title": "RAG vs. SFT", "abstract": "Comparison of retrieval augmented...", "keywords": ["RAG", "SFT", "LLM"]}
```

**原理**：新论文 embedding 与知识库做余弦相似度，低于阈值 → 水文过滤。

## 📄 简报格式

每份简报包含：

```
🤖 AI 核心技术简报 · 2026-04-05
=========================================
📊 概览          ArXiv 8篇 | GitHub 5个 | 博客 2篇
🔥 技术热词      Agent×4  RAG×3  MoE×2  LongContext×2

📄 ArXiv 精选论文
  1. [Title] 💡核心创新 | 🏗️架构思路 | ⚙️关键技术
  2. ...

🐙 GitHub Trending
  1. owner/repo 💡核心价值 | 🏗️架构设计
  2. ...
```

## ⚙️ 配置

所有参数集中在 `config.py`：

```python
# 关键词过滤（提高权重）
priority_keywords = ["agentic RAG", "MoE", "RLHF", "Long Context", ...]

# 知识库阈值
min_quality_score = 0.5  # 综合分低于此值 → 过滤

# 简报收录上限
max_papers_per_day = 8
max_github_projects = 5
```

## 🔒 安全提示

- 所有 API Key 和密码只放在 GitHub Secrets 中，不要提交到代码
- SMTP 授权码不是邮箱登录密码，是专用授权码（QQ/163 邮箱均可在线生成）
- `seed_papers.jsonl` 可随时编辑，保持多样性即可

## 📧 邮件发送配置详解

### 方式一：SMTP（推荐，简单免费）

**QQ 邮箱设置步骤：**
1. 登录 QQ 邮箱 → 设置 → 账户
2. 找到「POP3/SMTP服务」→ 开启
3. 点击「生成授权码」（会发短信验证）
4. 得到 16 位授权码，填入 `SMTP_PASSWORD`

**GitHub Secrets 设置：**
| Secret | 值 |
|--------|-----|
| `SMTP_USERNAME` | `2601082764@qq.com` |
| `SMTP_PASSWORD` | `abcdexxxxxxxxxxxx`（授权码）|
| `EMAIL_TO` | `2601082764@qq.com` |

**Repository Variables：**
| Variable | 值 |
|----------|----|
| `SMTP_HOST` | `smtp.qq.com` |
| `SMTP_PORT` | `465` |

### 方式二：SendGrid（更稳定，适合生产环境）

1. 注册 https://sendgrid.com（免费 100 封/天）
2. Settings → API Keys → Create API Key → Full Access
3. 将 `SENDGRID_API_KEY` 填入 GitHub Secrets

### 本地测试邮件发送

```bash
export SMTP_USERNAME="2601082764@qq.com"
export SMTP_PASSWORD="your_auth_code"
python -c "from notifier import send_email; print(send_email('# Test', '2026-04-05'))"
```
