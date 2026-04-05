"""
main.py — 每日《AI核心技术简报》主入口。

每天定时运行，流程：
  1. 抓取 ArXiv / GitHub Trending / Tech Blogs
  2. 知识库过滤（水文剔除）
  3. LLM 提取核心创新点 + 架构思路
  4. 生成 Markdown 简报
  5. 自动发布到 GitHub

Usage
-----
    # 本地手动运行
    python main.py

    # GitHub Actions（自动，每天 UTC 0 点 = 北京时间 8 点）
    # 参见 .github/workflows/daily.yml
"""

from __future__ import annotations

import os
import sys
from datetime import datetime

# Setup path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from config import get_config, ArxivConfig, GitHubTrendingConfig, TechBlogConfig, LLMConfig, BriefingConfig
from fetchers import ArxivFetcher, GitHubTrendingFetcher, TechBlogFetcher
from knowledge_base import KnowledgeBase
from analyzers import PaperAnalyzer
from briefing_generator import BriefingGenerator
from publish import publish


# ---------------------------------------------------------------------------
# 打印横幅
# ---------------------------------------------------------------------------

def print_banner(date_str: str) -> None:
    print(f"""
╔══════════════════════════════════════════════════════╗
║     🤖 AI 核心技术简报 · 自动生成器                     ║
║     📅 {date_str}                                        ║
╚══════════════════════════════════════════════════════╝
""")


# ---------------------------------------------------------------------------
# Step 1: 抓取数据
# ---------------------------------------------------------------------------

def step_fetch(cfg: dict) -> tuple:
    """
    抓取三大数据源。
    Returns: (arxiv_papers, github_projects, blog_articles)
    """
    print("\n[Step 1/5] 📡 抓取数据源...")

    # ArXiv
    arxiv_cfg = cfg["arxiv"]
    arxiv_fetcher = ArxivFetcher(arxiv_cfg)
    arxiv_papers = arxiv_fetcher.fetch(days_back=2)
    print(f"  ArXiv:       {len(arxiv_papers)} 篇论文")

    # GitHub Trending
    gh_cfg = cfg["github_trending"]
    gh_fetcher = GitHubTrendingFetcher(gh_cfg)
    github_projects = gh_fetcher.fetch()
    print(f"  GitHub:      {len(github_projects)} 个项目（过滤后）")

    # Tech Blogs
    blog_cfg = cfg["tech_blogs"]
    blog_fetcher = TechBlogFetcher(blog_cfg)
    blog_articles = blog_fetcher.fetch()
    print(f"  Tech Blogs: {len(blog_articles)} 篇")

    return arxiv_papers, github_projects, blog_articles


# ---------------------------------------------------------------------------
# Step 2: 知识库过滤
# ---------------------------------------------------------------------------

def step_filter(
    arxiv_papers: list,
    github_projects: list,
    blog_articles: list,
    cfg: dict,
) -> tuple:
    """
    用知识库过滤低质量/水文内容。
    """
    print("\n[Step 2/5] 🧠 知识库过滤...")

    kb_cfg = cfg["knowledge_base"]
    kb = KnowledgeBase(kb_cfg)
    kb.load()

    def filter_item(item, source):
        text = f"{item.title} {getattr(item, 'abstract', '') or getattr(item, 'description', '')}"
        keyword_score = getattr(item, "priority_score", 0.0)
        return kb.is_quality(text, keyword_score)

    arxiv_filtered = [p for p in arxiv_papers if filter_item(p, "arxiv")]
    gh_filtered = [p for p in github_projects if filter_item(p, "github")]
    blog_filtered = [p for p in blog_articles if filter_item(p, "blog")]

    print(f"  ArXiv:       {len(arxiv_filtered)}/{len(arxiv_papers)} 篇保留")
    print(f"  GitHub:      {len(gh_filtered)}/{len(github_projects)} 个保留")
    print(f"  Tech Blogs:  {len(blog_filtered)}/{len(blog_articles)} 篇保留")

    return arxiv_filtered, gh_filtered, blog_filtered


# ---------------------------------------------------------------------------
# Step 3: LLM 分析
# ---------------------------------------------------------------------------

def step_analyze(
    arxiv_items: list,
    github_items: list,
    blog_items: list,
    cfg: dict,
) -> tuple:
    """
    用 LLM 提取每篇论文/项目的核心创新点和架构思路。
    """
    print("\n[Step 3/5] 🧠 LLM 深度分析...")

    llm_cfg = cfg["llm"]
    analyzer = PaperAnalyzer(llm_cfg)

    arxiv_results: list = []
    github_results: list = []
    blog_results: list = []

    # ArXiv 分析（有完整 abstract）
    for i, paper in enumerate(arxiv_items, 1):
        print(f"  [ArXiv] {i}/{len(arxiv_items)}: {paper.title[:50]}...", end="\r")
        result = analyzer.analyze_arxiv(
            paper_id=paper.paper_id,
            title=paper.title,
            abstract=paper.abstract,
            authors=paper.authors,
            date=paper.updated_date.strftime("%Y-%m-%d"),
            url=paper.arxiv_url,
        )
        arxiv_results.append(result)

    print(f"  ArXiv:       {len(arxiv_results)} 篇分析完成")

    # GitHub 分析
    for i, proj in enumerate(github_items, 1):
        print(f"  [GitHub] {i}/{len(github_items)}: {proj.name}...", end="\r")
        result = analyzer.analyze_lightweight(
            paper_id=proj.name.replace("/", "_"),
            title=proj.name,
            description=proj.description,
            date=datetime.now().strftime("%Y-%m-%d"),
            url=proj.url,
            authors=proj.owner,
        )
        github_results.append(result)

    print(f"  GitHub:      {len(github_results)} 个分析完成")

    # 博客分析
    for i, article in enumerate(blog_items, 1):
        print(f"  [Blog] {i}/{len(blog_items)}: {article.title[:50]}...", end="\r")
        result = analyzer.analyze_lightweight(
            paper_id=article.url.split("/")[-1],
            title=article.title,
            description="",
            date=article.published_date.strftime("%Y-%m-%d") if article.published_date else "",
            url=article.url,
            authors=article.source_name,
        )
        blog_results.append(result)

    print(f"  Tech Blogs: {len(blog_results)} 篇分析完成")

    return arxiv_results, github_results, blog_results


# ---------------------------------------------------------------------------
# Step 4: 生成简报
# ---------------------------------------------------------------------------

def step_generate(
    date_val: datetime,
    arxiv_results: list,
    github_results: list,
    blog_results: list,
    cfg: dict,
) -> tuple:
    """生成 Markdown 简报。"""
    print("\n[Step 4/5] 📝 生成简报...")

    briefing_cfg = cfg["briefing"]
    generator = BriefingGenerator(briefing_cfg)

    output_dir = os.path.join(PROJECT_ROOT, "daily")
    os.makedirs(output_dir, exist_ok=True)

    path, content = generator.generate(
        date=date_val,
        arxiv_results=arxiv_results,
        github_results=github_results,
        blog_results=blog_results,
        output_dir=output_dir,
    )

    print(f"  简报已生成: {path}")
    return path, content


# ---------------------------------------------------------------------------
# Step 5: 发布到 GitHub
# ---------------------------------------------------------------------------

def step_publish(
    markdown_content: str,
    date_str: str,
) -> dict:
    """发布到 GitHub。"""
    print("\n[Step 5/5] 🚀 发布到 GitHub...")

    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        print("  ⚠️  GITHUB_TOKEN 未设置，跳过发布（本地保存）")
        return {"status": "skipped", "reason": "No GITHUB_TOKEN"}

    daily_dir = os.path.join(PROJECT_ROOT, "daily")
    result = publish(markdown_content, date_str, daily_dir)

    if result.get("status") == "skipped":
        print(f"  ⚠️  {result.get('reason')}")
    else:
        print(f"  ✅ {result['status']}: {result.get('url', '')}")

    return result


# ---------------------------------------------------------------------------
# Step 6: 发送邮件
# ---------------------------------------------------------------------------

def step_send_email(
    markdown_content: str,
    date_str: str,
    arxiv_count: int = 0,
    github_count: int = 0,
    blog_count: int = 0,
    github_url: str = "",
) -> dict:
    """发送邮件。"""
    from notifier import EmailNotifier

    print("\n[Step 6/6] 📧 发送邮件...")

    notifier = EmailNotifier()
    result = notifier.send_briefing_with_summary(
        markdown_content=markdown_content,
        date_str=date_str,
        arxiv_count=arxiv_count,
        github_count=github_count,
        blog_count=blog_count,
        github_url=github_url,
    )

    if result.get("status") == "skipped":
        print(f"  ⚠️  {result.get('message', '未配置邮件发送')}")
        print("   开启邮件: 设置 SMTP_USERNAME / SMTP_PASSWORD 或 SENDGRID_API_KEY")
    elif result.get("status") == "sent":
        print(f"  ✅ 邮件已发送 ({result['method']}): {result['message']}")
    else:
        print(f"  ❌ 邮件发送失败: {result.get('message', '未知错误')}")

    return result


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main() -> None:
    date_val = datetime.now()
    date_str = date_val.strftime("%Y-%m-%d")

    print_banner(date_str)

    cfg = get_config()

    # 检查 API Key
    if not cfg["llm"].api_key:
        print("⚠️  WARNING: DASHSCOPE_API_KEY 未设置，LLM 分析将输出 mock 结果")
        print("   设置方式: export DASHSCOPE_API_KEY='your-key'")

    # 1. 抓取
    arxiv_papers, github_projects, blog_articles = step_fetch(cfg)

    if not arxiv_papers and not github_projects and not blog_articles:
        print("\n❌ 所有数据源均无内容，可能遭遇反爬或网络问题，跳过。")
        sys.exit(0)

    # 2. 过滤
    arxiv_filtered, gh_filtered, blog_filtered = step_filter(
        arxiv_papers, github_projects, blog_articles, cfg
    )

    # 3. 分析
    arxiv_results, github_results, blog_results = step_analyze(
        arxiv_filtered, gh_filtered, blog_filtered, cfg
    )

    # 4. 生成
    path, content = step_generate(
        date_val, arxiv_results, github_results, blog_results, cfg
    )

    # 5. 发布到 GitHub
    pub_result = step_publish(content, date_str)
    github_url = pub_result.get("url", "")

    # 6. 发送邮件
    email_result = step_send_email(
        markdown_content=content,
        date_str=date_str,
        arxiv_count=len(arxiv_results),
        github_count=len(github_results),
        blog_count=len(blog_results),
        github_url=github_url,
    )

    # 最终输出
    print(f"""
╔══════════════════════════════════════════════════════╗
║  ✅ 简报生成完成！                                    ║
║                                                      ║
║  📄 本地文件 : {str(path)[-48]:<48}  ║
║  🚀 GitHub   : {str(pub_result.get('status', 'unknown')):<48}  ║
║  📧 邮件     : {str(email_result.get('status', 'unknown')):<48}  ║
╚══════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    main()
