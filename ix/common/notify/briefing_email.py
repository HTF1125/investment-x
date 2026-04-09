"""
Briefing email rendering and delivery.

Shared between the CLI script (`scripts/briefing/send_briefing_email.py`) and
the API endpoint (`POST /api/briefings/{date}/send-email`).
"""

from __future__ import annotations

import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ── Markdown → HTML renderer ─────────────────────────────────────────────────

DELTA_TAG_STYLES = {
    "NEW": ("background:#dcfce7;color:#166534;border:1px solid #bbf7d0;", "NEW"),
    "SHIFTED": ("background:#fef9c3;color:#854d0e;border:1px solid #fde68a;", "SHIFTED"),
    "CHANGED": ("background:#dbeafe;color:#1e40af;border:1px solid #bfdbfe;", "CHANGED"),
    "CARRIED": ("background:#f3f4f6;color:#6b7280;border:1px solid #e5e7eb;", "CARRIED"),
    "RESOLVED": ("background:#f3f4f6;color:#9ca3af;border:1px solid #e5e7eb;text-decoration:line-through;", "RESOLVED"),
}

TAG_RE = re.compile(
    r"\[(NEW|SHIFTED|CHANGED|CARRIED|RESOLVED)(?:\s+since\s+[\d:]+)?\]"
)
BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")


def _render_inline(text: str) -> str:
    """Convert markdown bold + delta tags to inline HTML."""

    def _replace_tag(m: re.Match) -> str:
        tag = m.group(1)
        style, label = DELTA_TAG_STYLES.get(tag, ("", tag))
        return (
            f'<span style="{style}font-size:9px;font-family:monospace;'
            f'padding:1px 6px;border-radius:3px;letter-spacing:0.05em;">'
            f"{label}</span>"
        )

    text = TAG_RE.sub(_replace_tag, text)
    text = BOLD_RE.sub(r'<strong style="color:#1a1a1a;">\1</strong>', text)
    return text


def md_to_html(md: str) -> str:
    """Convert briefing markdown to styled HTML suitable for email."""
    lines = md.split("\n")
    html: list[str] = []
    in_table = False
    in_list = False

    for line in lines:
        s = line.strip()

        # Close open blocks when context changes
        if in_list and not s.startswith("- "):
            html.append("</ul>")
            in_list = False
        if in_table and not s.startswith("|"):
            html.append("</tbody></table>")
            in_table = False

        # ── Headings ──
        if s.startswith("## "):
            html.append(
                f'<h2 style="font-size:14px;text-transform:uppercase;'
                f"letter-spacing:0.08em;color:#3250d0;margin-top:28px;"
                f'border-bottom:1px solid #e0e0e0;padding-bottom:6px;">'
                f"{s[3:]}</h2>"
            )

        # ── Tables ──
        elif s.startswith("|"):
            cells = [c.strip() for c in s.split("|")[1:-1]]
            # Skip separator rows (|---|---|)
            if all(set(c) <= set("- :") for c in cells):
                continue
            if not in_table:
                in_table = True
                html.append(
                    '<table style="width:100%;font-size:12px;font-family:monospace;'
                    'border-collapse:collapse;margin:12px 0;">'
                )
                hdr = ""
                for ci, c in enumerate(cells):
                    align = "text-align:left;" if ci == 0 else "text-align:right;"
                    hdr += (
                        f'<th style="{align}padding:5px 8px;color:#888;'
                        f'border-bottom:1px solid #e0e0e0;">{_render_inline(c)}</th>'
                    )
                html.append(f"<thead><tr>{hdr}</tr></thead><tbody>")
            else:
                row = ""
                for ci, c in enumerate(cells):
                    rendered = _render_inline(c)
                    color = ""
                    if "+" in c and "%" in c:
                        color = "color:#16a34a;"
                    elif "-" in c and "%" in c:
                        color = "color:#dc2626;"
                    align = "text-align:left;" if ci == 0 else "text-align:right;"
                    row += (
                        f'<td style="padding:4px 8px;{align}{color}'
                        f'border-bottom:1px solid #eee;">{rendered}</td>'
                    )
                html.append(f"<tr>{row}</tr>")

        # ── List items ──
        elif s.startswith("- "):
            if not in_list:
                in_list = True
                html.append('<ul style="padding-left:20px;margin:8px 0;">')
            html.append(
                f'<li style="font-size:13px;line-height:1.8;color:#333;'
                f'margin-bottom:4px;">{_render_inline(s[2:])}</li>'
            )

        # ── Blank line ──
        elif not s:
            html.append("<br>")

        # ── Paragraph ──
        else:
            html.append(
                f'<p style="font-size:13px;line-height:1.8;color:#333;'
                f'margin:6px 0;">{_render_inline(s)}</p>'
            )

    if in_list:
        html.append("</ul>")
    if in_table:
        html.append("</tbody></table>")
    return "\n".join(html)


# ── Email assembly ────────────────────────────────────────────────────────────


def build_email_html(
    briefings: dict[str, str], report_date: str, baseline_date: str | None = None
) -> str:
    """Build the full HTML email from a dict of {lang_label: markdown_content}."""
    baseline = f" &bull; Baseline: vs yesterday ({baseline_date})" if baseline_date else ""

    section_html = []
    for title, content in briefings.items():
        section_html.append(
            f'<div style="margin-bottom:40px;">'
            f'<h1 style="font-size:15px;color:#3250d0;font-family:monospace;'
            f"text-transform:uppercase;letter-spacing:0.1em;"
            f'border-bottom:2px solid #e0e0e0;padding-bottom:8px;margin-bottom:16px;">'
            f"{title}</h1>{md_to_html(content)}</div>"
        )

    return f"""<html><body style="font-family:'Inter','Segoe UI',Arial,sans-serif;background:#f8f7f4;color:#333;padding:32px;max-width:720px;margin:0 auto;">
<div style="text-align:center;margin-bottom:24px;">
<h1 style="font-size:18px;color:#1a1a1a;letter-spacing:0.04em;margin:0;">Macro Intelligence Briefings</h1>
<p style="font-size:11px;color:#999;font-family:monospace;margin:4px 0;">{report_date}{baseline}</p>
</div>
{"".join(section_html)}
<div style="text-align:center;margin-top:32px;padding-top:16px;border-top:1px solid #e0e0e0;">
<p style="font-size:10px;color:#999;font-family:monospace;">Investment-X &bull; Generated {report_date}</p>
</div>
</body></html>"""


# ── DB loader ────────────────────────────────────────────────────────────────


def load_briefings_from_db(report_date: str) -> tuple[dict[str, str], str | None]:
    """Load briefings + baseline_date from the database for a given date.

    Returns ({lang_label: markdown}, baseline_date) or ({}, None) if not found.
    """
    from ix.db.conn import Session
    from ix.db.models.briefing import Briefings

    with Session() as s:
        report = (
            s.query(Briefings)
            .filter(Briefings.date == report_date, Briefings.briefing.isnot(None))
            .first()
        )
        if not report:
            return {}, None

        briefings: dict[str, str] = {}
        if report.briefing:
            briefings["🇺🇸 English"] = report.briefing

        translations = (report.sources or {}).get("translations", {})
        lang_map = {"kr": "🇰🇷 한국어", "cn": "🇨🇳 中文", "jp": "🇯🇵 日本語"}
        for code, label in lang_map.items():
            if code in translations:
                briefings[label] = translations[code]

        baseline = (report.sources or {}).get("baseline_date")
        return briefings, baseline


# ── Recipients ───────────────────────────────────────────────────────────────


def load_admin_recipients() -> list[str]:
    """Return all active admin/owner email addresses from the DB."""
    from ix.db.conn import Session
    from ix.db.models.user import User

    with Session() as s:
        rows = (
            s.query(User.email)
            .filter(
                (User.role.in_(["admin", "owner"])) | (User.is_admin == True)  # noqa: E712
            )
            .filter(User.disabled == False)  # noqa: E712
            .all()
        )
    return [r.email for r in rows if r.email]


# ── SMTP delivery ────────────────────────────────────────────────────────────


class EmailConfigError(RuntimeError):
    """Raised when SMTP credentials are not configured."""


def send_email(html: str, subject: str, recipients: list[str]) -> None:
    """Send an HTML email via Gmail SMTP.

    Raises EmailConfigError if EMAIL_LOGIN / EMAIL_PASSWORD are not set.
    """
    smtp_user = os.environ.get("EMAIL_LOGIN")
    smtp_pass = os.environ.get("EMAIL_PASSWORD")
    if not smtp_user or not smtp_pass:
        raise EmailConfigError("EMAIL_LOGIN and EMAIL_PASSWORD must be set")

    msg = MIMEMultipart("alternative")
    msg["From"] = smtp_user
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)


# ── High-level helper ────────────────────────────────────────────────────────


def send_briefing_email(
    report_date: str,
    recipients: list[str] | None = None,
) -> dict:
    """Load, render, and send a briefing email.

    Args:
        report_date: ISO date string (YYYY-MM-DD).
        recipients: Override list. If None, falls back to admin/owner users.

    Returns:
        {"recipients_count": N, "languages": [...], "baseline_date": ...}

    Raises:
        ValueError: if no briefing content exists for the date.
        ValueError: if no recipients can be resolved.
        EmailConfigError: if SMTP credentials are missing.
    """
    briefings, baseline_date = load_briefings_from_db(report_date)
    if not briefings:
        raise ValueError(f"No briefing content found for {report_date}")

    if recipients is None:
        recipients = load_admin_recipients()
    if not recipients:
        raise ValueError("No recipients resolved (no admin/owner users found)")

    subject = f"Macro Intelligence Briefings — {report_date}"
    html = build_email_html(briefings, report_date, baseline_date)
    send_email(html, subject, recipients)

    return {
        "recipients_count": len(recipients),
        "languages": list(briefings.keys()),
        "baseline_date": baseline_date,
    }
