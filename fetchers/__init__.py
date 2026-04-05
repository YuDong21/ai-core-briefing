"""
fetchers/ — 数据源抓取模块。

每个文件负责一个数据源：
  arxiv.py          ArXiv 最新论文
  github_trending.py GitHub Trending 项目
  tech_blogs.py     技术博客最新文章
"""

from .arxiv import ArxivFetcher
from .github_trending import GitHubTrendingFetcher
from .tech_blogs import TechBlogFetcher

__all__ = ["ArxivFetcher", "GitHubTrendingFetcher", "TechBlogFetcher"]
