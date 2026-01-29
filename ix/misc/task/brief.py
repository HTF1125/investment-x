import os
from datetime import datetime, timedelta
from google import genai
from ix.db.conn import Session
from ix.db.models import TelegramMessage
from ix.misc.email import EmailSender
from ix.misc import Settings, get_logger
import markdown

logger = get_logger(__name__)


def send_daily_market_brief():
    """
    Generates the Daily Global Market Intelligence Brief using Google GenAI
    and sends it via email to configured recipients.
    """
    logger.info("Starting Daily Market Brief generation task...")

    # 1. Fetch Data
    msgs_text = ""
    try:
        with Session() as session:
            # DB stores KST.
            # Current KST = UTC + 9
            now_kst = datetime.utcnow() + timedelta(hours=9)
            cutoff = now_kst - timedelta(hours=24)

            msgs = (
                session.query(TelegramMessage)
                .filter(TelegramMessage.date >= cutoff)
                .order_by(TelegramMessage.date.desc())
                .all()
            )

            if not msgs:
                logger.info(
                    "No messages found in the last 24h. Skipping brief generation."
                )
                return

            for m in msgs:
                if m.message and m.message.strip():
                    # DB is KST, no adjustment needed
                    msgs_text += f"[{m.date.strftime('%Y-%m-%d %H:%M')}] @{m.channel_name}:\n{m.message}\n---\n"

    except Exception as e:
        logger.error(f"Error fetching Telegram messages: {e}")
        return

    if not msgs_text:
        logger.info("No valid message content found.")
        return

    # 2. Configure GenAI Client
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error(
            "GEMINI_API_KEY environment variable not set. Cannot generate brief."
        )
        return

    client = genai.Client(api_key=api_key)

    # 3. Prepare Prompt
    base_prompt = """
# 📌 *Global Market Intelligence & Strategic Outlook*

## ROLE & EXPERTISE

You are the **Global Chief Investment Officer (CIO)** of a sovereign wealth fund with **$500B+ AUM**.
Your daily briefs are read by the Investment Committee and Head of Trading.

**Your Edge:**
1.  **Connecting the dots:** You don't just report news; you explain the *mechanism* of how event A triggers reaction B in asset C.
2.  **Second-Level Thinking:** You look beyond the immediate reaction to the secondary consequences (e.g., "Oil up -> Headline CPI up -> Fed hawkish -> Tech valuation compression").
3.  **Institutional Tone:** You use precise, high-finance terminology in all output languages (English, Korean, Chinese, Japanese).

---

## SOURCE MATERIAL

Analyze the following **raw market intelligence feed** (Telegram messages from the last 24 hours):

<RAW_FEED>
{raw_feed_content}
</RAW_FEED>

---

## OBJECTIVE

Produce a **"Daily Global Market Intelligence Brief"** in **four languages** (Korean, English, Chinese, Japanese).
The report must be **information-dense**, **analytical**, and **forward-looking**.
**Do not be generic.** If the feed lacks data, state "No significant updates"; do not hallucinate. But where data exists, **squeeze every drop of insight out of it.**

---

## ANALYSIS GUIDELINES

### 1️⃣ Synthesis & Narrative Construction
*   **Don't just list bullet points.** Weave a narrative for the day. Is it a "Risk-Off" day? A "Reflation" trade? A "Tech Rotation"? Define the day's theme clearly.
*   **Cross-Asset Correlations:** If Treasury yields moved, how did that impact the Yen? If Oil tanked, what happened to Energy credits? Explicitly link these movements.

### 2️⃣ Depth of Commentary (The "Why" and "So What")
For every major development, you must address:
*   **Context:** Is this a reversal? A continuation? A breakout?
*   **Quantification:** Use specific numbers (basis points, % return, price levels) from the feed.
*   **Strategic Implication:** "Neutral", "Overweight", or "Underweight" signal for related assets.

### 3️⃣ Language Specifications
*   **Korean:** Use formal financial language (e.g., `듀레이션 조정`, `베어 스티프닝`, `리스크 프리미엄`).
*   **Chinese:** Use institutional terms (e.g., `收益率曲线控制`, `估值修复`, `避险情绪`).
*   **Japanese:** Use professional terminology (e.g., `イールドカーブ・コントロール`, `逆相関`, `ボラティリティ`).

---

## OUTPUT FORMAT (STRICT)

For **EACH** language (Korean, English, Chinese, Japanese), generate the report in this exact structure:

```
---
## [Language Name] Report

### 🧐 CIO's Daily Thesis (The "Big Picture")
* [2-3 sentences summarizing the dominant market narrative for the last 24h. What is the single most important thing driving flows today?]

### 🚨 Critical Alpha Signals (Executive Summary)
* **[Headline 1]:** [Detailed context + Strategic Implication]
* **[Headline 2]:** [Detailed context + Strategic Implication]
* **[Headline 3]:** [Detailed context + Strategic Implication]

### 📉 Macro, Rates & FX Deep Dive
* **Theme:** [e.g., "Fed Pivot Expectations vs. Sticky Inflation"]
* **Analysis:** [Detailed paragraph analyzing central bank moves, curve shape (2s10s), and liquidity conditions. Mention specific rates/FX levels if available.]
* **Trade Implication:** [e.g., "Favor short-duration cash over long-end Treasuries due to supply indigestion."]

### 🏢 Equities & Sector Rotation
* **Theme:** [e.g., "Tech divergence," "Energy resilience"]
* **Analysis:** [Discuss earnings drivers, valuation spreads, and active sector rotations.]
* **Key Movers:** [Mention specific tickers or sub-sectors if in feed.]

### ₿ Crypto, Alts & Commodities
* **Analysis:** [Gold, Oil, Bitcoin correlation with real rates and risk appetite.]
* **On-Chain/Flows:** [If data exists, mention ETF flows or on-chain signals.]
```
    """.format(
        raw_feed_content=msgs_text
    )

    # 4. Generate Content
    try:
        response = client.models.generate_content(
            model="gemini-3-pro-preview", contents=base_prompt
        )
        report_content = response.text
    except Exception as e:
        logger.error(f"Error generating content with Google GenAI: {e}")
        return

    # 5. Send Email

    # Fetch recipients from database (all enabled users with an email)
    recipients = []
    try:
        from ix.db.models.user import User

        with Session() as session:
            users = session.query(User).filter(User.disabled == False).all()
            recipients = [u.email for u in users if u.email]
    except Exception as e:
        logger.error(f"Error fetching email recipients from database: {e}")
        return

    if not recipients:
        logger.warning("No enabled users found in database to send email to.")
        return

    to_str = ", ".join(recipients)

    # Formatting valid KST time for subject
    now_kst = datetime.utcnow() + timedelta(hours=9)
    subject = f"[IX] Daily Global Market Intelligence Brief ({now_kst.strftime('%Y-%m-%d %H:%M')} KST)"

    # Convert Markdown to HTML for nicer email
    html_content = markdown.markdown(report_content)

    # Basic CSS for nicer email presentation
    html_body = f"""
    <html>
        <head>
            <style>
                body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
                h2 {{ color: #2c3e50; border-bottom: 2px solid #eee; padding-bottom: 10px; margin-top: 30px; }}
                h3 {{ color: #34495e; margin-top: 25px; }}
                ul {{ padding-left: 20px; }}
                li {{ margin-bottom: 8px; }}
                strong {{ color: #1a252f; }}
                .crawler-date {{ color: #7f8c8d; font-size: 0.9em; }}
                hr {{ border: 0; border-top: 1px solid #eee; margin: 30px 0; }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
    </html>
    """

    try:
        # Use BCC for privacy, 'to' defaults to sender in EmailSender
        email_sender = EmailSender(subject=subject, content=html_body, bcc=to_str)
        # Note: EmailSender needs to handle HTML content type
        email_sender.msg.set_content(html_body, subtype="html")
        email_sender.send()
        logger.info(
            f"Successfully sent Market Brief to {len(recipients)} recipients (BCC)."
        )
    except Exception as e:
        logger.error(f"Error sending email: {e}")
