"""
knowledge_base.py — 个人知识库（质量过滤器）。

功能：
  1. 加载 seed_papers.jsonl（手工维护的高价值论文/项目列表）
  2. 用 BGE-M3 将 seed 转为 embedding
  3. 新论文/项目通过 embedding 相似度过滤

原理：新论文与知识库中高价值论文 embedding 相似度低 →
      说明与已有知识体系差异大（可能是新方向）或水文（缺乏实质贡献）
      综合 score < threshold → 过滤
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from config import KnowledgeBaseConfig


class KnowledgeBase:
    """
    轻量知识库：seed paper + BGE-M3 embedding + 余弦相似度。

    不依赖外部向量数据库，直接用 numpy 计算。
    """

    def __init__(
        self,
        config: KnowledgeBaseConfig | None = None,
        embedder: Any = None,
    ) -> None:
        self.config = config or KnowledgeBaseConfig()
        self.embedder = embedder
        self._seed_embeddings: list[list[float]] = []
        self._seed_texts: list[str] = []
        self._loaded = False

    # -------------------------------------------------------------------------
    # 加载 & 初始化
    # -------------------------------------------------------------------------

    def load(self) -> None:
        """加载 seed_papers.jsonl 并生成 embedding。"""
        if self._loaded:
            return

        seed_path = self.config.seed_papers_path
        if not seed_path.exists():
            print(f"[kb] WARNING: seed_papers.jsonl not found at {seed_path}")
            print(f"[kb]   Create it with high-quality paper/project references.")
            self._loaded = True
            return

        print(f"[kb] Loading knowledge base from {seed_path}")
        self._seed_texts = []
        self._seed_embeddings = []

        with open(seed_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                    text = self._item_to_text(item)
                    self._seed_texts.append(text)
                except json.JSONDecodeError:
                    continue

        if self._seed_texts:
            self._embed_seed()

        print(f"[kb] Knowledge base loaded: {len(self._seed_embeddings)} entries")
        self._loaded = True

    def _item_to_text(self, item: dict) -> str:
        """将 JSON item 转换为 embedding 用文本。"""
        parts = []
        parts.append(item.get("title", ""))
        parts.append(item.get("abstract", "") or item.get("description", ""))
        parts.append(" ".join(item.get("keywords", [])))
        return " | ".join(p for p in parts if p)

    def _embed_seed(self) -> None:
        """用 BGE-M3 将 seed texts 转为 embeddings。"""
        if not self._seed_texts:
            return

        if self.embedder is None:
            try:
                from FlagEmbedding import BGEM3FlagModel
                self.embedder = BGEM3FlagModel(
                    "BAAI/bge-m3",
                    model_kwargs={"device": "cpu"},
                    encode_kwargs={"batch_size": 8, "max_length": 512},
                    use_fp16=False,
                )
            except ImportError:
                print("[kb] ERROR: FlagEmbedding not installed. Run: pip install FlagEmbedding")
                return

        print(f"[kb] Generating embeddings for {len(self._seed_texts)} seed entries...")
        results = self.embedder.encode(self._seed_texts)
        self._seed_embeddings = [v.tolist() for v in results["dense_vecs"]]

    # -------------------------------------------------------------------------
    # 相似度计算
    # -------------------------------------------------------------------------

    def score(self, text: str) -> float:
        """
        计算文本与知识库的相似度分（0-1）。

        1. 将 text 用 BGE-M3 embed
        2. 与所有 seed embedding 计算余弦相似度
        3. 取 max 作为最终分
        """
        if not self._seed_embeddings or not text:
            return 0.5  # 无知识库时默认中等分

        if self.embedder is None:
            return 0.5

        try:
            emb = self.embedder.encode([text])
            vec = emb["dense_vecs"][0].tolist()
        except Exception:  # noqa: BLE001
            return 0.5

        # 余弦相似度
        import numpy as np
        vec_a = np.array(vec)
        best_sim = 0.0
        for seed_vec in self._seed_embeddings:
            vec_b = np.array(seed_vec)
            sim = np.dot(vec_a, vec_b) / (np.linalg.norm(vec_a) * np.linalg.norm(vec_b) + 1e-8)
            best_sim = max(best_sim, float(sim))

        return float(best_sim)

    def is_quality(self, text: str, keyword_score: float = 0.0) -> bool:
        """
        综合判断是否为高质量内容。

        Parameters
        ----------
        text           : 待检测文本（title + abstract）
        keyword_score  : 关键词匹配分（0-1，来自 fetcher）

        Returns
        -------
        True = 高质量，值得收录
        """
        if not self._seed_embeddings:
            # 无知识库时，用关键词分判断
            return keyword_score >= 0.3

        kb_sim = self.score(text)
        # 综合分 = 0.4 * 知识库相似度 + 0.6 * 关键词分
        combined = 0.4 * kb_sim + 0.6 * keyword_score

        return combined >= self.config.min_quality_score

    def get_similar_seed(self, text: str, top_k: int = 3) -> list[tuple[str, float]]:
        """返回与 text 最相似的 top_k 个 seed 论文。"""
        if not self._seed_embeddings or not text:
            return []

        if self.embedder is None:
            return []

        try:
            emb = self.embedder.encode([text])
            vec = emb["dense_vecs"][0].tolist()
        except Exception:  # noqa: BLE001
            return []

        import numpy as np
        vec_a = np.array(vec)
        sims: list[tuple[str, float]] = []

        for i, seed_vec in enumerate(self._seed_embeddings):
            vec_b = np.array(seed_vec)
            sim = float(np.dot(vec_a, vec_b) / (np.linalg.norm(vec_a) * np.linalg.norm(vec_b) + 1e-8))
            sims.append((self._seed_texts[i], sim))

        sims.sort(key=lambda x: x[1], reverse=True)
        return sims[:top_k]
