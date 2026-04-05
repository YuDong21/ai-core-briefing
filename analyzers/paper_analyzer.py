"""
paper_analyzer.py — 论文核心内容提取器。

使用 LLM（通义千问）从论文的标题、摘要、描述中
提取：
  1. 核心创新点（Core Innovation）
  2. 架构思路（Architecture）
  3. 技术细节（Technical Details）
  4. 相关工作对比（Comparison）
  5. 潜在应用场景
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Optional

import dashscope
from dashscope import Generation

from config import LLMConfig


@dataclass
class AnalysisResult:
    """
    单篇论文/项目的分析结果。

    所有字段均由 LLM 生成，保证结构化输出。
    """

    paper_id: str
    title: str
    source: str  # "arxiv" / "github_trending" / "tech_blog"

    # 核心分析
    core_innovation: str = ""        # 一句话描述核心创新
    architecture_summary: str = ""   # 架构思路（100-200字）
    key_techniques: list[str] = field(default_factory=list)  # 关键技术列表
    strengths: list[str] = field(default_factory=list)      # 优势
    weaknesses: list[str] = field(default_factory=list)     # 局限/挑战
    comparison: str = ""              # 与同类工作对比

    # 元数据
    source_url: str = ""
    authors: str = ""        # ArXiv authors 或 GitHub owner
    date: str = ""           # 发布/更新日期

    # LLM 原始输出（用于调试）
    raw_llm_output: str = ""

    def to_dict(self) -> dict:
        return {
            "paper_id": self.paper_id,
            "title": self.title,
            "source": self.source,
            "core_innovation": self.core_innovation,
            "architecture_summary": self.architecture_summary,
            "key_techniques": self.key_techniques,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "comparison": self.comparison,
            "source_url": self.source_url,
            "authors": self.authors,
            "date": self.date,
        }


class PaperAnalyzer:
    """
    使用通义千问分析论文/项目的核心价值。

    两种模式：
      - arxiv    : 基于 abstract + title 分析（有完整摘要）
      - lightweight: 基于 title + description 分析（GitHub/博客）

    Prompt 工程：强制 JSON 输出，保证结构化。
    """

    ARXIV_ANALYSIS_PROMPT = """你是一位专业的 AI 论文评审专家。请分析以下 ArXiv 论文，提取核心价值。

论文标题: {title}
作者: {authors}
摘要: {abstract}

请以 JSON 格式输出分析结果（严格遵循格式，不要输出 JSON 之外的内容）：
{{
  "core_innovation": "一句话描述论文的核心创新点（≤30字）",
  "architecture_summary": "架构思路描述：模型/系统整体设计、主要组件、数据流（100-200字）",
  "key_techniques": ["关键技术1", "关键技术2", "关键技术3"],
  "strengths": ["优势1", "优势2"],
  "weaknesses": ["局限/挑战1", "局限/挑战2"],
  "comparison": "与同类工作（如 GPT-4、Claude、LLaMA、RAG、BERT 等）的核心差异对比（50-100字）"
}}

注意：只输出 JSON，不要有其他文字。"""

    LIGHTWEIGHT_PROMPT = """你是一位专业的 AI 技术分析师。请分析以下项目/文章，提取核心价值。

标题: {title}
描述: {description}

请以 JSON 格式输出分析结果（严格遵循格式）：
{{
  "core_innovation": "一句话描述核心创新/价值（≤30字）",
  "architecture_summary": "架构设计描述：技术选型、核心组件、实现思路（80-150字）",
  "key_techniques": ["技术1", "技术2", "技术3"],
  "strengths": ["优势1", "优势2"],
  "weaknesses": ["局限1", "局限2"],
  "comparison": "与同类开源项目或主流方案的核心差异（50字）"
}}

只输出 JSON，不要有其他文字。"""

    def __init__(self, config: LLMConfig | None = None) -> None:
        self.config = config or LLMConfig()
        if self.config.api_key:
            dashscope.api_key = self.config.api_key

    def analyze_arxiv(
        self,
        paper_id: str,
        title: str,
        abstract: str,
        authors: list[str],
        date: str,
        url: str,
    ) -> AnalysisResult:
        """分析 ArXiv 论文（有完整 abstract）。"""
        prompt = self.ARXIV_ANALYSIS_PROMPT.format(
            title=title,
            authors=", ".join(authors[:5]) + (" et al." if len(authors) > 5 else ""),
            abstract=abstract[:2000],  # 限制长度
        )

        raw = self._call_llm(prompt)

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            # 尝试修复常见 JSON 错误
            raw_clean = self._fix_json(raw)
            try:
                parsed = json.loads(raw_clean)
            except Exception:  # noqa: BLE001
                parsed = {
                    "core_innovation": "(解析失败)",
                    "architecture_summary": raw[:300],
                    "key_techniques": [],
                    "strengths": [],
                    "weaknesses": [],
                    "comparison": "",
                }

        return AnalysisResult(
            paper_id=paper_id,
            title=title,
            source="arxiv",
            source_url=url,
            authors=", ".join(authors[:5]) + (" et al." if len(authors) > 5 else ""),
            date=date,
            core_innovation=parsed.get("core_innovation", ""),
            architecture_summary=parsed.get("architecture_summary", ""),
            key_techniques=parsed.get("key_techniques", []),
            strengths=parsed.get("strengths", []),
            weaknesses=parsed.get("weaknesses", []),
            comparison=parsed.get("comparison", ""),
            raw_llm_output=raw[:500],
        )

    def analyze_lightweight(
        self,
        paper_id: str,
        title: str,
        description: str,
        date: str,
        url: str,
        authors: str = "",
    ) -> AnalysisResult:
        """分析 GitHub 项目或博客文章（描述有限）。"""
        prompt = self.LIGHTWEIGHT_PROMPT.format(
            title=title,
            description=description[:1500],
        )

        raw = self._call_llm(prompt)

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            raw_clean = self._fix_json(raw)
            try:
                parsed = json.loads(raw_clean)
            except Exception:  # noqa: BLE001
                parsed = {
                    "core_innovation": "(解析失败)",
                    "architecture_summary": raw[:200],
                    "key_techniques": [],
                    "strengths": [],
                    "weaknesses": [],
                    "comparison": "",
                }

        return AnalysisResult(
            paper_id=paper_id,
            title=title,
            source="github_trending" if "github.com" in url else "tech_blog",
            source_url=url,
            authors=authors,
            date=date,
            core_innovation=parsed.get("core_innovation", ""),
            architecture_summary=parsed.get("architecture_summary", ""),
            key_techniques=parsed.get("key_techniques", []),
            strengths=parsed.get("strengths", []),
            weaknesses=parsed.get("weaknesses", []),
            comparison=parsed.get("comparison", ""),
            raw_llm_output=raw[:500],
        )

    def _call_llm(self, prompt: str) -> str:
        """调用通义千问 API。"""
        if not self.config.api_key:
            return self._mock_response(prompt)

        try:
            resp = Generation.call(
                model=self.config.model,
                prompt=prompt,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            if resp.status_code == 200:
                return resp.output.text or ""
            else:
                print(f"[analyzer] LLM error: {resp.status_code} {resp.message}")
                return ""
        except Exception as exc:  # noqa: BLE001
            print(f"[analyzer] LLM call failed: {exc}")
            return ""

    @staticmethod
    def _fix_json(raw: str) -> str:
        """修复常见的 JSON 格式错误。"""
        # 去掉 markdown 代码块
        raw = raw.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:] if lines[0] == "```" else lines)
        if raw.endswith("```"):
            raw = raw[:-3].strip()
        # 去掉开头的非 JSON 字符
        first_brace = raw.find("{")
        if first_brace > 0:
            raw = raw[first_brace:]
        last_brace = raw.rfind("}")
        if last_brace > 0:
            raw = raw[:last_brace + 1]
        return raw

    @staticmethod
    def _mock_response(prompt: str) -> str:
        """无 API Key 时的 mock 输出（用于测试）。"""
        return json.dumps({
            "core_innovation": "(无 API Key，mock 结果)",
            "architecture_summary": "请配置 DASHSCOPE_API_KEY 以获取真实分析结果。",
            "key_techniques": ["[mock]"],
            "strengths": ["[mock]"],
            "weaknesses": ["[mock]"],
            "comparison": "[mock]",
        })
