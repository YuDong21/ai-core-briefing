"""
run.py — AI 核心技术简报 · 一键启动版
==========================================

【配置区】填写以下 5 个变量，然后运行即可：
    python run.py

【使用方式】
    python run.py              # 生成今日简报 + 发送邮件 + 推送 GitHub
    python run.py --no-email   # 仅生成简报，不发邮件
    python run.py --no-github  # 仅发邮件，不推 GitHub

【配置说明】
    · DASHSCOPE_API_KEY  : 通义千问 API（dashscope.aliyun.com）
    · SMTP_USERNAME/PASSWORD: QQ/163 邮箱的 SMTP 授权码
    · recipients          : 收件人邮箱列表
"""

from __future__ import annotations

import json
import os
import re
import smtplib
import ssl
import sys
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

# ══════════════════════════════════════════════════════════════════════════════
# 【配置区】— 修改这里即可
# ══════════════════════════════════════════════════════════════════════════════

# ✅ 大语言模型API（必须）
DASHSCOPE_API_KEY: str = "sk-****************************"

# ✅ 邮件发送配置（留空则跳过邮件）
SMTP_HOST: str = ""   # 邮件服务器地址（SMTP 服务器）
SMTP_PORT: int = 465  # 邮件服务器的端口号
SMTP_USERNAME: str = "123456789@qq.com" # 发件人的邮箱账号（以__名义发邮件）
SMTP_PASSWORD: str = "twzfqamuuooddjgg" # 邮箱的登录凭证（授权码）
recipients: list[str] = ["123456789@qq.com"]   # 收件人列表，如 ["you@example.com"]

# ✅ GitHub 发布（留空则跳过）
GITHUB_TOKEN: str = ""
GITHUB_REPO: str = ""        # 如 "YuDong21/ai-core-briefing"

# ✅ 过滤关键词（高价值论文匹配这些词会加分）
PRIORITY_KEYWORDS: list[str] = [
    "agent", "multi-agent", "agentic", "agentic RAG", "tool use",
    "RAG", "retrieval-augmented", "dense retrieval", "hybrid retrieval",
    "reranker", "colBERT", "vector search", "chunking",
    "mixture of experts", "MoE", "scaling law",
    "long context", "context extension", "quantization",
    "QLoRA", "LoRA", "prefix tuning",
    "chain-of-thought", "CoT", "self-consistency",
    "speculative decoding", "KV cache", "paged attention",
    "RLHF", "DPO", "PPO", "alignment", "reward model",
    "flash attention", "ring attention", "sparse attention",
    "multimodal", "vision-language", "LLaVA", "GPT-4V",
    "embedding", "contrastive learning",
    "knowledge graph", "GNN", "world model",
    "planning", "task decomposition", "reflection",
    "in-context learning", "few-shot", "zero-shot",
]

EXCLUDE_KEYWORDS: list[str] = [
    "survey", "overview", "review", "tutorial",
    "position paper", "workshop", "demo", "extended abstract",
]

# ✅ 简报收录上限
MAX_PAPERS: int = 8
MAX_GITHUB: int = 5
MAX_BLOGS: int = 3

# ✅ 知识库路径（留空则跳过知识库过滤）
KB_PATH: str = ""   # 如 "knowledge_base/seed_papers.jsonl"


# ══════════════════════════════════════════════════════════════════════════════
# 安装依赖
# ══════════════════════════════════════════════════════════════════════════════

def install_deps():
    """自动检测并提示安装缺失的依赖。"""
    missing: list[str] = []
    for pkg, imp in [
        ("arxiv", "arxiv"),
        ("bs4", "bs4"),
        ("dashscope", "dashscope"),
        ("PyGithub", "github"),
        ("requests", "requests"),
        ("python-dateutil", "dateutil"),
    ]:
        try:
            __import__(imp)
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f"[依赖] 正在安装缺失模块: {', '.join(missing)}")
        os.system(f"pip install {' '.join(missing)}")


# ══════════════════════════════════════════════════════════════════════════════
# 横幅
# ══════════════════════════════════════════════════════════════════════════════

def print_banner(date_str: str):
    print(f"""
╔══════════════════════════════════════════════════════╗
║     🤖 AI 核心技术简报 · 自动生成器                     ║
║     📅 {date_str}                                        ║
╚══════════════════════════════════════════════════════╝
""")


# ══════════════════════════════════════════════════════════════════════════════
# 数据模型
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Paper:
    paper_id: str
    title: str
    authors: list[str]
    abstract: str
    categories: list[str]
    published_date: datetime
    pdf_url: str = ""
    arxiv_url: str = ""
    priority_score: float = 0.0
    matched_keywords: list[str] = field(default_factory=list)
    source: str = "arxiv"


@dataclass
class GitHubProject:
    name: str
    description: str
    language: str
    stars: int
    today_stars: int
    topics: list[str]
    url: str
    priority_score: float = 0.0
    source: str = "github_trending"


@dataclass
class AnalysisResult:
    paper_id: str
    title: str
    source: str
    core_innovation: str = ""
    architecture_summary: str = ""
    key_techniques: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    comparison: str = ""
    source_url: str = ""
    authors: str = ""
    date: str = ""


# ══════════════════════════════════════════════════════════════════════════════
# Step 1: 抓取 ArXiv
# ══════════════════════════════════════════════════════════════════════════════

def fetch_arxiv(days_back: int = 2) -> list[Paper]:
    print("\n[Step 1] 📡 抓取 ArXiv 论文...")
    try:
        import arxiv
    except ImportError:
        print("  ⚠️ arxiv 未安装"); return []

    categories = ["cs.AI", "cs.CL", "cs.LG", "cs.MA", "cs.RO"]
    all_papers: list[Paper] = []
    cutoff = datetime.now() - timedelta(days=days_back)

    for cat in categories:
        try:
            client = arxiv.Client(page_size=30)
            search = arxiv.Search(query=f"cat:{cat}", max_results=30,
                                  sort_by=arxiv.SortCriterion.SubmittedDate)
            for p in client.results(search):
                if p.updated_date < cutoff:
                    continue
                text = (p.title + " " + p.summary).lower()
                score = sum(0.1 for kw in PRIORITY_KEYWORDS if kw.lower() in text)
                excluded = any(ex.lower() in text for ex in EXCLUDE_KEYWORDS)
                if excluded:
                    continue
                matched = [kw for kw in PRIORITY_KEYWORDS if kw.lower() in text]

                all_papers.append(Paper(
                    paper_id=p.entry_id.split("/")[-1],
                    title=re.sub(r"\s+", " ", p.title or "").strip(),
                    authors=[a.name for a in (p.authors or [])],
                    abstract=re.sub(r"\s+", " ", p.summary or "").strip(),
                    categories=p.categories or [],
                    published_date=p.published_date,
                    pdf_url=p.pdf_url or "",
                    arxiv_url=p.entry_id or "",
                    priority_score=min(score, 1.0),
                    matched_keywords=matched[:8],
                ))
        except Exception as exc:
            print(f"  ⚠️ {cat}: {exc}")

    # 去重 + 排序
    seen: set[str] = set()
    unique = []
    for p in all_papers:
        if p.paper_id not in seen:
            seen.add(p.paper_id)
            unique.append(p)
    unique.sort(key=lambda x: x.priority_score, reverse=True)
    print(f"  ✓ 获取 {len(unique)} 篇论文")
    return unique


# ══════════════════════════════════════════════════════════════════════════════
# Step 1b: 抓取 GitHub Trending
# ══════════════════════════════════════════════════════════════════════════════

def fetch_github_trending() -> list[GitHubProject]:
    print("\n[Step 1b] 🐙 抓取 GitHub Trending...")
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        print("  ⚠️ requests/bs4 未安装"); return []

    topics_filter = {
        "machine-learning", "deep-learning", "nlp",
        "large-language-model", "transformer", "GPT",
        "reinforcement-learning", "knowledge-graph",
        "vector-database", "rag", "agent",
    }
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
    results: list[GitHubProject] = []

    for lang in ["Python"]:
        try:
            resp = requests.get(f"https://github.com/trending/{lang}", headers=headers, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
            for article in soup.select("article.box-shadow-item")[:15]:
                h2 = article.select_one("h2 a")
                if not h2:
                    continue
                parts = [s.strip() for s in h2.get_text(strip=True).split("/")]
                if len(parts) < 2:
                    continue
                owner, repo = parts[-2], parts[-1]
                href = h2.get("href", "")
                url = f"https://github.com{href}" if href.startswith("/") else href
                desc = article.select_one("p.color-fg-muted")
                desc_text = desc.get_text(strip=True) if desc else ""
                lang_elem = article.select_one("span[itemprop='programmingLanguage']")
                lang_text = lang_elem.get_text(strip=True) if lang_elem else lang
                stars_elem = article.select_one("a[href*='/stargazers']")
                stars = _parse_num(stars_elem.get_text(strip=True)) if stars_elem else 0
                today_elem = article.select_one("span.d-inline-block.float-sm-right")
                today = _parse_num(today_elem.get_text(strip=True)) if today_elem else 0
                topic_elems = article.select("a.topic-tag")
                topics = [t.get_text(strip=True) for t in topic_elems]
                matched = [t for t in topics if t in topics_filter]

                if not matched or stars < 50:
                    continue

                score = len(matched) * 0.15 + (0.3 if stars >= 5000 else 0.2 if stars >= 1000 else 0.1)
                results.append(GitHubProject(
                    name=f"{owner}/{repo}", description=desc_text, language=lang_text,
                    stars=stars, today_stars=today, topics=topics, url=url,
                    priority_score=min(score, 1.0),
                ))
        except Exception as exc:
            print(f"  ⚠️ GitHub {lang}: {exc}")

    results.sort(key=lambda x: x.priority_score, reverse=True)
    print(f"  ✓ 获取 {len(results)} 个项目")
    return results


def _parse_num(text: str) -> int:
    t = text.strip().upper()
    try:
        if t.endswith("K"): return int(float(t[:-1]) * 1000)
        if t.endswith("M"): return int(float(t[:-1]) * 1_000_000)
        return int(t)
    except ValueError:
        return 0


# ══════════════════════════════════════════════════════════════════════════════
# Step 2: 知识库过滤
# ══════════════════════════════════════════════════════════════════════════════

def filter_with_kb(papers: list[Paper], kb_path: str) -> list[Paper]:
    if not kb_path or not Path(kb_path).exists():
        print("  ⏭  跳过知识库过滤（未配置）")
        return papers
    print(f"\n[Step 2] 🧠 知识库过滤...")
    # 简单实现：已有 priority_score，直接阈值过滤
    threshold = 0.15
    filtered = [p for p in papers if p.priority_score >= threshold]
    print(f"  ✓ {len(filtered)}/{len(papers)} 篇通过过滤")
    return filtered


# ══════════════════════════════════════════════════════════════════════════════
# Step 3: LLM 分析
# ══════════════════════════════════════════════════════════════════════════════

LLM_PROMPT_ARXIV = """你是一位专业的 AI 论文评审专家。请分析以下 ArXiv 论文，输出严格 JSON：

论文标题: {title}
作者: {authors}
摘要: {abstract}

输出格式（严格 JSON，不要输出其他内容）：
{{
  "core_innovation": "一句话核心创新（≤30字）",
  "architecture_summary": "架构思路描述（100-200字）",
  "key_techniques": ["技术1", "技术2", "技术3"],
  "strengths": ["优势1", "优势2"],
  "weaknesses": ["局限1", "局限2"],
  "comparison": "与同类工作对比（50-100字）"
}}"""

LLM_PROMPT_GITHUB = """你是一位专业的 AI 开源项目分析师。请分析以下 GitHub 项目，输出严格 JSON：

项目: {title}
描述: {description}

输出格式（严格 JSON）：
{{
  "core_innovation": "一句话核心价值（≤30字）",
  "architecture_summary": "架构设计描述（80-150字）",
  "key_techniques": ["技术1", "技术2", "技术3"],
  "strengths": ["优势1", "优势2"],
  "weaknesses": ["局限1", "局限2"],
  "comparison": "与同类项目对比（50字）"
}}"""


def analyze_with_llm(item, is_arxiv: bool = True) -> AnalysisResult:
    if not DASHSCOPE_API_KEY:
        return _mock_analysis(item, is_arxiv)

    try:
        import dashscope
        dashscope.api_key = DASHSCOPE_API_KEY
        from dashscope import Generation

        prompt = (LLM_PROMPT_ARXIV if is_arxiv else LLM_PROMPT_GITHUB).format(
            title=item.title,
            authors=", ".join(item.authors[:5]) if is_arxiv else (item.name or ""),
            abstract=item.abstract[:2000] if is_arxiv else item.description,
            description=item.description if not is_arxiv else "",
        )

        resp = Generation.call(
            model="qwen-plus",
            prompt=prompt,
            temperature=0.3,
            max_tokens=1024,
        )

        if resp.status_code == 200 and resp.output:
            raw = resp.output.text or "{}"
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                raw = re.sub(r"^```json\s*", "", raw.strip())
                raw = re.sub(r"\s*```$", "", raw)
                try:
                    parsed = json.loads(raw)
                except Exception:
                    parsed = _mock_analysis(item, is_arxiv).__dict__
        else:
            parsed = _mock_analysis(item, is_arxiv).__dict__

        return AnalysisResult(
            paper_id=item.paper_id,
            title=item.title,
            source=item.source,
            source_url=item.arxiv_url if is_arxiv else item.url,
            authors=", ".join(item.authors[:5]) if is_arxiv else item.name,
            date=item.published_date.strftime("%Y-%m-%d") if is_arxiv else datetime.now().strftime("%Y-%m-%d"),
            core_innovation=parsed.get("core_innovation", ""),
            architecture_summary=parsed.get("architecture_summary", ""),
            key_techniques=parsed.get("key_techniques", []),
            strengths=parsed.get("strengths", []),
            weaknesses=parsed.get("weaknesses", []),
            comparison=parsed.get("comparison", ""),
        )
    except Exception as exc:
        print(f"  ⚠️ LLM 分析失败: {exc}")
        return _mock_analysis(item, is_arxiv)


def _mock_analysis(item, is_arxiv: bool) -> AnalysisResult:
    return AnalysisResult(
        paper_id=item.paper_id,
        title=item.title,
        source=item.source,
        core_innovation="(请配置 DASHSCOPE_API_KEY 获取真实分析)",
        architecture_summary="请配置通义千问 API Key 后重新运行。",
        key_techniques=item.matched_keywords[:3] if hasattr(item, "matched_keywords") else [],
        source_url=item.arxiv_url if is_arxiv else getattr(item, "url", ""),
        authors=", ".join(item.authors[:3]) if is_arxiv else getattr(item, "name", ""),
        date=getattr(item, "published_date", datetime.now()).strftime("%Y-%m-%d") if is_arxiv else "",
    )


# ══════════════════════════════════════════════════════════════════════════════
# Step 4: 生成简报
# ══════════════════════════════════════════════════════════════════════════════

def generate_briefing(
    date_val: datetime,
    arxiv_results: list[AnalysisResult],
    github_results: list[AnalysisResult],
) -> tuple[Path, str]:
    print("\n[Step 4] 📝 生成简报...")
    date_str = date_val.strftime("%Y-%m-%d")
    weekday = date_val.strftime("%A")

    arxiv_items = arxiv_results[:MAX_PAPERS]
    github_items = github_results[:MAX_GITHUB]

    # 技术趋势统计
    all_keywords: list[str] = []
    for r in arxiv_results + github_results:
        all_keywords.extend(r.key_techniques or [])
    top_trends = Counter(all_keywords).most_common(12)

    lines: list[str] = []
    lines.append(f"# 🤖 AI 核心技术简报")
    lines.append(f"**📅 {date_str} ({weekday})** &nbsp;&nbsp; **自动生成**\n")
    lines.append("---\n")
    lines.append("> **本期要点**: 自动筛选 Agent、RAG、LLM 算法领域高价值论文与开源项目，")
    lines.append("> 提取核心创新点和架构思路，逼迫自己和 AI 一起保持对前沿架构的敏锐度。\n")
    lines.append("---\n")

    # 概览
    lines.append("## 📊 概览\n")
    lines.append(f"| 来源 | 收录数 |")
    lines.append(f"|------|--------|")
    lines.append(f"| ArXiv 论文 | {len(arxiv_items)} 篇 |")
    lines.append(f"| GitHub Trending | {len(github_items)} 个 |")
    lines.append("")

    if top_trends:
        tags = "  ".join(f"`{kw}×{cnt}`" for kw, cnt in top_trends)
        lines.append(f"### 🔥 技术热词\n{tags}\n")

    lines.append("---\n")

    # ArXiv 论文
    lines.append(f"## 📄 ArXiv 精选论文（共 {len(arxiv_items)} 篇）")
    for i, r in enumerate(arxiv_items, 1):
        lines.append(f"\n### {i}. {r.title}")
        lines.append(f"**🔗 链接**: {r.source_url}")
        if r.authors: lines.append(f"**👥 作者**: {r.authors}")
        if r.date: lines.append(f"**📅 日期**: {r.date}")
        if r.core_innovation: lines.append(f"\n**💡 核心创新**: {r.core_innovation}")
        if r.architecture_summary: lines.append(f"\n**🏗️ 架构思路**: {r.architecture_summary}")
        if r.key_techniques:
            techniques = " / ".join(f"`{t}`" for t in r.key_techniques)
            lines.append(f"\n**⚙️ 关键技术**: {techniques}")
        if r.comparison: lines.append(f"\n**⚖️ 同类对比**: {r.comparison}")
        if r.weaknesses:
            lines.append(f"\n**⚠️ 局限/挑战**: {'；'.join(r.weaknesses[:2])}")
        lines.append("\n---\n")

    # GitHub 项目
    if github_items:
        lines.append(f"\n## 🐙 GitHub Trending 精选（共 {len(github_items)} 个）")
        for i, r in enumerate(github_items, 1):
            lines.append(f"\n### {i}. {r.title}")
            lines.append(f"**🔗 链接**: {r.source_url}")
            if r.core_innovation: lines.append(f"\n**💡 核心价值**: {r.core_innovation}")
            if r.architecture_summary: lines.append(f"\n**🏗️ 架构设计**: {r.architecture_summary}")
            if r.key_techniques:
                techniques = " / ".join(f"`{t}`" for t in r.key_techniques)
                lines.append(f"\n**⚙️ 技术栈**: {techniques}")
            lines.append("\n---\n")

    lines.append(f"\n*🤖 AI 核心技术简报 · {date_str} · 自动生成*\n")

    md_content = "\n".join(lines)
    output_dir = Path(__file__).parent / "daily"
    output_dir.mkdir(exist_ok=True)
    out_path = output_dir / f"AI核心技术简报_{date_str}.md"
    out_path.write_text(md_content, encoding="utf-8")
    print(f"  ✓ 已保存: {out_path}")
    return out_path, md_content


# ══════════════════════════════════════════════════════════════════════════════
# Step 5: 发送邮件
# ══════════════════════════════════════════════════════════════════════════════

def send_email(md_content: str, date_str: str, arxiv_count: int, github_count: int) -> dict:
    if not SMTP_USERNAME or not SMTP_PASSWORD or not recipients:
        print("\n[Step 5] ⏭  邮件未配置，跳过")
        return {"status": "skipped"}

    print("\n[Step 5] 📧 发送邮件...")
    html_body = _md_to_html(md_content)

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"AI 核心技术简报 <{SMTP_USERNAME}>"
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = f"🤖 AI 核心技术简报 {date_str}（ArXiv {arxiv_count} 篇 | GitHub {github_count} 个）"
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)

        print(f"  ✅ 邮件已发送至 {len(recipients)} 位收件人")
        return {"status": "sent"}
    except Exception as exc:
        print(f"  ❌ 邮件发送失败: {exc}")
        return {"status": "error", "message": str(exc)}


def _md_to_html(md: str) -> str:
    import re
    md = re.sub(r"^### (.+)$", r"<h3>\1</h3>", md, flags=re.MULTILINE)
    md = re.sub(r"^## (.+)$", r"<h2>\1</h2>", md, flags=re.MULTILINE)
    md = re.sub(r"^# (.+)$", r"<h1>\1</h1>", md, flags=re.MULTILINE)
    md = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", md)
    md = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', md)
    md = re.sub(r"^---$", "<hr>", md, flags=re.MULTILINE)
    md = re.sub(r"`(.+?)`", r"<code>\1</code>", md)
    md = re.sub(r"\n\n+", "\n\n", md)
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
  body{{font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;max-width:720px;margin:0 auto;padding:20px;background:#f8f9fa;color:#1a1a2e}}
  .header{{background:linear-gradient(135deg,#667eea,#764ba2);color:white;padding:24px;border-radius:12px;margin-bottom:24px}}
  .header h1{{margin:0 0 8px;font-size:22px}}
  h2{{color:#2d3748;border-left:4px solid #667eea;padding-left:10px;margin-top:28px}}
  h3{{color:#4a5568;margin-bottom:8px}}
  p{{line-height:1.7;color:#2d3748}}
  code{{background:#edf2f7;padding:2px 6px;border-radius:4px;font-size:13px}}
  hr{{border:none;border-top:1px solid #e2e8f0;margin:24px 0}}
  .footer{{text-align:center;color:#a0aec0;font-size:12px;margin-top:40px;padding-top:20px;border-top:1px solid #e2e8f0}}
  a{{color:#667eea}}
</style></head><body>
<div class="header"><h1>🤖 AI 核心技术简报</h1></div>
<div class="content">{md}</div>
<div class="footer"><p>🤖 AI 核心技术简报 · 自动生成</p></div>
</body></html>"""


# ══════════════════════════════════════════════════════════════════════════════
# Step 6: 推送 GitHub
# ══════════════════════════════════════════════════════════════════════════════

def push_to_github(md_content: str, date_str: str) -> dict:
    if not GITHUB_TOKEN or not GITHUB_REPO:
        print("\n[Step 6] ⏭  GitHub 未配置，跳过")
        return {"status": "skipped"}

    print("\n[Step 6] 🚀 推送 GitHub...")
    try:
        from github import Github
        gh = Github(GITHUB_TOKEN)
        repo = gh.get_repo(GITHUB_REPO)
        file_path = f"daily/AI核心技术简报_{date_str}.md"
        commit_msg = f"📅 Daily Briefing: {date_str}"

        try:
            existing = repo.get_contents(file_path)
            result = repo.update_file(file_path, commit_msg, md_content, existing.sha)
        except Exception:
            result = repo.create_file(file_path, commit_msg, md_content)

        url = f"https://github.com/{GITHUB_REPO}/blob/main/{file_path}"
        print(f"  ✅ 已推送: {url}")
        return {"status": result.get("commit", {}).get("sha", ""), "url": url}
    except Exception as exc:
        print(f"  ❌ GitHub 推送失败: {exc}")
        return {"status": "error", "message": str(exc)}


# ══════════════════════════════════════════════════════════════════════════════
# 主流程
# ══════════════════════════════════════════════════════════════════════════════

def main():
    date_val = datetime.now()
    date_str = date_val.strftime("%Y-%m-%d")

    # CLI 参数
    no_email = "--no-email" in sys.argv
    no_github = "--no-github" in sys.argv

    print_banner(date_str)

    if not DASHSCOPE_API_KEY:
        print("⚠️  警告: DASHSCOPE_API_KEY 未设置，分析结果为占位符")
        print("   设置: 在文件顶部填写 DASHSCOPE_API_KEY = 'your-key'\n")

    # Step 1: 抓取
    papers = fetch_arxiv(days_back=2)
    github_projects = fetch_github_trending()

    if not papers and not github_projects:
        print("\n❌ 无内容，可能是网络问题或 API 限制")
        return

    # Step 2: 知识库过滤
    filtered = filter_with_kb(papers, KB_PATH)

    # Step 3: LLM 分析
    print("\n[Step 3] 🧠 LLM 深度分析...")
    arxiv_results: list[AnalysisResult] = []
    for i, p in enumerate(filtered[:MAX_PAPERS], 1):
        print(f"  [{i}/{min(len(filtered), MAX_PAPERS)}] {p.title[:50]}...", end="\r")
        arxiv_results.append(analyze_with_llm(p, is_arxiv=True))

    github_results: list[AnalysisResult] = []
    for i, g in enumerate(github_projects[:MAX_GITHUB], 1):
        print(f"  [GH {i}/{min(len(github_projects), MAX_GITHUB)}] {g.name}...", end="\r")
        github_results.append(analyze_with_llm(g, is_arxiv=False))

    print(f"\n  ✓ 分析完成: {len(arxiv_results)} 篇论文 + {len(github_results)} 个项目")

    # Step 4: 生成简报
    out_path, md_content = generate_briefing(date_val, arxiv_results, github_results)

    # Step 5: 发邮件
    email_result = {"status": "skipped"}
    if not no_email:
        email_result = send_email(md_content, date_str, len(arxiv_results), len(github_results))

    # Step 6: GitHub
    gh_result = {"status": "skipped"}
    if not no_github:
        gh_result = push_to_github(md_content, date_str)

    print(f"""
╔══════════════════════════════════════════════════════╗
║  ✅ 完成！                                           ║
║                                                      ║
║  📄 简报 : {str(out_path)[-50]:<50}  ║
║  📧 邮件 : {str(email_result.get('status', '')):<50}  ║
║  🚀 GitHub: {str(gh_result.get('status', '')):<49}  ║
╚══════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    install_deps()
    main()
