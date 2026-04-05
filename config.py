"""
config.py — 每日《AI核心技术简报》配置中心。

所有参数在此修改，不在业务代码中硬编码。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import list

# ---------------------------------------------------------------------------
# 项目路径
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent
DAILY_DIR = PROJECT_ROOT / "daily"
KB_DIR = PROJECT_ROOT / "knowledge_base"
OUTPUT_DIR = DAILY_DIR

# ---------------------------------------------------------------------------
# GitHub Publishing
# ---------------------------------------------------------------------------

GITHUB_REPO = "YuDong21/ai-core-briefing"
GITHUB_BRANCH = "main"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# ---------------------------------------------------------------------------
# 数据源配置
# ---------------------------------------------------------------------------

@dataclass
class ArxivConfig:
    """ArXiv 监控配置。"""

    categories: list[str] = field(default_factory=lambda: [
        "cs.AI", "cs.CL", "cs.LG", "cs.MA", "cs.RO",
    ])
    max_results_per_category: int = 30
    # 重点关键词过滤（优先级提高）
    priority_keywords: list[str] = field(default_factory=lambda: [
        # Agent 相关
        "agent", "multi-agent", "agentic", "agentic RAG", "tool use",
        "reasoning agent", "autonomous agent", "agent workflow",
        # RAG 相关
        "RAG", "retrieval-augmented", "knowledge retrieval",
        "dense retrieval", "hybrid retrieval", "reranker", "colBERT",
        "vector search", "chunking", "recall",
        # LLM 算法相关
        "mixture of experts", "MoE", "scaling law",
        "attention mechanism", "long context", "context extension",
        "quantization", "QLoRA", "LoRA", "prefix tuning",
        "chain-of-thought", "CoT", "self-consistency",
        "speculative decoding", "KV cache", "paged attention",
        "memory mechanism", "working memory", "semantic cache",
        "reward model", "RLHF", "PPO", "DPO", "KTO",
        "distillation", "model compression", "pruning",
        "sparse attention", "flash attention", "ring attention",
        "multi-modal", "vision-language", "GPT-4V", "LLaVA",
        "embedding", "contrastive learning", "instruction tuning",
        "few-shot", "zero-shot", "in-context learning",
        "world model", "planning", "task decomposition",
        "reflection", "self-correction", "error correction",
        "graph neural network", "GNN", "knowledge graph",
        "neural architecture search", "NAS", "automated ML",
    ])
    # 排除词（水文过滤）
    exclude_keywords: list[str] = field(default_factory=lambda: [
        "survey", "overview", "review", "tutorial",
        "position paper", "workshop", "demo",
        "extended abstract", "short version",
        "meta-analysis", "benchmark only",
    ])


@dataclass
class GitHubTrendingConfig:
    """GitHub Trending 监控配置。"""

    languages: list[str] = field(default_factory=lambda: ["Python", "Jupyter Notebook"])
    topics_filter: list[str] = field(default_factory=lambda: [
        "machine-learning", "deep-learning", "nlp",
        "large-language-model", "transformer", "GPT",
        "reinforcement-learning", "knowledge-graph",
        "vector-database", "rag", "agent",
    ])


@dataclass
class TechBlogConfig:
    """技术博客监控配置。"""

    blogs: list[dict] = field(default_factory=lambda: [
        {
            "name": "Hugging Face Blog",
            "url": "https://huggingface.co/blog",
            "selector": "article h2",
        },
        {
            "name": "OpenAI Blog",
            "url": "https://openai.com/blog",
            "selector": "h2",
        },
        {
            "name": "Anthropic Blog",
            "url": "https://www.anthropic.com/news",
            "selector": "h2",
        },
        {
            "name": "DeepMind Blog",
            "url": "https://deepmind.google/discover/blog/",
            "selector": "h2",
        },
        {
            "name": "Google AI Blog",
            "url": "https://blog.google/technology/ai/",
            "selector": "h2",
        },
        {
            "name": "Meta AI Blog",
            "url": "https://ai.meta.com/blog/",
            "selector": "h2",
        },
        {
            "name": "Microsoft Research",
            "url": "https://www.microsoft.com/en-us/research/blog/",
            "selector": "h2",
        },
    ])


# ---------------------------------------------------------------------------
# 知识库配置（用于过滤水文）
# ---------------------------------------------------------------------------

@dataclass
class KnowledgeBaseConfig:
    """个人知识库配置。"""

    seed_papers_path: Path = KB_DIR / "seed_papers.jsonl"
    similarity_threshold: float = 0.65  # 低于此分数视为低质量/水文
    min_quality_score: float = 0.5     # 知识库匹配分 + 关键词分 综合最低要求


# ---------------------------------------------------------------------------
# LLM 配置（生成简报）
# ---------------------------------------------------------------------------

@dataclass
class LLMConfig:
    """LLM 生成配置。"""

    model: str = "qwen-plus"
    api_key: str = os.getenv("DASHSCOPE_API_KEY", "")
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    temperature: float = 0.3
    max_tokens: int = 4096


# ---------------------------------------------------------------------------
# 简报生成配置
# ---------------------------------------------------------------------------

@dataclass
class BriefingConfig:
    """简报生成配置。"""

    max_papers_per_day: int = 8   # 每天最多收录篇论文
    max_github_projects: int = 5  # 每天最多收录 GitHub 项目
    include_tables: bool = True
    include_architecture_diagrams: bool = True  # 以文字描述形式


# ---------------------------------------------------------------------------
# 全局配置
# ---------------------------------------------------------------------------

def get_config():
    return {
        "arxiv": ArxivConfig(),
        "github_trending": GitHubTrendingConfig(),
        "tech_blogs": TechBlogConfig(),
        "knowledge_base": KnowledgeBaseConfig(),
        "llm": LLMConfig(),
        "briefing": BriefingConfig(),
        "github": {
            "repo": GITHUB_REPO,
            "branch": GITHUB_BRANCH,
            "token": GITHUB_TOKEN,
        },
    }
