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

<CONSTRAINTS>
1. **Total Coverage:** Capture EVERY significant event, price move, or data point mentioned in the RAW_FEED. Do not limit to a "Top 3".
2. **Category-Based Organization:** Group all insights into the specific sections provided (Macro, Equities, etc.).
3. **Cross-Lingual Consistency:** The factual content, specific numbers, and strategic stance MUST be identical across all four languages. 
4. **Professional Tone:** Maintain the CIO persona: institutional, quantitative, and analytical.
</CONSTRAINTS>

## ROLE
You are the **Global Chief Investment Officer (CIO)**. Your brief must be precise, dense, and written for an Investment Committee.

---

## SOURCE MATERIAL
Analyze the following raw market intelligence feed:

<RAW_FEED>
{raw_feed_content}
</RAW_FEED>

---

## EXECUTION STEPS (Internal Reasoning)
1. **Step 1 (Inventory):** Extract every distinct market event, data release, and asset price movement from the RAW_FEED.
2. **Step 2 (Drafting):** Draft the full report in **English** first as the "Master Draft" to ensure logic and depth.
3. **Step 3 (Translation):** Accurately translate the Master Draft into Korean, Chinese, and Japanese using high-finance terminology.

---

## OUTPUT FORMAT (STRICT)

Generate the report for **EACH** language (Korean, English, Chinese, Japanese). 

### 🧐 CIO's Daily Thesis (The "Big Picture")
* [Summary of the dominant theme of the last 24h based on the feed.]

### 🚨 Comprehensive Alpha Signals (Categorized)
* **Macro & Central Banks:** [List ALL relevant macro events/data from the feed. Use bold headers for each event.]
* **Equities & Sectors:** [List ALL stock-specific or sector-wide movements.]
* **Rates & FX:** [List ALL yield curve shifts and currency moves.]
* **Commodities & Alternatives:** [List ALL updates on Oil, Gold, Crypto, etc.]

### 📈 Detailed Strategic Depth
* **Analysis:** [Connect the dots. If Treasury yields rose, explain the impact on Nasdaq or the Yen based on the feed's data.]
* **Quantification:** [Explicitly mention basis points, %, and price levels.]
* **Strategic Implication:** [Label specific assets as "Overweight", "Underweight", or "Neutral" based on the analysis.]

---
(Repeat the above structure for Korean, Chinese, and Japanese)
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
