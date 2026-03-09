"""Helper script for Claude Code cron to fetch/save intel briefings.

Usage:
    python scripts/intel_briefing.py fetch          # Output raw intel JSON (last 24h)
    python scripts/intel_briefing.py save '<json>'  # Save briefing to DB
"""

import sys
import json
import logging
from datetime import datetime, timedelta, timezone, date

# Suppress all logging to stderr so stdout is clean JSON
logging.disable(logging.CRITICAL)


def fetch():
    """Fetch last 24h of intel from all 3 sources and print as JSON."""
    from ix.db.conn import Session
    from ix.db.models import TelegramMessage, NewsItem
    from ix.db.models.youtube_intel import YouTubeIntel

    cutoff = datetime.now(timezone.utc) - timedelta(hours=72)

    with Session() as db:
        # News items
        news_rows = (
            db.query(NewsItem)
            .filter(NewsItem.discovered_at >= cutoff)
            .order_by(NewsItem.discovered_at.desc())
            .limit(150)
            .all()
        )
        news = [
            {
                "source": r.source_name or r.source,
                "title": r.title,
                "summary": (r.summary or "")[:300],
                "url": r.url,
                "published_at": str(r.published_at) if r.published_at else None,
            }
            for r in news_rows
        ]

        # Telegram messages (wider window — messages may lag)
        tg_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        tg_rows = (
            db.query(TelegramMessage)
            .filter(TelegramMessage.date >= tg_cutoff)
            .order_by(TelegramMessage.date.desc())
            .limit(200)
            .all()
        )
        telegram = [
            {
                "channel": r.channel_name,
                "message": (r.message or "")[:500],
                "date": str(r.date) if r.date else None,
            }
            for r in tg_rows
        ]

        # YouTube videos (with summaries)
        yt_rows = (
            db.query(YouTubeIntel)
            .filter(
                YouTubeIntel.is_deleted == False,
                YouTubeIntel.published_at >= cutoff - timedelta(days=6),
            )
            .order_by(YouTubeIntel.published_at.desc())
            .limit(30)
            .all()
        )
        youtube = [
            {
                "channel": r.channel,
                "title": r.title,
                "summary": (r.summary or "")[:500],
                "published_at": str(r.published_at) if r.published_at else None,
                "url": r.url,
            }
            for r in yt_rows
        ]

    result = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "news_count": len(news),
        "telegram_count": len(telegram),
        "youtube_count": len(youtube),
        "news": news,
        "telegram": telegram,
        "youtube": youtube,
    }
    print(json.dumps(result, ensure_ascii=False))


def save(briefing_json: str):
    """Save a briefing JSON to the intel_briefing table (upsert by date)."""
    from ix.db.conn import Session
    from ix.db.models.intel_briefing import IntelBriefing

    data = json.loads(briefing_json)
    briefing_date = date.fromisoformat(data["date"])

    with Session() as db:
        existing = (
            db.query(IntelBriefing)
            .filter(IntelBriefing.date == briefing_date)
            .first()
        )
        if existing:
            existing.headlines = data["headlines"]
            existing.insights = data["insights"]
            existing.themes = data["themes"]
            existing.raw_input_summary = data.get("raw_input_summary")
        else:
            db.add(
                IntelBriefing(
                    date=briefing_date,
                    headlines=data["headlines"],
                    insights=data["insights"],
                    themes=data["themes"],
                    raw_input_summary=data.get("raw_input_summary"),
                )
            )
    print(json.dumps({"ok": True, "date": str(briefing_date)}))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/intel_briefing.py [fetch|save]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "fetch":
        fetch()
    elif cmd == "save":
        if len(sys.argv) < 3:
            print("Usage: python scripts/intel_briefing.py save '<json>'")
            sys.exit(1)
        save(sys.argv[2])
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
