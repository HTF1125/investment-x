"""
Collect-Only Macro Research Pipeline
Runs all data source collection (YouTube, RSS, Telegram, Central Banks,
Macro Data, Firecrawl Reports) without NotebookLM.

Saves all collected data to a timestamped output directory as markdown/JSON files.

Usage:
    python ix/scripts/collect_sources.py                    # last 7 days, all sources
    python ix/scripts/collect_sources.py --days 3           # last 3 days
    python ix/scripts/collect_sources.py --topic "inflation" # filter YouTube by topic
    python ix/scripts/collect_sources.py --skip-youtube      # skip any source
    python ix/scripts/collect_sources.py --skip-firecrawl    # skip Firecrawl (slow)
    python ix/scripts/collect_sources.py -o ./my_output      # custom output dir
"""

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Ensure project root is on path for ix imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

# Import everything from macro_research
from ix.scripts.macro_research import (
    CHANNELS,
    RSS_FEEDS,
    RESEARCH_SITES,
    RESEARCH_QUERIES,
    TELEGRAM_CHANNELS,
    CENTRAL_BANKS,
    fetch_channel_videos,
    score_video,
    scrape_rss_news,
    scrape_telegram_direct,
    fetch_central_bank_urls,
    build_macro_data_snapshot,
    scrape_investment_reports,
)


async def main():
    parser = argparse.ArgumentParser(description="Collect-Only Macro Research Pipeline")
    parser.add_argument("--days", type=int, default=7, help="Look back N days (default: 7)")
    parser.add_argument("--date", type=str, default=None, help="Target date YYYY-MM-DD")
    parser.add_argument("--topic", type=str, default=None, help="Filter YouTube by topic")
    parser.add_argument("--max-videos", type=int, default=30, help="Max YouTube videos (default: 30)")
    parser.add_argument("--max-per-channel", type=int, default=10, help="Max videos per channel (default: 10)")
    parser.add_argument("--max-firecrawl-sites", type=int, default=30, help="Max Firecrawl sites (default: 30)")
    parser.add_argument("--skip-youtube", action="store_true")
    parser.add_argument("--skip-news", action="store_true")
    parser.add_argument("--skip-telegram", action="store_true")
    parser.add_argument("--skip-central-banks", action="store_true")
    parser.add_argument("--skip-data", action="store_true")
    parser.add_argument("--skip-firecrawl", action="store_true")
    parser.add_argument("-o", "--output", type=str, default=None, help="Output directory")
    args = parser.parse_args()

    target_date = datetime.strptime(args.date, "%Y-%m-%d") if args.date else datetime.now()
    report_label = target_date.strftime("%Y-%m-%d")
    date_before = target_date.strftime("%Y%m%d")
    date_after = (target_date - timedelta(days=args.days)).strftime("%Y%m%d")

    # Output directory
    if args.output:
        out_dir = Path(args.output)
    else:
        out_dir = Path(__file__).resolve().parent.parent.parent / "data" / "collected" / report_label
    out_dir.mkdir(parents=True, exist_ok=True)

    src_parts = []
    if not args.skip_youtube:
        src_parts.append(f"YouTube({len(CHANNELS)}ch)")
    if not args.skip_news:
        src_parts.append(f"RSS({len(RSS_FEEDS)})")
    if not args.skip_telegram:
        src_parts.append(f"Telegram({len(TELEGRAM_CHANNELS)}ch)")
    if not args.skip_central_banks:
        src_parts.append(f"Central Banks({len(CENTRAL_BANKS)})")
    if not args.skip_data:
        src_parts.append("Macro Data")
    if not args.skip_firecrawl:
        src_parts.append(f"Firecrawl({len(RESEARCH_SITES)})")

    print(f"{'=' * 60}")
    print(f"  Collect-Only Macro Research Pipeline")
    print(f"  Date: {report_label}  |  Range: {date_after}-{date_before}")
    print(f"  Sources: {' + '.join(src_parts)}")
    print(f"  Output: {out_dir}")
    if args.topic:
        print(f"  Topic filter: {args.topic}")
    print(f"{'=' * 60}\n")

    results = {}
    step = 0
    total_steps = sum([
        not args.skip_youtube,
        not args.skip_news,
        not args.skip_telegram,
        not args.skip_central_banks,
        not args.skip_data,
        not args.skip_firecrawl,
    ])

    # ── 1. YouTube ──
    if not args.skip_youtube:
        step += 1
        print(f"[{step}/{total_steps}] Fetching videos from {len(CHANNELS)} channels...")
        all_videos = []
        for ch in CHANNELS:
            print(f"  {ch['name']}...", end=" ", flush=True)
            videos = fetch_channel_videos(
                ch["url"], args.max_per_channel, date_after, date_before
            )
            for v in videos:
                v["channel"] = ch["name"]
            all_videos.extend(videos)
            print(f"{len(videos)} videos")

        # Score and rank
        for v in all_videos:
            v["score"] = score_video(v, args.topic)
        all_videos.sort(key=lambda v: v["score"], reverse=True)
        selected = all_videos[:args.max_videos]

        print(f"\n  Total: {len(all_videos)} fetched, top {len(selected)} selected")
        if selected:
            for i, v in enumerate(selected[:10]):
                print(f"    {i + 1:2d}. [{v['score']:2d}] {v['channel']}: {v['title'][:65]}")
            if len(selected) > 10:
                print(f"    ... and {len(selected) - 10} more")

        # Save
        with open(out_dir / "youtube_videos.json", "w", encoding="utf-8") as f:
            json.dump(selected, f, indent=2, ensure_ascii=False)
        results["youtube"] = len(selected)
        print(f"  Saved {len(selected)} videos to youtube_videos.json\n")

    # ── 2. RSS News ──
    if not args.skip_news:
        step += 1
        print(f"[{step}/{total_steps}] Scraping {len(RSS_FEEDS)} RSS feeds (last {args.days} days)...")
        news_text, news_count = scrape_rss_news(args.days)
        if news_text:
            with open(out_dir / "rss_news.md", "w", encoding="utf-8") as f:
                f.write(news_text)
            results["rss_news"] = news_count
            print(f"  Scraped {news_count} articles, saved to rss_news.md\n")
        else:
            results["rss_news"] = 0
            print(f"  No articles found.\n")

    # ── 3. Telegram ──
    if not args.skip_telegram:
        step += 1
        print(f"[{step}/{total_steps}] Scraping {len(TELEGRAM_CHANNELS)} Telegram channels (last {args.days} days)...")
        telegram_text, tg_count = await scrape_telegram_direct(args.days)
        if telegram_text:
            with open(out_dir / "telegram_messages.md", "w", encoding="utf-8") as f:
                f.write(telegram_text)
            results["telegram"] = tg_count
            print(f"  Scraped {tg_count} messages, saved to telegram_messages.md\n")
        else:
            results["telegram"] = 0
            print(f"  No messages found.\n")

    # ── 4. Central Banks ──
    if not args.skip_central_banks:
        step += 1
        print(f"[{step}/{total_steps}] Fetching central bank minutes/statements...")
        cb_urls = fetch_central_bank_urls(days=90)
        if cb_urls:
            with open(out_dir / "central_banks.json", "w", encoding="utf-8") as f:
                json.dump(cb_urls, f, indent=2, ensure_ascii=False)

            # Also save as markdown for easy reading
            cb_text = "# Central Bank Documents\n\n"
            for cb in cb_urls:
                cb_text += f"## [{cb['name']}] {cb['title']}\n"
                cb_text += f"- URL: {cb['url']}\n"
                cb_text += f"- Date: {cb.get('date_str', 'N/A')}\n\n"
            with open(out_dir / "central_banks.md", "w", encoding="utf-8") as f:
                f.write(cb_text)

            results["central_banks"] = len(cb_urls)
            print(f"  Found {len(cb_urls)} documents:")
            for cb in cb_urls:
                print(f"    [{cb['name']}] {cb['title'][:60]}")
            print(f"  Saved to central_banks.json + .md\n")
        else:
            results["central_banks"] = 0
            print(f"  No recent documents found.\n")

    # ── 5. Macro Data Snapshot ──
    if not args.skip_data:
        step += 1
        print(f"[{step}/{total_steps}] Building macro data snapshot from timeseries DB...")
        data_text, data_count = build_macro_data_snapshot()
        if data_text:
            with open(out_dir / "macro_data.md", "w", encoding="utf-8") as f:
                f.write(data_text)
            results["macro_data"] = data_count
            print(f"  Built snapshot with {data_count} indicators, saved to macro_data.md\n")
        else:
            results["macro_data"] = 0
            print(f"  No macro data available.\n")

    # ── 6. Firecrawl Investment Reports ──
    if not args.skip_firecrawl:
        step += 1
        print(f"[{step}/{total_steps}] Scraping investment reports via Firecrawl ({args.max_firecrawl_sites} sites)...")
        reports_text, reports_count = scrape_investment_reports(
            days=args.days, max_sites=args.max_firecrawl_sites
        )
        if reports_text:
            with open(out_dir / "investment_reports.md", "w", encoding="utf-8") as f:
                f.write(reports_text)
            results["firecrawl_reports"] = reports_count
            print(f"  Scraped {reports_count} articles, saved to investment_reports.md\n")
        else:
            results["firecrawl_reports"] = 0
            print(f"  No reports scraped.\n")

    # ── Summary ──
    # Save manifest
    manifest = {
        "date": report_label,
        "range": f"{date_after}-{date_before}",
        "days": args.days,
        "topic": args.topic,
        "collected_at": datetime.now().isoformat(),
        "results": results,
        "output_dir": str(out_dir),
    }
    with open(out_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"{'=' * 60}")
    print(f"  Collection Complete — {report_label}")
    print(f"  Output: {out_dir}")
    print(f"")
    total_items = 0
    for source, count in results.items():
        label = source.replace("_", " ").title()
        print(f"    {label:<25} {count:>6}")
        total_items += count
    print(f"    {'─' * 32}")
    print(f"    {'Total':<25} {total_items:>6}")
    print(f"")

    # List output files
    files = sorted(out_dir.glob("*"))
    print(f"  Files:")
    for fp in files:
        size = fp.stat().st_size
        if size > 1_000_000:
            size_str = f"{size / 1_000_000:.1f}MB"
        elif size > 1_000:
            size_str = f"{size / 1_000:.0f}KB"
        else:
            size_str = f"{size}B"
        print(f"    {fp.name:<35} {size_str:>8}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    asyncio.run(main())
