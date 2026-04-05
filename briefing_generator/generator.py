"""
generator.py — 《AI核心技术简报》Markdown 生成器。

将论文分析结果、GitHub Trending 项目整合为结构化的
每日 Markdown 简报，包含：
  1. 简报概览（元数据：日期、篇数等）
  2. 今日 ArXiv 精选论文（按优先级排列）
  3. GitHub Trending 精选项目
  4. 技术趋势观察（关键词出现频率统计）
  5. 重点论文深度摘要
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from analyzers import AnalysisResult
from config import BriefingConfig


class BriefingGenerator:
    """
    生成每日《AI核心技术简报》。

    输出格式：Markdown，支持直接渲染或转 PDF。
    文件名：AI核心技术简报_YYYY-MM-DD.md
    """

    def __init__(self, config: BriefingConfig | None = None) -> None:
        self.config = config or BriefingConfig()

    def generate(
        self,
        date: datetime,
        arxiv_results: list[AnalysisResult],
        github_results: list[AnalysisResult],
        blog_results: list[AnalysisResult],
        output_dir: Path | str,
    ) -> tuple[Path, str]:
        """
        生成简报 Markdown 文件。

        Parameters
        ----------
        date           : 简报日期
        arxiv_results  : ArXiv 论文分析结果
        github_results : GitHub 项目分析结果
        blog_results   : 博客文章分析结果
        output_dir     : 输出目录

        Returns
        -------
        (output_path, markdown_content)
        """
        os.makedirs(output_dir, exist_ok=True)
        date_str = date.strftime("%Y-%m-%d")
        weekday = date.strftime("%A")
        output_path = Path(output_dir) / f"AI核心技术简报_{date_str}.md"

        # 限制收录数量
        arxiv_items = arxiv_results[: self.config.max_papers_per_day]
        github_items = github_results[: self.config.max_github_projects]
        blog_items = blog_results[: 3]  # 最多 3 篇博客

        # 技术趋势统计
        tech_trends = self._extract_tech_trends(arxiv_items + github_items)

        # 构建 Markdown
        md = self._build_markdown(
            date_str=date_str,
            weekday=weekday,
            arxiv_items=arxiv_items,
            github_items=github_items,
            blog_items=blog_items,
            tech_trends=tech_trends,
        )

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md)

        print(f"[briefing] Generated: {output_path}")
        return output_path, md

    def _build_markdown(
        self,
        date_str: str,
        weekday: str,
        arxiv_items: list[AnalysisResult],
        github_items: list[AnalysisResult],
        blog_items: list[AnalysisResult],
        tech_trends: dict[str, int],
    ) -> str:
        """构建完整 Markdown 内容。"""
        lines: list[str] = []

        # ═══════════════════════════════════════════════════════════════
        # Header
        # ═══════════════════════════════════════════════════════════════
        lines.append(f"# 🤖 AI 核心技术简报")
        lines.append(f"**日期**: {date_str} ({weekday})  &nbsp;&nbsp; **自动生成**")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("> **本期要点**: 自动筛选 Agent、RAG、LLM 算法领域高价值论文与开源项目，")
        lines.append("> 提取核心创新点和架构思路，逼迫自己和 AI 一起保持对前沿架构的敏锐度。")
        lines.append("")
        lines.append("---")
        lines.append("")

        # ═══════════════════════════════════════════════════════════════
        # 概览统计
        # ═══════════════════════════════════════════════════════════════
        lines.append("## 📊 概览")
        lines.append("")
        lines.append(f"| 来源 | 收录数 |")
        lines.append(f"|------|--------|")
        lines.append(f"| ArXiv 论文 | {len(arxiv_items)} 篇 |")
        lines.append(f"| GitHub Trending | {len(github_items)} 个 |")
        lines.append(f"| 技术博客 | {len(blog_items)} 篇 |")
        lines.append("")

        # 技术趋势词云（用文字表格代替）
        if tech_trends:
            top_trends = sorted(tech_trends.items(), key=lambda x: x[1], reverse=True)[:15]
            lines.append("### 🔥 技术热词（本期高频）")
            lines.append("")
            trend_tags = "  ".join(f"`{kw}×{cnt}`" for kw, cnt in top_trends)
            lines.append(trend_tags)
            lines.append("")

        lines.append("---")
        lines.append("")

        # ═══════════════════════════════════════════════════════════════
        # ArXiv 精选论文
        # ═══════════════════════════════════════════════════════════════
        lines.append(f"## 📄 ArXiv 精选论文（共 {len(arxiv_items)} 篇）")
        lines.append("")

        for i, item in enumerate(arxiv_items, 1):
            lines.append(f"### {i}. {item.title}")
            lines.append("")
            lines.append(f"**🔗 链接**: [{item.source_url}]({item.source_url})")
            if item.authors:
                lines.append(f"**👥 作者**: {item.authors}")
            lines.append(f"**📅 日期**: {item.date}")
            lines.append("")

            if item.core_innovation:
                lines.append(f"**💡 核心创新**: {item.core_innovation}")
                lines.append("")

            if item.architecture_summary:
                lines.append(f"**🏗️ 架构思路**: {item.architecture_summary}")
                lines.append("")

            if item.key_techniques:
                techniques = " / ".join(f"`{t}`" for t in item.key_techniques)
                lines.append(f"**⚙️ 关键技术**: {techniques}")
                lines.append("")

            if item.comparison:
                lines.append(f"**⚖️ 同类对比**: {item.comparison}")
                lines.append("")

            if item.weaknesses:
                weak = "；".join(f"{w}" for w in item.weaknesses[:2])
                lines.append(f"**⚠️ 局限/挑战**: {weak}")
                lines.append("")

            lines.append("---")
            lines.append("")

        # ═══════════════════════════════════════════════════════════════
        # GitHub Trending
        # ═══════════════════════════════════════════════════════════════
        if github_items:
            lines.append(f"## 🐙 GitHub Trending 精选（共 {len(github_items)} 个）")
            lines.append("")

            for i, item in enumerate(github_items, 1):
                lines.append(f"### {i}. {item.title}")
                lines.append("")
                lines.append(f"**🔗 链接**: [{item.source_url}]({item.source_url})")
                if item.authors:
                    lines.append(f"**👤 作者**: {item.authors}")
                lines.append(f"**📅 日期**: {item.date}")
                lines.append("")

                if item.core_innovation:
                    lines.append(f"**💡 核心价值**: {item.core_innovation}")
                    lines.append("")

                if item.architecture_summary:
                    lines.append(f"**🏗️ 架构设计**: {item.architecture_summary}")
                    lines.append("")

                if item.key_techniques:
                    techniques = " / ".join(f"`{t}`" for t in item.key_techniques)
                    lines.append(f"**⚙️ 技术栈**: {techniques}")
                    lines.append("")

                lines.append("---")
                lines.append("")

        # ═══════════════════════════════════════════════════════════════
        # 技术博客
        # ═══════════════════════════════════════════════════════════════
        if blog_items:
            lines.append(f"## 📝 技术博客精选（共 {len(blog_items)} 篇）")
            lines.append("")

            for i, item in enumerate(blog_items, 1):
                lines.append(f"### {i}. {item.title}")
                lines.append("")
                lines.append(f"**🔗 链接**: [{item.source_url}]({item.source_url})")
                lines.append(f"**📰 来源**: {item.source}")
                lines.append("")
                if item.core_innovation:
                    lines.append(f"**💡 核心内容**: {item.core_innovation}")
                    lines.append("")
                lines.append("---")
                lines.append("")

        # ═══════════════════════════════════════════════════════════════
        # Footer
        # ═══════════════════════════════════════════════════════════════
        lines.append("---")
        lines.append("")
        lines.append(f"*🤖 AI 核心技术简报 · {date_str} · 由 ai-core-briefing 自动生成*")
        lines.append(f"*📡 数据来源: ArXiv · GitHub Trending · AI Lab Blogs*")

        return "\n".join(lines)

    @staticmethod
    def _extract_tech_trends(items: list[AnalysisResult]) -> dict[str, int]:
        """统计高频技术词汇。"""
        from collections import Counter

        keywords: list[str] = []
        ALL_KEYWORDS = {
            "Agent", "Multi-Agent", "Agentic RAG", "Tool Use", "RAG",
            "Retrieval-Augmented", "Mixture of Experts", "MoE",
            "Long Context", "Context Extension", "Quantization",
            "QLoRA", "LoRA", "RLHF", "DPO", "PPO",
            "Chain-of-Thought", "CoT", "Self-Consistency",
            "Flash Attention", "Paged Attention", "Ring Attention",
            "Speculative Decoding", "KV Cache",
            "Vision-Language", "Multimodal", "LLaVA", "GPT-4V",
            "Embedding", "Contrastive Learning", "Reranker",
            "Knowledge Graph", "GNN", "World Model",
            "Planning", "Task Decomposition", "Reflection",
            "In-Context Learning", "Few-Shot", "Zero-Shot",
            "Model Distillation", "Pruning", "NAS",
            "Alignment", "Preference Model", "Reward Model",
            "Vector Search", "ColBERT", "BM25", "Dense Retrieval",
        }

        for item in items:
            text = (item.title + " " + item.architecture_summary + " " +
                    " ".join(item.key_techniques)).lower()
            for kw in ALL_KEYWORDS:
                if kw.lower() in text:
                    keywords.append(kw)

        counts = Counter(keywords)
        return dict(counts)
