from datetime import datetime, timedelta
from sqlalchemy import desc
from ix.db.conn import Session
from ix.db.models.news_item import NewsItem
from ix.misc import get_logger
import os

logger = get_logger(__name__)

REPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>The AI Bottleneck Desk Report | {date}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;500;600;700;900&family=Playfair+Display:ital,wght@0,400;0,500;0,600;0,700;0,800;0,900;1,400;1,500;1,600;1,700&family=Source+Serif+4:ital,opsz,wght@0,8..60,200..900;1,8..60,200..900&family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

  :root {{
    --paper: #f5f0e8;
    --paper-dark: #e8e0d0;
    --paper-light: #faf7f0;
    --ink: #1a1a1a;
    --ink-light: #3a3a3a;
    --ink-muted: #6b6b6b;
    --accent-red: #8b0000;
    --accent-gold: #b8860b;
    --accent-blue: #1a3a5c;
    --rule: #2a2a2a;
    --rule-light: #c0b8a8;
  }}

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    font-family: 'Source Serif 4', 'Noto Serif KR', serif;
    background: #d4cec2;
    color: var(--ink);
    line-height: 1.7;
    -webkit-font-smoothing: antialiased;
  }}

  .newspaper {{
    max-width: 1100px;
    margin: 30px auto;
    background: var(--paper);
    box-shadow: 0 8px 30px rgba(0,0,0,0.12);
    position: relative;
    overflow: hidden;
    padding-bottom: 50px;
  }}

  .masthead {{
    text-align: center;
    padding: 28px 40px 0;
    border-bottom: 4px double var(--rule);
  }}

  .masthead-top {{
    display: flex;
    justify-content: space-between;
    font-family: 'Inter', sans-serif;
    font-size: 10px;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: var(--ink-muted);
    margin-bottom: 12px;
  }}

  .masthead-title {{
    font-family: 'Playfair Display', serif;
    font-size: 56px;
    font-weight: 900;
    letter-spacing: -1px;
    line-height: 1.05;
    color: var(--ink);
    margin: 8px 0;
  }}

  .content-wrapper {{ padding: 0 40px 30px; }}

  .article-section {{
    padding: 28px 0;
    border-bottom: 1px solid var(--rule-light);
  }}

  .section-label {{
    font-family: 'Inter', sans-serif;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: var(--accent-red);
    margin-bottom: 4px;
  }}

  .section-title {{
    font-family: 'Playfair Display', serif;
    font-size: 30px;
    font-weight: 800;
    line-height: 1.15;
    color: var(--ink);
    margin-bottom: 10px;
  }}
  
  .section-meta {{
      font-family: 'Inter', sans-serif;
      font-size: 11px;
      color: var(--ink-muted);
      margin-bottom: 16px;
      font-style: italic;
  }}

  .article-body p {{ 
      margin-bottom: 14px; 
      font-size: 15px;
      color: var(--ink-light);
  }}
  
  a {{ color: var(--accent-blue); text-decoration: none; border-bottom: 1px dotted var(--accent-blue); }}
  a:hover {{ border-bottom: 1px solid var(--accent-blue); }}

</style>
</head>
<body>

<div class="newspaper">
  <div class="masthead">
    <div class="masthead-top">
      <span>Daily Intelligence Briefing</span>
      <span>{date}</span>
      <span>Vol. {vol_num}</span>
    </div>
    <h1 class="masthead-title">The Desk Report</h1>
    <div style="height: 1px; background: var(--rule); margin: 0 -40px 10px;"></div>
  </div>

  <div class="content-wrapper">
    <!-- GENERATED CONTENT STARTS HERE -->
    {content}
    <!-- GENERATED CONTENT ENDS HERE -->
  </div>
</div>

</body>
</html>
"""


def generate_desk_report():
    today_str = datetime.now().strftime("%Y-%m-%d")
    report_filename = f"desk_report_{datetime.now().strftime('%Y%m%d')}.html"

    logger.info(f"Generating desk report: {report_filename}")

    with Session() as db:
        # Fetch latest news
        news_items = db.query(NewsItem).order_by(desc(NewsItem.published_at)).limit(20).all()

        content_html = ""
        for i, item in enumerate(news_items):
            idx = str(i + 1).zfill(2)
            source = item.source_name or item.source or "unknown"
            time_str = item.published_at.strftime("%H:%M") if item.published_at else ""

            # Simple content cleaning
            body = item.summary or item.body_text or "No content available."
            # Remove HTML tags if raw
            # ... skipping robust cleaning for brevity ...

            content_html += f"""
            <div class="article-section">
              <div class="section-label">Briefing {idx} / {source}</div>
              <h3 class="section-title"><a href="{item.url or '#'}" target="_blank">{item.title}</a></h3>
              <div class="section-meta">Published at {time_str}</div>
              <div class="article-body">
                <p>{body}</p>
              </div>
            </div>
            """

    final_html = REPORT_TEMPLATE.format(
        date=datetime.now().strftime("%B %d, %Y"),
        vol_num=datetime.now().strftime("%j"),  # Day of year as volume
        content=content_html,
    )

    # Save to root directory
    output_path = os.path.join(os.getcwd(), report_filename)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_html)

    logger.info(f"Report saved to {output_path}")


if __name__ == "__main__":
    generate_desk_report()
