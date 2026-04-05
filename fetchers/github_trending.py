"""
github_trending.py — GitHub Trending 项目抓取器。

抓取 Python / Jupyter Notebook 分类的 Trending 项目，
按 topics 过滤出 AI/ML/NLP 相关项目，并提取关键元数据。
"""

from __future__ import annotations

import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from config import GitHubTrendingConfig


@dataclass
class GitHubProject:
    """GitHub Trending 项目的结构化表示。"""

    name: str            # "owner/repo"
    description: str
    language: str
    stars: int
    forks: int
    today_stars: int
    topics: list[str]
    url: str
    author_url: str
    avatar_url: str
    opened_issues: int
    owner: str
    repo: str
    matched_topics: list[str] = field(default_factory=list)
    priority_score: float = 0.0
    source: str = "github_trending"


class GitHubTrendingFetcher:
    """
    抓取 GitHub Trending 页面，按 topics 过滤 AI/ML 相关项目。

    Topics Filter: machine-learning, deep-learning, nlp,
    large-language-model, transformer, GPT, reinforcement-learning,
    knowledge-graph, vector-database, rag, agent 等。
    """

    BASE_URL = "https://github.com/trending"

    def __init__(self, config: GitHubTrendingConfig | None = None) -> None:
        self.config = config or GitHubTrendingConfig()

    def fetch(self) -> list[GitHubProject]:
        """
        抓取 GitHub Trending 列表。

        Returns
        -------
        list[GitHubProject]，按 priority_score 降序排列
        """
        results: list[GitHubProject] = []

        for language in self.config.languages:
            page_results = self._fetch_page(language=language)
            results.extend(page_results)

        # 过滤：必须有匹配的 topics
        filtered = [p for p in results if p.matched_topics]

        # 过滤：star 数至少 50（去除纯水文）
        filtered = [p for p in filtered if p.stars >= 50]

        # 计算优先级分
        for p in filtered:
            self._score(p)

        filtered.sort(key=lambda x: x.priority_score, reverse=True)
        return filtered

    def _fetch_page(self, language: str) -> list[GitHubProject]:
        """抓取单个语言分类的 Trending 页面。"""
        url = f"{self.BASE_URL}/{language}"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            print(f"[github_trending] ERROR fetching {language}: {exc}")
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        articles = soup.select("article.box-shadow-item")

        projects: list[GitHubProject] = []

        for article in articles:
            try:
                # 解析仓库名
                h2 = article.select_one("h2 a")
                if not h2:
                    continue
                full_name = h2.get_text(strip=True)
                # 格式: "owner / repo" 或 "/owner/repo"
                parts = [p.strip() for p in full_name.split("/")]
                if len(parts) < 2:
                    continue
                owner, repo_name = parts[-2], parts[-1]

                # URL
                href = h2.get("href", "")
                repo_url = f"https://github.com{href}" if href.startswith("/") else href

                # 描述
                desc_elem = article.select_one("p.color-fg-muted")
                description = desc_elem.get_text(strip=True) if desc_elem else ""

                # 编程语言
                lang_elem = article.select_one("span[itemprop='programmingLanguage']")
                lang = lang_elem.get_text(strip=True) if lang_elem else language

                # Stars
                stars_elem = article.select_one("a[href*='/stargazers']")
                stars = self._parse_number(stars_elem.get_text(strip=True)) if stars_elem else 0

                # 今日 star
                today_elem = article.select_one("span.d-inline-block.float-sm-right")
                today_stars = 0
                if today_elem:
                    text = today_elem.get_text(strip=True)
                    today_stars = self._parse_number(text)

                # Issues
                issues_elem = article.select_one("a[href*='/issues']")
                issues = self._parse_number(issues_elem.get_text(strip=True)) if issues_elem else 0

                # Topics
                topic_elems = article.select("a.topic-tag")
                topics = [t.get_text(strip=True) for t in topic_elems]

                # 匹配 topics
                matched = [t for t in topics if t in self.config.topics_filter]

                projects.append(GitHubProject(
                    name=f"{owner}/{repo_name}",
                    description=description,
                    language=lang,
                    stars=stars,
                    forks=0,
                    today_stars=today_stars,
                    topics=topics,
                    url=repo_url,
                    author_url=f"https://github.com/{owner}",
                    avatar_url=f"https://github.com/{owner}.png",
                    opened_issues=issues,
                    owner=owner,
                    repo=repo_name,
                    matched_topics=matched,
                ))

            except Exception as exc:  # noqa: BLE001
                print(f"[github_trending] ERROR parsing article: {exc}")
                continue

        return projects

    @staticmethod
    def _parse_number(text: str) -> int:
        """解析 '1.2k', '340' 等格式的数字。"""
        text = text.strip().upper()
        if text.endswith("K"):
            return int(float(text[:-1]) * 1000)
        if text.endswith("M"):
            return int(float(text[:-1]) * 1_000_000)
        try:
            return int(text)
        except ValueError:
            return 0

    def _score(self, project: GitHubProject) -> None:
        """计算 GitHub 项目优先级分。"""
        score = 0.0

        # 匹配的 topics 数（越多越相关）
        score += len(project.matched_topics) * 0.15

        # Star 数分段打分
        if project.stars >= 5000:
            score += 0.3
        elif project.stars >= 1000:
            score += 0.2
        elif project.stars >= 500:
            score += 0.1

        # 今日新增 star（反映热度）
        if project.today_stars >= 200:
            score += 0.2
        elif project.today_stars >= 50:
            score += 0.1

        # 高价值 topics 加权
        high_value = {
            "large-language-model", "transformer", "GPT",
            "reinforcement-learning", "agent", "rag",
        }
        for t in project.matched_topics:
            if t in high_value:
                score += 0.1

        project.priority_score = min(score, 1.0)
