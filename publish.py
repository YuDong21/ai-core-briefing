"""
publish.py — GitHub 发布模块。

将生成的简报自动 commit + push 到 GitHub 仓库。
支持：
  1. 提交当日简报文件
  2. 更新每日 INDEX.md（所有历史简报索引）
  3. GitHub Actions trigger（可选）
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from config import GITHUB_REPO, GITHUB_BRANCH, GITHUB_TOKEN


class GitHubPublisher:
    """
    将简报发布到 GitHub 仓库。

    使用 PyGithub API 或直接 HTTP API 提交文件。
    """

    def __init__(
        self,
        repo: str | None = None,
        branch: str | None = None,
        token: str | None = None,
    ) -> None:
        self.repo_name = repo or GITHUB_REPO
        self.branch = branch or GITHUB_BRANCH
        self.token = token or GITHUB_TOKEN

    def publish_briefing(
        self,
        markdown_content: str,
        date_str: str,
        daily_dir: Path | str,
    ) -> dict[str, Any]:
        """
        发布单日简报到 GitHub。

        1. 将 markdown 文件写入 local_daily_dir
        2. 调用 GitHub API 创建/更新 daily/AI核心技术简报_YYYY-MM-DD.md
        3. 更新 INDEX.md 索引
        """
        if not self.token:
            return {"status": "skipped", "reason": "No GITHUB_TOKEN"}

        from github import Github

        gh = Github(self.token)
        repo = gh.get_repo(self.repo_name)

        # ── 1. 提交当日简报文件 ─────────────────────────────────────────
        file_path = f"daily/AI核心技术简报_{date_str}.md"
        commit_msg = f"📅 Daily Briefing: {date_str}"

        try:
            existing = repo.get_contents(file_path, ref=self.branch)
            # 文件已存在，更新
            result = repo.update_file(
                path=file_path,
                message=commit_msg,
                content=markdown_content,
                sha=existing.sha,
                branch=self.branch,
            )
            status = "updated"
        except Exception:  # noqa: BLE001
            # 文件不存在，创建
            result = repo.create_file(
                path=file_path,
                message=commit_msg,
                content=markdown_content,
                branch=self.branch,
            )
            status = "created"

        # ── 2. 更新 INDEX.md ───────────────────────────────────────────
        self._update_index(repo, date_str, file_path)

        return {
            "status": status,
            "sha": result.get("commit", {}).get("sha", ""),
            "url": f"https://github.com/{self.repo_name}/blob/{self.branch}/{file_path}",
        }

    def _update_index(
        self,
        repo: Any,
        date_str: str,
        file_path: str,
    ) -> None:
        """更新简报总索引 INDEX.md。"""
        index_path = "INDEX.md"
        date_label = datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y年%m月%d日")
        weekday = datetime.strptime(date_str, "%Y-%m-%d").strftime("%A")

        new_entry = f"| {date_label} ({weekday}) | [📄 简报]({file_path}) | 自动生成 |"

        try:
            existing = repo.get_contents(index_path, ref=self.branch)
            existing_content = existing.decoded_content.decode("utf-8")
            sha = existing.sha
        except Exception:  # noqa: BLE001
            existing_content = ""
            sha = None

        # 检查是否已有当天记录
        if date_str in existing_content:
            return  # 已存在，跳过

        # 插入到最顶部（紧跟 header）
        lines = existing_content.split("\n")
        insert_after = 0
        for i, line in enumerate(lines):
            if line.startswith("| 日期"):
                insert_after = i + 1
                break

        if insert_after:
            lines.insert(insert_after, new_entry)
            new_content = "\n".join(lines)
        else:
            # 没有找到表头，直接插入
            header = "| 日期 | 简报 | 生成方式 |\n|------|------|----------|\n"
            new_content = header + new_entry + "\n\n" + existing_content

        if sha:
            repo.update_file(
                path=index_path,
                message=f"📑 Update INDEX: {date_str}",
                content=new_content,
                sha=sha,
                branch=self.branch,
            )
        else:
            repo.create_file(
                path=index_path,
                message=f"📑 Create INDEX: {date_str}",
                content=new_content,
                branch=self.branch,
            )


def publish(
    markdown_content: str,
    date_str: str,
    daily_dir: Path | str,
) -> dict[str, Any]:
    """
    快捷发布函数。
    """
    publisher = GitHubPublisher()
    return publisher.publish_briefing(markdown_content, date_str, daily_dir)
