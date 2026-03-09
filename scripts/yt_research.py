"""
Automated YouTube + Google Drive Macro Research Pipeline
1. Pulls recent videos from configured channels via yt-dlp
2. Searches Google Drive for recent research PDFs (via NotebookLM)
3. Creates a NotebookLM notebook
4. Adds videos + Drive files as sources
5. Asks NotebookLM to analyze
6. Generates infographic + report

Usage:
    python scripts/yt_research.py                    # last 3 days, all channels + Drive
    python scripts/yt_research.py --days 5           # last 5 days
    python scripts/yt_research.py --date 2026-02-15  # specific date (lookback --days from that date)
    python scripts/yt_research.py --topic "inflation" # filter by topic
    python scripts/yt_research.py --max-videos 15    # limit video sources
    python scripts/yt_research.py --skip-drive        # skip Google Drive sources
    python scripts/yt_research.py --drive-folder "My Research"  # custom Drive folder
"""
import argparse
import asyncio
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# ── Channel Configuration ──────────────────────────────────────────
CHANNELS = [
    {"url": "https://www.youtube.com/@ForwardGuidanceBW", "name": "Forward Guidance"},
    {"url": "https://www.youtube.com/@ARKInvest2015", "name": "ARK Invest"},
    {"url": "https://www.youtube.com/@RealVisionFinance", "name": "Real Vision"},
    {"url": "https://www.youtube.com/@RealEismanPlaybook", "name": "Real Eisman Playbook"},
    {"url": "https://www.youtube.com/@DoubleLineCapital", "name": "DoubleLine Capital"},
    {"url": "https://www.youtube.com/@MilkRoadMacro", "name": "Milk Road Macro"},
    {"url": "https://www.youtube.com/@MilkRoadDaily", "name": "Milk Road Daily"},
    {"url": "https://www.youtube.com/@MilkRoadAI", "name": "Milk Road AI"},
    {"url": "https://www.youtube.com/@RaoulPalTJM", "name": "Raoul Pal TJM"},
    {"url": "https://www.youtube.com/@business", "name": "Bloomberg"},
    {"url": "https://www.youtube.com/@StansberryMedia", "name": "Stansberry Media"},
    {"url": "https://www.youtube.com/@maggielake-talkingmarkets", "name": "Maggie Lake"},
    {"url": "https://www.youtube.com/@bravosresearch", "name": "Bravos Research"},
    {"url": "https://www.youtube.com/@JamieTree", "name": "JamieTree"},
    {"url": "https://www.youtube.com/@C-Documentary", "name": "C-Documentary"},
]



def run_cmd(cmd, timeout=120):
    """Run a command and return stdout.

    ``cmd`` can be a list (preferred) or a string.  When a string is given it
    is split with ``shlex.split`` and executed *without* ``shell=True`` to
    avoid shell-injection risks from dynamic arguments.
    """
    import shlex

    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return result.stdout.strip(), result.stderr.strip(), result.returncode


# ── News & Telegram Functions ─────────────────────────────────────

def fetch_news_and_telegram(days=3):
    """Fetch recent news items and Telegram messages from the database.

    Returns (news_text, telegram_text) — formatted strings ready to add as NotebookLM sources.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from ix.db.conn import Session
    from ix.db.models.news_item import NewsItem
    from ix.db.models.telegram import TelegramMessage

    cutoff = datetime.utcnow() - timedelta(days=days)

    news_items = []
    telegram_msgs = []

    with Session() as db:
        # Fetch news items
        rows = (
            db.query(NewsItem)
            .filter(NewsItem.published_at >= cutoff, NewsItem.is_deleted == False)
            .order_by(NewsItem.published_at.desc())
            .limit(200)
            .all()
        )
        for r in rows:
            date_str = r.published_at.strftime("%Y-%m-%d %H:%M") if r.published_at else ""
            body = r.summary or r.body_text or ""
            if body:
                body = body[:1000]  # Truncate long articles
            news_items.append(f"[{date_str}] {r.source_name or r.source}: {r.title}\n{body}")

        # Fetch Telegram messages
        msgs = (
            db.query(TelegramMessage)
            .filter(TelegramMessage.date >= cutoff)
            .order_by(TelegramMessage.date.desc())
            .limit(300)
            .all()
        )
        for m in msgs:
            date_str = m.date.strftime("%Y-%m-%d %H:%M") if m.date else ""
            telegram_msgs.append(f"[{date_str}] {m.channel_name}: {m.message}")

    # Format as single text blocks for NotebookLM (cap at ~200KB to stay within limits)
    news_text = None
    if news_items:
        combined = f"# News Headlines & Summaries (last {days} days)\n\n"
        for item in news_items:
            if len(combined) + len(item) > 200_000:
                break
            combined += item + "\n\n---\n\n"
        news_text = combined

    telegram_text = None
    if telegram_msgs:
        telegram_text = f"# Telegram Channel Messages (last {days} days)\n\n" + "\n\n---\n\n".join(telegram_msgs)

    return news_text, telegram_text, len(news_items), len(telegram_msgs)


# ── YouTube Functions ──────────────────────────────────────────────

def fetch_channel_videos(channel_url, max_per_channel=15, date_after=None, date_before=None):
    """Fetch recent videos from a channel using yt-dlp, optionally filtered by date range."""
    target_url = f"{channel_url}/videos"

    if date_after or date_before:
        cmd = ["yt-dlp", "-j", "--playlist-end", str(max_per_channel * 5)]
        if date_after:
            cmd += ["--dateafter", str(date_after)]
        if date_before:
            cmd += ["--datebefore", str(date_before)]
        cmd.append(target_url)
    else:
        cmd = ["yt-dlp", "--flat-playlist", "-j", "--playlist-end", str(max_per_channel), target_url]

    stdout, stderr, rc = run_cmd(cmd, timeout=120)
    if rc != 0:
        return []
    videos = []
    for line in stdout.splitlines():
        try:
            d = json.loads(line)
            videos.append({
                "id": d.get("id", ""),
                "title": d.get("title", ""),
                "upload_date": d.get("upload_date", ""),
                "duration": d.get("duration_string", ""),
                "views": d.get("view_count", 0),
                "url": f"https://www.youtube.com/watch?v={d.get('id', '')}",
            })
        except json.JSONDecodeError:
            continue
    return videos[:max_per_channel]


def score_video(video, topic=None):
    """Score a video for relevance. Higher = more relevant."""
    score = 0
    title_lower = video["title"].lower()

    views = video.get("views", 0) or 0
    if views > 100000: score += 5
    elif views > 50000: score += 4
    elif views > 10000: score += 3
    elif views > 5000: score += 2
    elif views > 1000: score += 1

    macro_keywords = [
        "macro", "fed", "inflation", "recession", "market", "economy", "oil",
        "gold", "silver", "bond", "yield", "credit", "risk", "crash", "rally",
        "rotation", "dollar", "geopolit", "iran", "china", "tariff", "war",
        "ai", "tech", "bubble", "debt", "liquidity", "commodity", "energy",
        "weekly", "roundup", "wrap", "outlook", "forecast", "prediction",
    ]
    for kw in macro_keywords:
        if kw in title_lower:
            score += 2

    if topic:
        for t in topic.lower().split():
            if t in title_lower:
                score += 5

    duration = video.get("duration", "")
    if ":" in duration:
        parts = duration.split(":")
        if len(parts) == 2:
            mins = int(parts[0])
            if 15 <= mins <= 60:
                score += 2
            elif mins > 60:
                score += 1

    return score


# ── NotebookLM Functions ──────────────────────────────────────────

async def get_nlm_client():
    """Get an authenticated NotebookLM client (must be used as async context manager)."""
    from notebooklm import NotebookLMClient
    client = await NotebookLMClient.from_storage()
    await client._core.open()
    return client


def ensure_notebooklm_auth():
    """Ensure NotebookLM is authenticated. Runs interactive login if expired."""
    print("  Checking NotebookLM auth...", end=" ", flush=True)

    stdout, stderr, rc = run_cmd(["notebooklm", "list"], timeout=30)
    if rc == 0 and "Error" not in stdout and "Authentication" not in stdout:
        print("OK")
        return True

    print("expired.")
    print("  Launching NotebookLM login (browser will open)...")
    print("  >> Log in to Google, then press ENTER in this terminal. <<\n")
    rc = subprocess.call(["notebooklm", "login"], timeout=180)
    if rc != 0:
        print("  [ERROR] Login failed or was cancelled.")
        return False

    stdout, stderr, rc = run_cmd(["notebooklm", "list"], timeout=30)
    if rc == 0 and "Error" not in stdout and "Authentication" not in stdout:
        print("  Auth OK.")
        return True

    print("  [ERROR] Auth still invalid after login.")
    return False


def notebooklm_cmd(args, timeout=120):
    """Run a notebooklm CLI command.

    ``args`` is a string that will be split via ``shlex.split`` and prepended
    with ``notebooklm``.
    """
    import shlex

    cmd = ["notebooklm"] + shlex.split(args)
    stdout, stderr, rc = run_cmd(cmd, timeout=timeout)
    if rc != 0:
        print(f"  [ERROR] notebooklm {args}: {stderr}")
    return stdout, rc


def extract_drive_file_id(url):
    """Extract Google Drive file ID from a Drive URL."""
    parsed = urlparse(url)
    # https://drive.google.com/open?id=FILE_ID
    if "id" in parse_qs(parsed.query):
        return parse_qs(parsed.query)["id"][0]
    # https://drive.google.com/file/d/FILE_ID/...
    parts = parsed.path.split("/")
    if "d" in parts:
        idx = parts.index("d")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return None


async def search_drive_via_nlm(client, nb_id, query):
    """Search Google Drive via NotebookLM's research API. Returns list of {title, url, file_id}."""
    from notebooklm._research import ResearchAPI
    research = ResearchAPI(client._core)
    result = await research.start(nb_id, query, source="drive", mode="fast")
    if not result:
        return []

    # Poll for results
    for _ in range(30):
        await asyncio.sleep(1)
        status = await research.poll(nb_id)
        if status and status.get("sources"):
            break
    else:
        return []

    sources = status.get("sources", [])
    drive_files = []
    for s in sources:
        url = s.get("url", "")
        title = s.get("title", "")
        file_id = extract_drive_file_id(url)
        if file_id and title:
            drive_files.append({"title": title, "url": url, "file_id": file_id})

    return drive_files


async def add_drive_files_to_notebook(client, nb_id, drive_files):
    """Add Drive files as proper Drive sources (not web URLs)."""
    from notebooklm._sources import SourcesAPI
    sources_api = SourcesAPI(client._core)
    added = 0
    for i, f in enumerate(drive_files):
        print(f"  [{i+1}/{len(drive_files)}] Adding: {f['title'][:60]}...", end=" ", flush=True)
        try:
            await sources_api.add_drive(
                notebook_id=nb_id,
                file_id=f["file_id"],
                title=f["title"],
                mime_type="application/pdf",
            )
            added += 1
            print("OK")
        except Exception as e:
            print(f"FAILED ({e})")
    return added


# ── Main Pipeline ─────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="YouTube + Drive Macro Research Pipeline")
    parser.add_argument("--days", type=int, default=3, help="Look back N days (default: 3)")
    parser.add_argument("--date", type=str, default=None, help="Target date YYYY-MM-DD (default: today)")
    parser.add_argument("--topic", type=str, default=None, help="Filter by topic keyword")
    parser.add_argument("--max-videos", type=int, default=20, help="Max videos to add to NotebookLM (default: 20)")
    parser.add_argument("--max-per-channel", type=int, default=10, help="Max videos to fetch per channel (default: 10)")
    parser.add_argument("--skip-infographic", action="store_true", help="Skip infographic generation")
    parser.add_argument("--skip-drive", action="store_true", help="Skip Google Drive sources")
    parser.add_argument("--skip-youtube", action="store_true", help="Skip YouTube sources")
    parser.add_argument("--skip-news", action="store_true", help="Skip news + Telegram sources")
    parser.add_argument("--drive-folder", type=str, default="0.research", help="Google Drive folder name (default: 0.research)")
    parser.add_argument("--language", type=str, default="en", help="Output language (default: en)")
    args = parser.parse_args()

    if args.date:
        target_date = datetime.strptime(args.date, "%Y-%m-%d")
    else:
        target_date = datetime.now()

    report_label = target_date.strftime("%Y-%m-%d")
    date_before = target_date.strftime("%Y%m%d")
    date_after = (target_date - timedelta(days=args.days)).strftime("%Y%m%d")
    date_after_iso = (target_date - timedelta(days=args.days)).strftime("%Y-%m-%d")

    # Temp dir for infographic download (notebooklm CLI needs a file path)
    import tempfile
    tmp_dir = Path(tempfile.mkdtemp(prefix="ix_research_"))

    total_steps = 7
    print(f"{'='*60}")
    print(f"  Macro Research Pipeline")
    print(f"  Date: {report_label}  |  Range: {date_after}-{date_before}")
    src_parts = []
    if not args.skip_youtube: src_parts.append("YouTube")
    if not args.skip_drive: src_parts.append("Drive")
    if not args.skip_news: src_parts.append("News+Telegram")
    print(f"  Sources: {' + '.join(src_parts) or 'None'}")
    if args.topic:
        print(f"  Topic filter: {args.topic}")
    print(f"{'='*60}\n")

    # ── Step 1: Ensure NotebookLM auth ──
    print(f"[1/{total_steps}] Authenticating NotebookLM...")
    if not ensure_notebooklm_auth():
        print("  Cannot proceed without NotebookLM auth. Aborting.")
        sys.exit(1)
    client = await get_nlm_client()

    # ── Step 2: Fetch videos from all channels ──
    selected = []
    if not args.skip_youtube:
        print(f"\n[2/{total_steps}] Fetching videos from channels...")
        all_videos = []
        for ch in CHANNELS:
            print(f"  Scanning: {ch['name']}...", end=" ", flush=True)
            videos = fetch_channel_videos(ch["url"], args.max_per_channel, date_after, date_before)
            for v in videos:
                v["channel"] = ch["name"]
            all_videos.extend(videos)
            print(f"{len(videos)} videos")

        print(f"\n  Total videos fetched: {len(all_videos)}")

        # ── Step 3: Score and rank videos ──
        print(f"\n[3/{total_steps}] Scoring and ranking videos...")
        for v in all_videos:
            v["score"] = score_video(v, args.topic)

        all_videos.sort(key=lambda v: v["score"], reverse=True)
        selected = all_videos[:args.max_videos]

        print(f"  Selected top {len(selected)} videos:")
        for i, v in enumerate(selected):
            print(f"    {i+1:2d}. [{v['score']:2d}] {v['channel']}: {v['title'][:70]}")

        with open(tmp_dir / "selected_videos.json", "w", encoding="utf-8") as f:
            json.dump(selected, f, indent=2, ensure_ascii=False)
    else:
        print(f"\n[2/{total_steps}] Skipping YouTube fetch.")
        print(f"[3/{total_steps}] Skipping video scoring.")

    # ── Step 4: Create NotebookLM notebook ──
    print(f"\n[4/{total_steps}] Creating NotebookLM notebook...")
    title = f"Macro Intel - {report_label}"
    if args.topic:
        title += f" ({args.topic})"
    stdout, rc = notebooklm_cmd(f'create "{title}"', timeout=60)
    if rc != 0:
        print("  FAILED to create notebook. Aborting.")
        sys.exit(1)

    nb_id = None
    for word in stdout.split():
        if len(word) > 30 and "-" in word:
            nb_id = word
            break
    if not nb_id:
        print(f"  Could not parse notebook ID from: {stdout}")
        sys.exit(1)
    print(f"  Notebook: {nb_id}")

    # ── Step 5: Add all sources ──
    print(f"\n[5/{total_steps}] Adding sources to NotebookLM...")

    added_yt = 0
    added_drive = 0

    # Add YouTube videos
    if selected:
        print(f"\n  --- YouTube Videos ({len(selected)}) ---")
        for i, v in enumerate(selected):
            print(f"  [{i+1}/{len(selected)}] Adding: {v['title'][:60]}...", end=" ", flush=True)
            stdout, rc = notebooklm_cmd(f'source add --notebook "{nb_id}" "{v["url"]}"', timeout=60)
            if rc == 0:
                added_yt += 1
                print("OK")
            else:
                print("FAILED")
        print(f"\n  YouTube: {added_yt}/{len(selected)} added")

    # Search Drive and add files as proper Drive sources (scoped to folder)
    if not args.skip_drive:
        print(f"\n  --- Google Drive ({args.drive_folder}) ---")
        print(f"  Searching Drive folder '{args.drive_folder}'...")

        drive_files = await search_drive_via_nlm(client, nb_id, args.drive_folder)

        if drive_files:
            print(f"  Found {len(drive_files)} Drive file(s):")
            for i, f in enumerate(drive_files):
                print(f"    {i+1:2d}. {f['title'][:70]}")

            with open(tmp_dir / "drive_files.json", "w", encoding="utf-8") as fp:
                json.dump(drive_files, fp, indent=2, ensure_ascii=False)

            print(f"\n  Adding Drive files as sources...")
            added_drive = await add_drive_files_to_notebook(client, nb_id, drive_files)
            print(f"\n  Drive: {added_drive}/{len(drive_files)} added")
        else:
            print(f"  No Drive files found.")

    # Add news items and Telegram messages as text sources
    added_news = 0
    added_telegram = 0
    if not args.skip_news:
        print(f"\n  --- News & Telegram ---")
        print(f"  Fetching from database (last {args.days} days)...")
        try:
            news_text, telegram_text, news_count, telegram_count = fetch_news_and_telegram(args.days)

            if news_text:
                print(f"  Found {news_count} news items. Adding as source...", end=" ", flush=True)
                # Write to temp file and add as text source
                news_file = tmp_dir / "_news_source.md"
                with open(news_file, "w", encoding="utf-8") as f:
                    f.write(news_text)
                stdout, rc = notebooklm_cmd(
                    f'source add --notebook "{nb_id}" --type text --title "News Headlines ({report_label})" "{news_file}"',
                    timeout=60,
                )
                if rc == 0:
                    added_news = news_count
                    print("OK")
                else:
                    print("FAILED")
                news_file.unlink(missing_ok=True)
            else:
                print(f"  No news items found.")

            if telegram_text:
                print(f"  Found {telegram_count} Telegram messages. Adding as source...", end=" ", flush=True)
                tg_file = tmp_dir / "_telegram_source.md"
                with open(tg_file, "w", encoding="utf-8") as f:
                    f.write(telegram_text)
                stdout, rc = notebooklm_cmd(
                    f'source add --notebook "{nb_id}" --type text --title "Telegram Messages ({report_label})" "{tg_file}"',
                    timeout=60,
                )
                if rc == 0:
                    added_telegram = telegram_count
                    print("OK")
                else:
                    print("FAILED")
                tg_file.unlink(missing_ok=True)
            else:
                print(f"  No Telegram messages found.")

        except Exception as e:
            print(f"  [WARN] Could not fetch news/telegram: {e}")

    print(f"\n  Total sources: {added_yt} videos + {added_drive} Drive files"
          f" + {added_news} news + {added_telegram} Telegram msgs")

    # ── Step 6: Ask NotebookLM for analysis ──
    print(f"\n[6/{total_steps}] Requesting NotebookLM analysis...")

    briefing_text = None
    scorecard_text = None
    takeaways_text = None
    infographic_bytes = None

    print("  Generating comprehensive briefing...")
    briefing_prompt = (
        "Based on ALL sources, create a comprehensive macro intelligence briefing covering: "
        "1) Current state of global markets and key risks, "
        "2) Key themes - where experts agree and disagree, "
        "3) Geopolitics and their market impact, "
        "4) Credit and financial system risks, "
        "5) Capital rotation trends, "
        "6) AI and technology impact on markets, "
        "7) Fed and monetary policy outlook, "
        "8) Forward-looking predictions and what to watch. "
        "Be specific, cite which experts said what."
    )
    stdout, rc = notebooklm_cmd(f'ask --notebook "{nb_id}" "{briefing_prompt}"', timeout=120)
    if rc == 0:
        briefing_text = f"# Macro Intelligence Briefing — {report_label}\n\n" + stdout.replace("Answer:", "").strip()
        print("  Briefing OK.")

    print("  Generating risk scorecard...")
    risk_prompt = (
        "Create a risk scorecard rating these areas 1-10: "
        "Geopolitical Risk, Credit Market Risk, Equity Market Risk, "
        "Inflation Risk, Liquidity Risk, Technology Disruption Risk. "
        "For each cite the key expert and explain why."
    )
    stdout, rc = notebooklm_cmd(f'ask --notebook "{nb_id}" "{risk_prompt}"', timeout=120)
    if rc == 0:
        scorecard_text = f"# Risk Scorecard — {report_label}\n\n" + stdout.replace("Answer:", "").strip()
        print("  Risk scorecard OK.")

    print("  Generating executive takeaways...")
    takeaway_prompt = (
        "In exactly 3 bullet points, give the most important actionable takeaways "
        "an institutional investor should focus on this week. Be specific about positioning."
    )
    stdout, rc = notebooklm_cmd(f'ask --notebook "{nb_id}" "{takeaway_prompt}"', timeout=120)
    if rc == 0:
        takeaways_text = f"# Executive Takeaways — {report_label}\n\n" + stdout.replace("Answer:", "").strip()
        print("  Takeaways OK.")

    # ── Step 7: Generate infographic ──
    if not args.skip_infographic:
        print(f"\n[7/{total_steps}] Generating infographic via NotebookLM...")
        infographic_prompt = (
            "Create a comprehensive macro intelligence infographic in English covering: "
            "aggregate risk levels, asset class sentiment signals, capital rotation from "
            "big tech to real assets, key expert positions and stances, top 3 actionable "
            "investment takeaways, and what to watch next week."
        )
        stdout, rc = notebooklm_cmd(
            f'generate infographic --notebook "{nb_id}" --language {args.language} '
            f'"{infographic_prompt}" --wait',
            timeout=300
        )
        if rc == 0:
            print("  Infographic generated. Downloading...")
            infographic_tmp = tmp_dir / "infographic.png"
            stdout, rc = notebooklm_cmd(
                f'download infographic --notebook "{nb_id}" "{infographic_tmp}"',
                timeout=60
            )
            if rc == 0 and infographic_tmp.is_file():
                infographic_bytes = infographic_tmp.read_bytes()
                infographic_tmp.unlink(missing_ok=True)
                print(f"  Infographic OK ({len(infographic_bytes):,} bytes).")
            else:
                print(f"  Failed to download infographic.")
    else:
        print(f"\n[7/{total_steps}] Skipping infographic generation.")

    # ── Save to database ──
    print(f"\n  Saving report to database...")
    try:
        from ix.db.conn import Session as DBSession
        from ix.db.models.research_report import ResearchReport

        report_date = target_date.date() if hasattr(target_date, 'date') else target_date

        sources_data = {}
        if selected:
            sources_data["selected_videos"] = selected
        if drive_files:
            sources_data["drive_files"] = drive_files

        with DBSession() as db:
            existing = db.query(ResearchReport).filter(ResearchReport.date == report_date).first()
            if existing:
                existing.briefing = briefing_text
                existing.risk_scorecard = scorecard_text
                existing.takeaways = takeaways_text
                if infographic_bytes:
                    existing.infographic = infographic_bytes
                existing.sources = sources_data
                print(f"  Updated existing report for {report_label}.")
            else:
                report = ResearchReport(
                    date=report_date,
                    briefing=briefing_text,
                    risk_scorecard=scorecard_text,
                    takeaways=takeaways_text,
                    infographic=infographic_bytes,
                    sources=sources_data,
                )
                db.add(report)
                print(f"  Saved new report for {report_label}.")

    except Exception as e:
        print(f"  [ERROR] Failed to save to database: {e}")

    # ── Cleanup ──
    print(f"\n  Cleaning up NotebookLM notebook...")
    stdout, rc = notebooklm_cmd(f'delete -n "{nb_id}" -y', timeout=30)
    if rc == 0:
        print(f"  Notebook {nb_id[:12]}... deleted.")
    else:
        print(f"  [WARN] Could not delete notebook. Delete manually: notebooklm delete {nb_id}")

    # Clean up temp dir
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)

    # ── Done ──
    print(f"\n{'='*60}")
    print(f"  DONE! Report saved to database.")
    print(f"  Sources: {added_yt} videos + {added_drive} Drive + {added_news} news + {added_telegram} Telegram")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
