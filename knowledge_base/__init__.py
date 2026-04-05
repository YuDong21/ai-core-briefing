"""
knowledge_base/ — 个人知识库模块。

seed_papers.jsonl：手工维护的高价值论文/项目列表，
作为质量过滤的锚点。新论文通过 embedding 相似度
与知识库对比，过滤掉水文。
"""

from .knowledge_base import KnowledgeBase

__all__ = ["KnowledgeBase"]
