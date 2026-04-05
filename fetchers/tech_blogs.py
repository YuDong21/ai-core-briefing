"""
tech_blogs.py — 技术博客文章抓取器。

抓取 Hugging Face、OpenAI、Anthropic、DeepMind、Meta AI 等
主要 AI 实验室的最新博客文章，按关键词过滤。
"""

from __future__ import annotations

import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from config import TechBlogConfig


@dataclass
class BlogArticle:
    """博客文章的结构化表示。"""

    title: str
    url: str
    source_name: str
    published_date: datetime | None
    summary: str
    matched_keywords: list[str] = field(default_factory=list)
    priority_score: float = 0.0
    source: str = "tech_blog"


class TechBlogFetcher:
    """
    抓取多个 AI 技术博客的最新文章。

    默认监控：HuggingFace, OpenAI, Anthropic, DeepMind,
    Google AI, Meta AI, Microsoft Research
    """

    # 高价值关键词，用于打分
    HIGH_VALUE_KEYWORDS = {
        "agent", "tool use", "reasoning", "chain-of-thought",
        "multimodal", "vision-language", "LLaVA", "GPT-4V",
        "mixture of experts", "MoE", "scaling",
        "long context", "RAG", "retrieval",
        "alignment", "RLHF", "DPO", "preference",
        "distillation", "quantization", "LoRA", "QLoRA",
        "architecture", "model", "training",
        "inference", "benchmark", "SOTA",
    }

    def __init__(self, config: TechBlogConfig | None = None) -> None:
        self.config = config or TechBlogConfig()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        })

    def fetch(self) -> list[BlogArticle]:
        """
        抓取所有配置的博客。

        Returns
        -------
        list[BlogArticle]，按 priority_score 降序
        """
        all_articles: list[BlogArticle] = []

        for blog in self.config.blogs:
            try:
                articles = self._fetch_blog(blog)
                all_articles.extend(articles)
            except Exception as exc:  # noqa: BLE001
                print(f"[tech_blogs] ERROR fetching {blog['name']}: {exc}")

        # 打分并排序
        for a in all_articles:
            self._score(a)

        all_articles.sort(key=lambda x: x.priority_score, reverse=True)
        return all_articles

    def _fetch_blog(self, blog: dict) -> list[BlogArticle]:
        """抓取单个博客的最新文章。"""
        url = blog["url"]
        selector = blog["selector"]
        name = blog["name"]

        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            print(f"[tech_blogs] HTTP error {name}: {exc}")
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        articles: list[BlogArticle] = []

        # 尝试通用 h2 列表
        for elem in soup.select(selector)[:15]:
            try:
                title = elem.get_text(strip=True)
                if not title or len(title) < 10:
                    continue

                # 获取链接
                link_elem = elem if elem.name == "a" else elem.find_parent("a")
                if link_elem:
                    href = link_elem.get("href", "")
                    if href.startswith("/"):
                        from urllib.parse import urljoin
                        article_url = urljoin(url, href)
                    elif href.startswith("http"):
                        article_url = href
                    else:
                        article_url = url
                else:
                    article_url = url

                # 尝试获取日期
                date: datetime | None = None
                date_elem = elem.find_parent("article") or elem.find_parent("div")
                if date_elem:
                    date_str = date_elem.get("datetime") or ""
                    if date_str:
                        try:
                            date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                        except Exception:  # noqa: BLE001
                            pass

                articles.append(BlogArticle(
                    title=title,
                    url=article_url,
                    source_name=name,
                    published_date=date,
                    summary="",  # 摘要从详情页中提取（可选优化）
                ))

            except Exception as exc:  # noqa: BLE001
                continue

        return articles

    def _score(self, article: BlogArticle) -> None:
        """计算博客文章的优先级分。"""
        text = (article.title + " " + article.summary).lower()
        score = 0.0
        matched: list[str] = []

        for kw in self.HIGH_VALUE_KEYWORDS:
            if kw in text:
                score += 0.15
                matched.append(kw)

        # 标题含高价值词额外加分
        high_title = {"agent", "reasoning", "MoE", "multimodal", "alignment",
                      "GPT-5", "Claude", "Gemini", "LLaMA", "training"}
        for kw in high_title:
            if kw.lower() in article.title.lower():
                score += 0.1

        article.priority_score = min(score, 1.0)
        article.matched_keywords = matched[:8]
