"""
notifier.py — 邮件发送模块。

支持两种方式：
  1. SMTP 直接发送（QQ / 163 / Gmail 等支持 SMTP 的邮箱）
  2. SendGrid API（更稳定，推荐生产环境使用）

使用方式：
  # SMTP（以 QQ 邮箱为例）
  export SMTP_USERNAME="2601082764@qq.com"
  export SMTP_PASSWORD="your_auth_code"  # 不是登录密码，是授权码

  # SendGrid（更稳定）
  export SENDGRID_API_KEY="SG.xxxx"

  python main.py  # 自动发送邮件
"""

from __future__ import annotations

import json
import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

import requests
from config import EmailConfig


class EmailNotifier:
    """
    邮件发送器，支持 SMTP 和 SendGrid 两种方式。
    """

    def __init__(self, config: EmailConfig | None = None) -> None:
        self.config = config or EmailConfig()

    # -------------------------------------------------------------------------
    # 公共 API
    # -------------------------------------------------------------------------

    def send_briefing(
        self,
        markdown_content: str,
        date_str: str,
        subject: str | None = None,
    ) -> dict[str, Any]:
        """
        发送简报邮件。

        Parameters
        ----------
        markdown_content : str
            简报 Markdown 内容
        date_str : str
            日期字符串，如 "2026-04-05"
        subject : str, optional
            邮件标题，默认自动生成

        Returns
        -------
        dict — {"status": "sent" | "skipped" | "error", "message": str}
        """
        if not self.config.is_configured:
            return {
                "status": "skipped",
                "message": "Email not configured. Set SMTP_USERNAME/SMTP_PASSWORD or SENDGRID_API_KEY.",
            }

        if not self.config.recipients:
            return {"status": "skipped", "message": "No recipients configured."}

        subject = subject or f"🤖 AI 核心技术简报 {date_str}"

        if self.config.method == "sendgrid":
            return self._send_via_sendgrid(subject, markdown_content)
        return self._send_via_smtp(subject, markdown_content)

    def send_briefing_with_summary(
        self,
        markdown_content: str,
        date_str: str,
        arxiv_count: int = 0,
        github_count: int = 0,
        blog_count: int = 0,
        github_url: str = "",
    ) -> dict[str, Any]:
        """
        发送带摘要预览的邮件版本（HTML 格式，更美观）。

        Parameters
        ----------
        markdown_content : str
            完整 Markdown 内容作为邮件正文
        date_str : str
            日期
        arxiv_count / github_count / blog_count : int
            本期收录数量
        github_url : str
            GitHub 简报链接
        """
        if not self.config.is_configured:
            return {
                "status": "skipped",
                "message": "Email not configured.",
            }

        subject = f"🤖 AI 核心技术简报 {date_str}（ArXiv {arxiv_count} 篇 | GitHub {github_count} 个）"

        html_body = self._build_html_email(
            markdown_content=markdown_content,
            date_str=date_str,
            arxiv_count=arxiv_count,
            github_count=github_count,
            blog_count=blog_count,
            github_url=github_url,
        )

        if self.config.method == "sendgrid":
            return self._send_html_via_sendgrid(subject, html_body)
        return self._send_html_via_smtp(subject, html_body)

    # -------------------------------------------------------------------------
    # SMTP 发送
    # -------------------------------------------------------------------------

    def _send_via_smtp(self, subject: str, body: str) -> dict[str, Any]:
        """通过 SMTP 发送纯文本邮件。"""
        try:
            msg = MIMEMultipart()
            msg["From"] = f"{self.config.from_name} <{self.config.smtp_username}>"
            msg["To"] = ", ".join(self.config.recipients)
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain", "utf-8"))

            self._smtp_send(msg)
            return {
                "status": "sent",
                "method": "smtp",
                "recipients": self.config.recipients,
                "message": f"Sent to {len(self.config.recipients)} recipient(s)",
            }
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "method": "smtp", "message": str(exc)}

    def _send_html_via_smtp(self, subject: str, html_body: str) -> dict[str, Any]:
        """通过 SMTP 发送 HTML 邮件。"""
        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = f"{self.config.from_name} <{self.config.smtp_username}>"
            msg["To"] = ", ".join(self.config.recipients)
            msg["Subject"] = subject
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            self._smtp_send(msg)
            return {
                "status": "sent",
                "method": "smtp",
                "recipients": self.config.recipients,
                "message": f"Sent HTML email to {len(self.config.recipients)} recipient(s)",
            }
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "method": "smtp", "message": str(exc)}

    def _smtp_send(self, msg: MIMEMultipart) -> None:
        """建立 SMTP 连接并发送。"""
        if self.config.smtp_ssl:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(
                self.config.smtp_host,
                self.config.smtp_port,
                context=context,
            ) as server:
                server.login(self.config.smtp_username, self.config.smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.smtp_username, self.config.smtp_password)
                server.send_message(msg)

    # -------------------------------------------------------------------------
    # SendGrid 发送
    # -------------------------------------------------------------------------

    def _send_via_sendgrid(self, subject: str, body: str) -> dict[str, Any]:
        """通过 SendGrid API 发送邮件。"""
        url = "https://api.sendgrid.com/v3/mail/send"
        headers = {
            "Authorization": f"Bearer {self.config.sendgrid_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "personalizations": [
                {"to": [{"email": r} for r in self.config.recipients]}],
            "from": {"email": self.config.smtp_username, "name": self.config.from_name},
            "subject": subject,
            "content": [{"type": "text/plain", "value": body}],
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        if resp.status_code in (200, 201, 202):
            return {
                "status": "sent",
                "method": "sendgrid",
                "recipients": self.config.recipients,
                "message": f"Sent to {len(self.config.recipients)} recipient(s)",
            }
        return {"status": "error", "method": "sendgrid", "message": resp.text[:200]}

    def _send_html_via_sendgrid(self, subject: str, html_body: str) -> dict[str, Any]:
        """通过 SendGrid API 发送 HTML 邮件。"""
        url = "https://api.sendgrid.com/v3/mail/send"
        headers = {
            "Authorization": f"Bearer {self.config.sendgrid_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "personalizations": [
                {"to": [{"email": r} for r in self.config.recipients]}],
            "from": {"email": self.config.smtp_username, "name": self.config.from_name},
            "subject": subject,
            "content": [{"type": "text/html", "value": html_body}],
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        if resp.status_code in (200, 201, 202):
            return {
                "status": "sent",
                "method": "sendgrid",
                "recipients": self.config.recipients,
                "message": f"Sent HTML email to {len(self.config.recipients)} recipient(s)",
            }
        return {"status": "error", "method": "sendgrid", "message": resp.text[:200]}

    # -------------------------------------------------------------------------
    # HTML 邮件模板
    # -------------------------------------------------------------------------

    @staticmethod
    def _build_html_email(
        markdown_content: str,
        date_str: str,
        arxiv_count: int,
        github_count: int,
        blog_count: int,
        github_url: str,
    ) -> str:
        """将 Markdown 简报转为 HTML 邮件。"""
        # 简单的 Markdown → HTML 转换
        import re

        def md_to_html(text: str) -> str:
            # 标题
            text = re.sub(r"^### (.+)$", r"<h3>\1</h3>", text, flags=re.MULTILINE)
            text = re.sub(r"^## (.+)$", r"<h2>\1</h2>", text, flags=re.MULTILINE)
            text = re.sub(r"^# (.+)$", r"<h1>\1</h1>", text, flags=re.MULTILINE)
            # 粗体
            text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
            # 链接
            text = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', text)
            # 分割线
            text = re.sub(r"^---$", "<hr>", text, flags=re.MULTILINE)
            # 列表
            text = re.sub(r"^- (.+)$", r"<li>\1</li>", text, flags=re.MULTILINE)
            # 代码块
            text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
            # 段落
            lines = text.split("\n")
            result: list[str] = []
            in_list = False
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("<"):
                    if in_list:
                        result.append("</ul>")
                        in_list = False
                    result.append(line)
                elif stripped and not stripped.startswith("<"):
                    if in_list:
                        result.append("</ul>")
                        in_list = False
                    result.append(f"<p>{stripped}</p>")
                elif stripped == "":
                    if in_list:
                        result.append("</ul>")
                        in_list = False
            if in_list:
                result.append("</ul>")
            return "\n".join(result)

        html_body = md_to_html(markdown_content)

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI 核心技术简报 {date_str}</title>
<style>
  body {{ font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
         max-width: 720px; margin: 0 auto; padding: 20px;
         background: #f8f9fa; color: #1a1a2e; }}
  .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
             color: white; padding: 24px; border-radius: 12px; margin-bottom: 24px; }}
  .header h1 {{ margin: 0 0 8px; font-size: 22px; }}
  .header .meta {{ opacity: 0.85; font-size: 13px; }}
  .stats {{ display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; }}
  .stat {{ background: white; border-radius: 8px; padding: 12px 18px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.1); }}
  .stat strong {{ font-size: 20px; color: #667eea; }}
  h2 {{ color: #2d3748; border-left: 4px solid #667eea; padding-left: 10px; margin-top: 28px; }}
  h3 {{ color: #4a5568; margin-bottom: 8px; }}
  p {{ line-height: 1.7; color: #2d3748; }}
  li {{ line-height: 1.7; color: #2d3748; }}
  code {{ background: #edf2f7; padding: 2px 6px; border-radius: 4px; font-size: 13px; }}
  hr {{ border: none; border-top: 1px solid #e2e8f0; margin: 24px 0; }}
  .footer {{ text-align: center; color: #a0aec0; font-size: 12px;
              margin-top: 40px; padding-top: 20px; border-top: 1px solid #e2e8f0; }}
  a {{ color: #667eea; }}
  .badge {{ display: inline-block; background: #edf2f7; padding: 2px 8px;
            border-radius: 12px; font-size: 12px; margin-right: 6px; }}
</style>
</head>
<body>
<div class="header">
  <h1>🤖 AI 核心技术简报</h1>
  <div class="meta">📅 {date_str} &nbsp; 自动生成</div>
</div>

<div class="stats">
  <div class="stat"><strong>{arxiv_count}</strong> 篇 ArXiv 论文</div>
  <div class="stat"><strong>{github_count}</strong> 个 GitHub 项目</div>
  <div class="stat"><strong>{blog_count}</strong> 篇技术博客</div>
</div>

<div class="content">
{html_body}
</div>

<div class="footer">
  <p>🤖 AI 核心技术简报 · 由 ai-core-briefing 自动生成</p>
  <p>📡 数据来源: ArXiv · GitHub Trending · AI Lab Blogs</p>
  {"<p><a href='" + github_url + "'>📄 GitHub 在线阅读</a></p>" if github_url else ""}
</div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# 快捷函数
# ---------------------------------------------------------------------------

def send_email(
    markdown_content: str,
    date_str: str,
    **kwargs,
) -> dict[str, Any]:
    """一行发送邮件。"""
    notifier = EmailNotifier()
    return notifier.send_briefing(markdown_content, date_str, **kwargs)


def send_html_email(
    markdown_content: str,
    date_str: str,
    **kwargs,
) -> dict[str, Any]:
    """一行发送 HTML 邮件。"""
    notifier = EmailNotifier()
    return notifier.send_briefing_with_summary(markdown_content, date_str, **kwargs)
