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
```

### 3. 本地运行

```bash
# 生成今日简报
python main.py

# 输出: daily/AI核心技术简报_2026-04-05.md
```

### 4. GitHub Actions（每天自动运行）

在 GitHub 仓库设置 secrets：
- `DASHSCOPE_API_KEY` — 通义千问 API Key
- `GITHUB_TOKEN` — 自动提供（无需手动设置）

Actions 将每天 UTC 00:00（北京时间 8:00）自动运行并推送简报。

## 📂 项目结构

```
ai-core-briefing/
├── main.py                      # ⭐ 主入口
├── config.py                    # ⭐ 配置中心
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

- `DASHSCOPE_API_KEY` 和 `GITHUB_TOKEN` 只放在 GitHub Secrets 中，不要提交到代码
- `seed_papers.jsonl` 可随时编辑，格式无要求，保持多样性即可
