"""
arxiv.py — ArXiv 论文抓取器。

监控 cs.AI, cs.CL, cs.LG 等分类的最新论文，
按关键词权重过滤后返回高质量论文列表。
"""

from __future__ import annotations

import arxiv
import html
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from config import ArxivConfig


@dataclass
class PaperEntry:
    """单篇论文的结构化表示。"""

    paper_id: str
    title: str
    authors: list[str]
    abstract: str
    categories: list[str]
    published_date: datetime
    updated_date: datetime
    pdf_url: str
    arxiv_url: str
    priority_score: float = 0.0
    matched_keywords: list[str] = field(default_factory=list)
    excluded: bool = False
    source: str = "arxiv"


class ArxivFetcher:
    """
    从 ArXiv 抓取论文，支持分类过滤 + 关键词权重打分。

    使用 ArXiv API，按更新日期倒序取最新论文。
    通过关键词匹配计算 priority_score，辅助知识库过滤。
    """

    def __init__(self, config: ArxivConfig | None = None) -> None:
        self.config = config or ArxivConfig()

    def fetch(self, days_back: int = 2) -> list[PaperEntry]:
        """
        抓取最近 days_back 天内更新的论文。

        Parameters
        ----------
        days_back : int
            向前追溯的天数，默认 2（覆盖最近一次更新）

        Returns
        -------
        list[PaperEntry]，按 priority_score 降序排列
        """
        cutoff = datetime.now() - timedelta(days=days_back)
        all_papers: list[PaperEntry] = []

        for category in self.config.categories:
            papers = self._fetch_category(category, cutoff)
            all_papers.extend(papers)
            time.sleep(1)  # 避免触发 ArXiv API 限流

        # 去重（同一论文可能跨多个分类）
        seen_ids: set[str] = set()
        unique: list[PaperEntry] = []
        for p in all_papers:
            if p.paper_id not in seen_ids:
                seen_ids.add(p.paper_id)
                unique.append(p)

        # 计算优先级分
        for p in unique:
            self._score(p)

        # 过滤排除词命中的论文
        filtered = [p for p in unique if not p.excluded]

        # 降序排列
        filtered.sort(key=lambda x: x.priority_score, reverse=True)

        return filtered

    def _fetch_category(self, category: str, cutoff: datetime) -> list[PaperEntry]:
        """从单个 ArXiv 分类抓取论文。"""
        try:
            client = arxiv.Client(page_size=self.config.max_results_per_category)
            search = arxiv.Search(
                query=f"cat:{category}",
                max_results=self.config.max_results_per_category,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending,
            )
            papers = list(client.results(search))
        except Exception as exc:  # noqa: BLE001
            print(f"[arxiv] ERROR fetching {category}: {exc}")
            return []

        results: list[PaperEntry] = []
        for paper in papers:
            if paper.updated_date < cutoff:
                continue

            # 清理 abstract
            abstract = self._clean_abstract(paper.summary)

            results.append(PaperEntry(
                paper_id=paper.entry_id.split("/")[-1],
                title=html.unescape(paper.title or ""),
                authors=[a.name for a in (paper.authors or [])],
                abstract=abstract,
                categories=paper.categories or [],
                published_date=paper.published_date,
                updated_date=paper.updated_date,
                pdf_url=paper.pdf_url or "",
                arxiv_url=paper.entry_id or "",
            ))

        return results

    def _score(self, paper: PaperEntry) -> None:
        """计算论文优先级分（0-1）。"""
        score = 0.0
        matched: list[str] = []
        text = (paper.title + " " + paper.abstract).lower()

        # 精确关键词匹配
        for kw in self.config.priority_keywords:
            kw_lower = kw.lower()
            if kw_lower in text:
                score += 0.1
                matched.append(kw)
                # 高价值词额外加分
                high_value = {"agentic", "mixture of experts", "MoE", "RLHF", "DPO",
                              "long context", "speculative decoding", "ring attention",
                              "flash attention", "paged attention", "colBERT",
                              "agentic RAG", "knowledge graph", "world model"}
                if kw_lower in high_value:
                    score += 0.05

        # 排除词检测
        for ex_kw in self.config.exclude_keywords:
            if ex_kw.lower() in text:
                paper.excluded = True
                return

        # ArXiv 热门分类加分
        hot_cats = {"cs.CL", "cs.LG", "cs.AI"}
        if set(paper.categories) & hot_cats:
            score += 0.05

        # 近期引用暗示（标题含 2024/2025 更有时效性）
        year = str(datetime.now().year)
        if year in paper.title:
            score += 0.05

        paper.priority_score = min(score, 1.0)
        paper.matched_keywords = matched[:10]  # 保留最多10个匹配词

    @staticmethod
    def _clean_abstract(text: str) -> str:
        """清理 ArXiv abstract 中的特殊字符和多余空白。"""
        text = re.sub(r"\s+", " ", text)
        text = text.replace("\n", " ").strip()
        return text
