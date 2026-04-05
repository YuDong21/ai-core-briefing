"""
analyzers/ — 论文深度分析模块。

paper_analyzer.py — 用 LLM 从论文 abstract/paper 中
提取核心创新点、架构思路、技术细节。
"""

from .paper_analyzer import PaperAnalyzer, AnalysisResult

__all__ = ["PaperAnalyzer", "AnalysisResult"]
