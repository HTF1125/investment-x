"""
Automated Multi-Source Macro Research Pipeline
1. Pulls recent videos from configured YouTube channels via yt-dlp
2. Searches Google Drive for research PDFs (via NotebookLM)
3. Scrapes RSS news feeds directly (no DB dependency)
4. Reads recent Telegram channel messages directly via telethon
5. Fetches recent central bank minutes/statements (Fed, ECB, BOK, BOJ, BOE, RBA)
6. Builds a macro data snapshot from the timeseries DB (indicators, CFTC, performance)
7. Creates a NotebookLM notebook and adds all sources
8. Generates briefing, takeaways, risk scorecard, infographic, and slide deck

Usage:
    python scripts/macro_research.py                    # last 3 days, all sources
    python scripts/macro_research.py --days 7           # last 7 days
    python scripts/macro_research.py --date 2026-02-15  # specific date
    python scripts/macro_research.py --topic "inflation" # filter by topic
    python scripts/macro_research.py --skip-drive        # skip Google Drive sources
    python scripts/macro_research.py --skip-youtube      # skip YouTube
    python scripts/macro_research.py --skip-news         # skip RSS news
    python scripts/macro_research.py --skip-telegram     # skip Telegram
    python scripts/macro_research.py --skip-central-banks # skip central bank minutes
    python scripts/macro_research.py --skip-data         # skip macro data snapshot
"""

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# Ensure project root is on path for ix imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# Load .env BEFORE any ix imports (modules read env vars at import time)
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")


# ── Channel Configuration ──────────────────────────────────────────
CHANNELS = [
    {"url": "https://www.youtube.com/@ForwardGuidanceBW", "name": "Forward Guidance"},
    {"url": "https://www.youtube.com/@ARKInvest2015", "name": "ARK Invest"},
    {"url": "https://www.youtube.com/@RealVisionFinance", "name": "Real Vision"},
    {
        "url": "https://www.youtube.com/@RealEismanPlaybook",
        "name": "Real Eisman Playbook",
    },
    {"url": "https://www.youtube.com/@DoubleLineCapital", "name": "DoubleLine Capital"},
    {"url": "https://www.youtube.com/@MilkRoadMacro", "name": "Milk Road Macro"},
    {"url": "https://www.youtube.com/@MilkRoadDaily", "name": "Milk Road Daily"},
    {"url": "https://www.youtube.com/@MilkRoadAI", "name": "Milk Road AI"},
    {"url": "https://www.youtube.com/@RaoulPalTJM", "name": "Raoul Pal TJM"},
    {"url": "https://www.youtube.com/@business", "name": "Bloomberg"},
    {"url": "https://www.youtube.com/@StansberryMedia", "name": "Stansberry Media"},
    {
        "url": "https://www.youtube.com/@maggielake-talkingmarkets",
        "name": "Maggie Lake",
    },
    {"url": "https://www.youtube.com/@bravosresearch", "name": "Bravos Research"},
    {"url": "https://www.youtube.com/@JamieTree", "name": "JamieTree"},
    # {"url": "https://www.youtube.com/@C-Documentary", "name": "C-Documentary"},
]

# ── RSS News Feeds ─────────────────────────────────────────────────
RSS_FEEDS = {
    "Yahoo Finance": "https://finance.yahoo.com/rss/",
    "CNBC Finance": "https://www.cnbc.com/id/10000664/device/rss/rss.html",
    "MarketWatch": "http://feeds.marketwatch.com/marketwatch/topstories/",
    "Investing.com": "https://www.investing.com/rss/news.rss",
    "WSJ Markets": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
}

# ── Telegram Channels (single source of truth in ix.misc.telegram) ──
from ix.misc.telegram import (
    CHANNELS_TO_SCRAPE as TELEGRAM_CHANNELS,
    SESSION_NAME as _TG_SESSION,
    API_ID as _TG_API_ID,
    API_HASH as _TG_API_HASH,
)

# ── Central Bank Configuration ─────────────────────────────────────
CENTRAL_BANKS = [
    {
        "name": "Federal Reserve (FOMC)",
        "rss": "https://www.federalreserve.gov/feeds/press_monetary.xml",
        "minutes_base": "https://www.federalreserve.gov/monetarypolicy/fomcminutes{date}.htm",
        "format": "html",
    },
    {
        "name": "ECB",
        "listing": "https://www.ecb.europa.eu/press/accounts/html/index.en.html",
        "format": "html",
    },
    {
        "name": "Bank of Korea",
        "listing": "https://www.bok.or.kr/eng/bbs/E0000737/list.do?menuNo=400203",
        "format": "html",
    },
    {
        "name": "Bank of Japan",
        "rss": "https://www.boj.or.jp/en/rss/whatsnew.xml",
        "format": "pdf",
    },
    {
        "name": "Bank of England",
        "listing": "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes",
        "format": "html",
    },
    {
        "name": "Reserve Bank of Australia",
        "rss": "https://www.rba.gov.au/rss/rss-cb-media-releases.xml",
        "format": "html",
    },
]

# ── Macro Data Series for Snapshot ─────────────────────────────────
# { display_name: timeseries_code }
MACRO_INDICATORS = {
    # Equity indices
    "S&P 500": "SPX INDEX:PX_LAST",
    "Nasdaq 100": "CCMP INDEX:PX_LAST",
    "KOSPI": "KOSPI INDEX:PX_LAST",
    "Nikkei 225": "NKY INDEX:PX_LAST",
    "Euro Stoxx 50": "SX5E INDEX:PX_LAST",
    "MSCI EM": "891800:FG_TOTAL_RET_IDX",
    "Shanghai Composite": "SHCOMP INDEX:PX_LAST",
    "DAX": "DAX INDEX:PX_LAST",
    "Hang Seng": "HSI INDEX:PX_LAST",
    "KOSDAQ": "KOSDAQ:PX_LAST",
    # Rates & Bonds
    "US 10Y Yield": "TRYUS10Y:PX_YTM",
    "Korea 10Y Yield": "TRYKR10Y:PX_YTM",
    "Germany 10Y Yield": "TRYDE10Y:PX_YTM",
    "Japan 10Y Yield": "TRYJP10Y:PX_YTM",
    # Volatility
    "VIX": "VIX INDEX:PX_LAST",
    "VIX3M": "VIX3M INDEX:PX_LAST",
    # Credit
    "HY OAS Spread": "BAMLH0A0HYM2",
    # FX
    "DXY": "DXY INDEX:PX_LAST",
    "USD/KRW": "USDKRW CURNCY:PX_LAST",
    "EUR/USD": "EURUSD CURNCY:PX_LAST",
    "USD/JPY": "USDJPY CURNCY:PX_LAST",
    # Commodities
    "Gold": "GOLDCOMP:PX_LAST",
    "Copper": "COPPER CURNCY:PX_LAST",
    "WTI Crude": "CL1 COMDTY:PX_LAST",
}

CFTC_ASSETS = {
    "S&P 500": ("CFTNCLALLSP500EMINCMEF_US", "CFTNCSALLSP500EMINCMEF_US"),
    "USD": ("CFTNCLALLJUSDNYBTF_US", "CFTNCSALLJUSDNYBTF_US"),
    "Gold": ("CFTNCLALLGOLDCOMF_US", "CFTNCSALLGOLDCOMF_US"),
    "JPY": ("CFTNCLALLYENCMEF_US", "CFTNCSALLYENCMEF_US"),
    "UST 10Y": ("CFTNCLALLTN10YCBOTF_US", "CFTNCSALLTN10YCBOTF_US"),
}


# ═══════════════════════════════════════════════════════════════════
# Helper utilities
# ═══════════════════════════════════════════════════════════════════


def run_cmd(cmd, timeout=120):
    """Run a command and return (stdout, stderr, returncode)."""
    import shlex

    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return result.stdout.strip(), result.stderr.strip(), result.returncode


# ═══════════════════════════════════════════════════════════════════
# 1. YouTube Functions
# ═══════════════════════════════════════════════════════════════════


def fetch_channel_videos(
    channel_url, max_per_channel=15, date_after=None, date_before=None
):
    """Fetch recent videos from a channel using yt-dlp."""
    target_url = f"{channel_url}/videos"
    if date_after or date_before:
        cmd = ["yt-dlp", "-j", "--playlist-end", str(max_per_channel * 5)]
        if date_after:
            cmd += ["--dateafter", str(date_after)]
        if date_before:
            cmd += ["--datebefore", str(date_before)]
        cmd.append(target_url)
    else:
        cmd = [
            "yt-dlp",
            "--flat-playlist",
            "-j",
            "--playlist-end",
            str(max_per_channel),
            target_url,
        ]

    stdout, stderr, rc = run_cmd(cmd, timeout=120)
    if rc != 0:
        return []
    videos = []
    for line in stdout.splitlines():
        try:
            d = json.loads(line)
            videos.append(
                {
                    "id": d.get("id", ""),
                    "title": d.get("title", ""),
                    "upload_date": d.get("upload_date", ""),
                    "duration": d.get("duration_string", ""),
                    "views": d.get("view_count", 0),
                    "url": f"https://www.youtube.com/watch?v={d.get('id', '')}",
                }
            )
        except json.JSONDecodeError:
            continue
    return videos[:max_per_channel]


def score_video(video, topic=None):
    """Score a video for relevance. Higher = more relevant."""
    score = 0
    title_lower = video["title"].lower()
    views = video.get("views", 0) or 0
    if views > 100000:
        score += 5
    elif views > 50000:
        score += 4
    elif views > 10000:
        score += 3
    elif views > 5000:
        score += 2
    elif views > 1000:
        score += 1

    macro_keywords = [
        "macro",
        "fed",
        "inflation",
        "recession",
        "market",
        "economy",
        "oil",
        "gold",
        "silver",
        "bond",
        "yield",
        "credit",
        "risk",
        "crash",
        "rally",
        "rotation",
        "dollar",
        "geopolit",
        "iran",
        "china",
        "tariff",
        "war",
        "ai",
        "tech",
        "bubble",
        "debt",
        "liquidity",
        "commodity",
        "energy",
        "weekly",
        "roundup",
        "wrap",
        "outlook",
        "forecast",
        "prediction",
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


# ═══════════════════════════════════════════════════════════════════
# 2. RSS News Scraping (direct, no DB)
# ═══════════════════════════════════════════════════════════════════


def scrape_rss_news(days=3):
    """Scrape RSS feeds directly and return formatted text.

    Returns (news_text, article_count) — no database dependency.
    """
    try:
        import feedparser
    except ImportError:
        print("  [WARN] feedparser not installed. pip install feedparser")
        return None, 0

    cutoff = datetime.utcnow() - timedelta(days=days)
    articles = []

    for source_name, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:50]:
                # Parse published date
                pub_date = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        pub_date = datetime(*entry.published_parsed[:6])
                    except Exception:
                        pass
                if not pub_date:
                    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
                        try:
                            pub_date = datetime(*entry.updated_parsed[:6])
                        except Exception:
                            pass

                if pub_date and pub_date < cutoff:
                    continue

                title = getattr(entry, "title", "")
                summary = getattr(entry, "summary", "")
                if summary:
                    # Strip HTML tags
                    summary = re.sub(r"<[^>]+>", "", summary)[:500]

                date_str = pub_date.strftime("%Y-%m-%d %H:%M") if pub_date else ""
                articles.append(
                    {
                        "source": source_name,
                        "date": date_str,
                        "title": title,
                        "summary": summary,
                        "sort_key": pub_date or datetime.min,
                    }
                )
        except Exception as e:
            print(f"  [WARN] RSS feed {source_name}: {e}")

    if not articles:
        return None, 0

    # Sort by date descending
    articles.sort(key=lambda a: a["sort_key"], reverse=True)

    text = f"# Financial News Headlines (last {days} days)\n\n"
    for a in articles:
        text += f"[{a['date']}] {a['source']}: {a['title']}\n"
        if a["summary"]:
            text += f"{a['summary']}\n"
        text += "\n---\n\n"
        if len(text) > 200_000:
            break

    return text, len(articles)


# ═══════════════════════════════════════════════════════════════════
# 3. Telegram Scraping (direct via telethon, no DB)
# ═══════════════════════════════════════════════════════════════════


async def scrape_telegram_direct(days=3, max_per_channel=30):
    """Read recent Telegram messages directly via telethon.

    Returns (telegram_text, msg_count) — no database dependency.
    Uses session/credentials from ix.misc.telegram module.
    """
    try:
        from telethon import TelegramClient
    except ImportError:
        print("  [WARN] telethon not installed. pip install telethon")
        return None, 0

    if not _TG_API_ID or not _TG_API_HASH:
        print("  [WARN] TELEGRAM_API_ID/TELEGRAM_API_HASH not set.")
        return None, 0

    client = TelegramClient(_TG_SESSION, int(_TG_API_ID), _TG_API_HASH)

    cutoff = datetime.utcnow() - timedelta(days=days)
    all_msgs = []

    try:
        await client.connect()
        if not await client.is_user_authorized():
            print("  [WARN] Telegram session expired. Run telethon login to re-auth.")
            return None, 0

        for channel_url in TELEGRAM_CHANNELS:
            channel_name = channel_url.split("/")[-1]
            try:
                entity = await client.get_input_entity(channel_url)
                async for msg in client.iter_messages(entity, limit=max_per_channel):
                    if msg.date and msg.date.replace(tzinfo=None) < cutoff:
                        break
                    if msg.message:
                        date_str = (
                            msg.date.strftime("%Y-%m-%d %H:%M") if msg.date else ""
                        )
                        all_msgs.append(
                            {
                                "channel": channel_name,
                                "date": date_str,
                                "text": msg.message[:2000],
                                "sort_key": (
                                    msg.date.replace(tzinfo=None)
                                    if msg.date
                                    else datetime.min
                                ),
                            }
                        )
            except Exception as e:
                # Silently skip channels we can't access
                pass

        await client.disconnect()
    except Exception as e:
        print(f"  [WARN] Telegram connection error: {e}")
        return None, 0

    if not all_msgs:
        return None, 0

    all_msgs.sort(key=lambda m: m["sort_key"], reverse=True)

    text = f"# Telegram Channel Messages (last {days} days)\n\n"
    for m in all_msgs:
        text += f"[{m['date']}] {m['channel']}: {m['text']}\n\n---\n\n"
        if len(text) > 200_000:
            break

    return text, len(all_msgs)


# ═══════════════════════════════════════════════════════════════════
# 4. Central Bank Minutes Fetcher
# ═══════════════════════════════════════════════════════════════════


def fetch_central_bank_urls(days=90):
    """Fetch recent central bank minutes/statement URLs via RSS and listing pages.

    Uses a wider window (default 90 days) since meetings are every 6-8 weeks.
    Returns list of {name, url, title, date_str}.
    """
    try:
        import feedparser
    except ImportError:
        print("  [WARN] feedparser not installed.")
        return []

    from urllib.request import Request, urlopen

    cutoff = datetime.utcnow() - timedelta(days=days)
    results = []

    # ── Federal Reserve ──
    try:
        feed = feedparser.parse(
            "https://www.federalreserve.gov/feeds/press_monetary.xml"
        )
        for entry in feed.entries[:10]:
            pub_date = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                pub_date = datetime(*entry.published_parsed[:6])
            if pub_date and pub_date < cutoff:
                continue
            title = getattr(entry, "title", "")
            link = getattr(entry, "link", "")
            if link and (
                "minute" in title.lower()
                or "statement" in title.lower()
                or "press release" in title.lower()
            ):
                results.append(
                    {
                        "name": "Federal Reserve",
                        "url": link,
                        "title": title,
                        "date_str": pub_date.strftime("%Y-%m-%d") if pub_date else "",
                    }
                )
    except Exception as e:
        print(f"  [WARN] Fed RSS: {e}")

    # ── ECB ──
    try:
        feed = feedparser.parse("https://www.ecb.europa.eu/rss/press.html")
        for entry in feed.entries[:15]:
            pub_date = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                pub_date = datetime(*entry.published_parsed[:6])
            if pub_date and pub_date < cutoff:
                continue
            title = getattr(entry, "title", "")
            link = getattr(entry, "link", "")
            if link and (
                "monetary policy" in title.lower() or "account" in title.lower()
            ):
                results.append(
                    {
                        "name": "ECB",
                        "url": link,
                        "title": title,
                        "date_str": pub_date.strftime("%Y-%m-%d") if pub_date else "",
                    }
                )
    except Exception as e:
        print(f"  [WARN] ECB RSS: {e}")

    # ── Bank of Japan ──
    try:
        feed = feedparser.parse("https://www.boj.or.jp/en/rss/whatsnew.xml")
        for entry in feed.entries[:15]:
            pub_date = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                pub_date = datetime(*entry.published_parsed[:6])
            if pub_date and pub_date < cutoff:
                continue
            title = getattr(entry, "title", "")
            link = getattr(entry, "link", "")
            if link and (
                "monetary policy" in title.lower()
                or "minutes" in title.lower()
                or "outlook" in title.lower()
                or "statement" in title.lower()
            ):
                results.append(
                    {
                        "name": "Bank of Japan",
                        "url": link,
                        "title": title,
                        "date_str": pub_date.strftime("%Y-%m-%d") if pub_date else "",
                    }
                )
    except Exception as e:
        print(f"  [WARN] BOJ RSS: {e}")

    # ── Reserve Bank of Australia ──
    try:
        feed = feedparser.parse("https://www.rba.gov.au/rss/rss-cb-media-releases.xml")
        for entry in feed.entries[:10]:
            pub_date = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                pub_date = datetime(*entry.published_parsed[:6])
            if pub_date and pub_date < cutoff:
                continue
            title = getattr(entry, "title", "")
            link = getattr(entry, "link", "")
            if link and (
                "monetary" in title.lower()
                or "rate" in title.lower()
                or "minute" in title.lower()
                or "statement" in title.lower()
            ):
                results.append(
                    {
                        "name": "RBA",
                        "url": link,
                        "title": title,
                        "date_str": pub_date.strftime("%Y-%m-%d") if pub_date else "",
                    }
                )
    except Exception as e:
        print(f"  [WARN] RBA RSS: {e}")

    # ── Bank of England ──
    try:
        # BOE publishes minutes with the decision — try recent URLs by month
        now = datetime.utcnow()
        for months_back in range(4):
            dt = now - timedelta(days=months_back * 30)
            month_name = dt.strftime("%B").lower()
            year = dt.year
            url = f"https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/{year}/{month_name}-{year}"
            try:
                req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
                resp = urlopen(req, timeout=10)
                if resp.status == 200:
                    results.append(
                        {
                            "name": "Bank of England",
                            "url": url,
                            "title": f"MPC Minutes - {month_name.title()} {year}",
                            "date_str": f"{year}-{dt.strftime('%m')}",
                        }
                    )
                    break  # Only need the most recent
            except Exception:
                continue
    except Exception as e:
        print(f"  [WARN] BOE: {e}")

    # ── Bank of Korea ──
    try:
        # BOK publishes at a BBS URL; try to scrape the listing page
        req = Request(
            "https://www.bok.or.kr/eng/bbs/E0000737/list.do?menuNo=400203",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        resp = urlopen(req, timeout=15)
        if resp.status == 200:
            html = resp.read().decode("utf-8", errors="ignore")
            # Find nttId values from the listing
            ntt_ids = re.findall(r"nttId=(\d+)", html)
            titles_raw = re.findall(r'class="title"[^>]*>([^<]+)', html)
            for i, ntt_id in enumerate(ntt_ids[:3]):  # Top 3 most recent
                title = (
                    titles_raw[i].strip()
                    if i < len(titles_raw)
                    else f"BOK Minutes #{ntt_id}"
                )
                url = f"https://www.bok.or.kr/eng/bbs/E0000737/view.do?nttId={ntt_id}&menuNo=400203"
                results.append(
                    {
                        "name": "Bank of Korea",
                        "url": url,
                        "title": title,
                        "date_str": "",
                    }
                )
    except Exception as e:
        print(f"  [WARN] BOK: {e}")

    return results


# ═══════════════════════════════════════════════════════════════════
# 5. Macro Data Snapshot (timeseries DB)
# ═══════════════════════════════════════════════════════════════════


def build_macro_data_snapshot():
    """Build a formatted text snapshot of macro indicators, CFTC positioning,
    and recent cross-asset performance from the timeseries database.

    Returns (text, indicator_count) or (None, 0) on failure.
    """
    try:
        import pandas as pd
        from ix.db.query import Series
    except Exception as e:
        print(f"  [WARN] Could not import timeseries modules: {e}")
        return None, 0

    sections = []
    indicator_count = 0

    # ── Section 1: Key Macro Indicators (latest value + changes) ──
    rows = []
    for name, code in MACRO_INDICATORS.items():
        try:
            s = Series(code)
            if s.empty:
                continue
            last_val = s.iloc[-1]

            # Calculate changes
            def _pct(n_days):
                idx = max(0, len(s) - n_days - 1)
                prev = s.iloc[idx]
                if prev and prev != 0:
                    return (last_val / prev - 1) * 100
                return None

            chg_1w = _pct(5)
            chg_1m = _pct(21)
            chg_3m = _pct(63)
            chg_ytd = None
            try:
                yr_start = s.loc[:f"{datetime.now().year}-01-02"].iloc[-1]
                if yr_start and yr_start != 0:
                    chg_ytd = (last_val / yr_start - 1) * 100
            except Exception:
                pass

            def _fmt(v):
                return f"{v:+.1f}%" if v is not None else "n/a"

            rows.append(
                f"| {name:<22} | {last_val:>10.2f} | {_fmt(chg_1w):>8} | {_fmt(chg_1m):>8} | {_fmt(chg_3m):>8} | {_fmt(chg_ytd):>8} |"
            )
            indicator_count += 1
        except Exception:
            continue

    if rows:
        header = (
            "## Key Macro Indicators\n\n"
            f"| {'Indicator':<22} | {'Last':>10} | {'1W Chg':>8} | {'1M Chg':>8} | {'3M Chg':>8} | {'YTD':>8} |\n"
            f"|{'-'*24}|{'-'*12}|{'-'*10}|{'-'*10}|{'-'*10}|{'-'*10}|\n"
        )
        sections.append(header + "\n".join(rows))

    # ── Section 2: CFTC Positioning ──
    cftc_rows = []
    for name, (long_code, short_code) in CFTC_ASSETS.items():
        try:
            long_s = Series(long_code)
            short_s = Series(short_code)
            net = long_s - short_s
            net = net.dropna()
            if net.empty:
                continue

            last_net = net.iloc[-1]
            # Z-score (52-week)
            roll_mean = net.rolling(52).mean()
            roll_std = net.rolling(52).std()
            z = (net - roll_mean) / roll_std
            z = z.dropna()
            last_z = z.iloc[-1] if not z.empty else None

            # 1-week change
            prev_net = net.iloc[-2] if len(net) > 1 else None
            wk_chg = last_net - prev_net if prev_net is not None else None

            z_str = f"{last_z:+.2f}" if last_z is not None else "n/a"
            chg_str = f"{wk_chg:+,.0f}" if wk_chg is not None else "n/a"

            cftc_rows.append(
                f"| {name:<12} | {last_net:>12,.0f} | {chg_str:>10} | {z_str:>8} |"
            )
            indicator_count += 1
        except Exception:
            continue

    if cftc_rows:
        header = (
            "\n\n## CFTC Commitment of Traders — Net Positioning\n\n"
            f"| {'Asset':<12} | {'Net Position':>12} | {'1W Change':>10} | {'Z-Score':>8} |\n"
            f"|{'-'*14}|{'-'*14}|{'-'*12}|{'-'*10}|\n"
        )
        sections.append(header + "\n".join(cftc_rows))

    # ── Section 3: VIX Term Structure ──
    try:
        vix = Series("VIX INDEX:PX_LAST")
        vix3m = Series("VIX3M INDEX:PX_LAST")
        if not vix.empty and not vix3m.empty:
            vix_val = vix.iloc[-1]
            vix3m_val = vix3m.iloc[-1]
            ratio = vix_val / vix3m_val if vix3m_val else None
            structure = (
                "BACKWARDATION (stress)" if ratio and ratio > 1 else "Contango (normal)"
            )
            sections.append(
                f"\n\n## Volatility Snapshot\n\n"
                f"- VIX: {vix_val:.1f}\n"
                f"- VIX3M: {vix3m_val:.1f}\n"
                f"- VIX/VIX3M Ratio: {ratio:.3f} → **{structure}**\n"
            )
    except Exception:
        pass

    if not sections:
        return None, 0

    text = (
        f"# Macro Data Snapshot — {datetime.now().strftime('%Y-%m-%d')}\n\n"
        + "\n".join(sections)
    )
    return text, indicator_count


# ═══════════════════════════════════════════════════════════════════
# 6. NotebookLM Functions
# ═══════════════════════════════════════════════════════════════════


async def get_nlm_client():
    """Get an authenticated NotebookLM client."""
    from notebooklm import NotebookLMClient

    client = await NotebookLMClient.from_storage()
    await client._core.open()
    return client


def ensure_notebooklm_auth():
    """Ensure NotebookLM is authenticated."""
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
    """Run a notebooklm CLI command."""
    import shlex

    cmd = ["notebooklm"] + shlex.split(args)
    stdout, stderr, rc = run_cmd(cmd, timeout=timeout)
    if rc != 0:
        print(f"  [ERROR] notebooklm {args[:80]}...: {stderr[:200]}")
    return stdout, rc


def generate_and_download(
    nb_id,
    asset_type,
    prompt,
    out_path,
    language="en",
    max_retries=8,
    poll_interval=30,
    gen_timeout=900,
):
    """Trigger NotebookLM generation and poll until download succeeds.

    gen_timeout is set high (900s = 15 min) because slide decks can take 10+ minutes.
    """
    label = asset_type.replace("-", " ")

    # Step 1: Trigger generation (fire and forget on timeout — still poll)
    print(f"  Triggering {label} generation...", flush=True)
    try:
        stdout, rc = notebooklm_cmd(
            f'generate {asset_type} --notebook "{nb_id}" --language {language} '
            f'"{prompt}" --wait',
            timeout=gen_timeout,
        )
        if rc != 0:
            print(
                f"  [WARN] generate command returned rc={rc}, will still attempt download."
            )
    except subprocess.TimeoutExpired:
        print(
            f"  [INFO] generate command timed out after {gen_timeout}s — will poll for download."
        )

    # Step 2: Poll download with retries
    for attempt in range(1, max_retries + 1):
        print(f"  Download attempt {attempt}/{max_retries}...", end=" ", flush=True)
        stdout, rc = notebooklm_cmd(
            f'download {asset_type} --notebook "{nb_id}" "{out_path}"',
            timeout=120,
        )
        if rc == 0 and out_path.is_file() and out_path.stat().st_size > 0:
            data = out_path.read_bytes()
            out_path.unlink(missing_ok=True)
            print(f"OK ({len(data):,} bytes)")
            return data

        print(f"not ready yet.", flush=True)
        if attempt < max_retries:
            print(f"  Waiting {poll_interval}s before next attempt...", flush=True)
            time.sleep(poll_interval)

    print(f"  [ERROR] {label} download failed after {max_retries} attempts.")
    return None


# ═══════════════════════════════════════════════════════════════════
# 7. Google Drive Functions
# ═══════════════════════════════════════════════════════════════════

# Reuse credentials/token from gdrive_rename.py
_DRIVE_TOKEN_PATH = Path(__file__).resolve().parent.parent.parent / "scripts" / "token.json"
_DRIVE_CREDS_PATH = Path(__file__).resolve().parent.parent.parent / "scripts" / "credentials.json"
_DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]
_DRIVE_FOLDER_ID = "1jkpxtpaZophtkx5Lhvb-TAF9BuKY_pPa"

# Map Drive MIME types to the values NotebookLM expects
_MIME_MAP = {
    "application/pdf": "application/pdf",
    "application/vnd.google-apps.document": "application/vnd.google-apps.document",
    "application/vnd.google-apps.presentation": "application/vnd.google-apps.presentation",
    "application/vnd.google-apps.spreadsheet": "application/vnd.google-apps.spreadsheet",
}


def _get_drive_service():
    """Build an authenticated Google Drive API service."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if _DRIVE_TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(_DRIVE_TOKEN_PATH), _DRIVE_SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not _DRIVE_CREDS_PATH.exists():
                print(f"  ERROR: {_DRIVE_CREDS_PATH} not found. Run scripts/gdrive_rename.py first.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(str(_DRIVE_CREDS_PATH), _DRIVE_SCOPES)
            creds = flow.run_local_server(port=0)
        _DRIVE_TOKEN_PATH.write_text(creds.to_json())
    return build("drive", "v3", credentials=creds)


def list_drive_files(max_files=15, date_after=None, date_before=None, folder_id=None):
    """List files from Google Drive folder sorted by modifiedTime desc.

    Args:
        max_files: Maximum number of files to return.
        date_after: Only files modified after this date (YYYYMMDD string).
        date_before: Only files modified before this date (YYYYMMDD string).
        folder_id: Drive folder ID (defaults to _DRIVE_FOLDER_ID).

    Returns:
        List of dicts with title, file_id, mime_type, modified_time.
    """
    service = _get_drive_service()
    if not service:
        return []

    fid = folder_id or _DRIVE_FOLDER_ID
    q_parts = [f"'{fid}' in parents", "trashed=false"]

    if date_after:
        dt = datetime.strptime(date_after, "%Y%m%d")
        q_parts.append(f"modifiedTime >= '{dt.strftime('%Y-%m-%dT00:00:00')}'")
    if date_before:
        dt = datetime.strptime(date_before, "%Y%m%d") + timedelta(days=1)
        q_parts.append(f"modifiedTime < '{dt.strftime('%Y-%m-%dT00:00:00')}'")

    query = " and ".join(q_parts)

    results = []
    page_token = None
    while True:
        resp = service.files().list(
            q=query,
            fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
            orderBy="modifiedTime desc",
            pageSize=min(max_files, 100),
            pageToken=page_token,
        ).execute()
        results.extend(resp.get("files", []))
        if len(results) >= max_files:
            break
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    drive_files = []
    for f in results[:max_files]:
        mime = f.get("mimeType", "application/pdf")
        nlm_mime = _MIME_MAP.get(mime, "application/pdf")
        drive_files.append({
            "title": f["name"],
            "file_id": f["id"],
            "mime_type": nlm_mime,
            "modified_time": f.get("modifiedTime", ""),
        })
    return drive_files


async def add_drive_files_to_notebook(client, nb_id, drive_files):
    """Add Drive files as proper Drive sources."""
    from notebooklm._sources import SourcesAPI

    sources_api = SourcesAPI(client._core)
    added = 0
    for i, f in enumerate(drive_files):
        print(
            f"  [{i+1}/{len(drive_files)}] Adding: {f['title'][:60]}...",
            end=" ",
            flush=True,
        )
        try:
            await sources_api.add_drive(
                notebook_id=nb_id,
                file_id=f["file_id"],
                title=f["title"],
                mime_type=f.get("mime_type", "application/pdf"),
            )
            added += 1
            print("OK")
        except Exception as e:
            print(f"FAILED ({e})")
    return added


# ═══════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════════


async def main():
    parser = argparse.ArgumentParser(description="Multi-Source Macro Research Pipeline")
    parser.add_argument(
        "--days", type=int, default=7, help="Look back N days (default: 7)"
    )
    parser.add_argument(
        "--date", type=str, default=None, help="Target date YYYY-MM-DD (default: today)"
    )
    parser.add_argument(
        "--topic", type=str, default=None, help="Filter by topic keyword"
    )
    parser.add_argument(
        "--max-videos", type=int, default=20, help="Max videos to add (default: 20)"
    )
    parser.add_argument(
        "--max-per-channel",
        type=int,
        default=10,
        help="Max videos per channel (default: 10)",
    )
    parser.add_argument(
        "--skip-infographic", action="store_true", help="Skip infographic generation"
    )
    parser.add_argument(
        "--skip-slides", action="store_true", help="Skip slide deck generation"
    )
    parser.add_argument(
        "--skip-drive", action="store_true", help="Skip Google Drive sources"
    )
    parser.add_argument(
        "--skip-youtube", action="store_true", help="Skip YouTube sources"
    )
    parser.add_argument(
        "--skip-news", action="store_true", help="Skip RSS news scraping"
    )
    parser.add_argument(
        "--skip-telegram", action="store_true", help="Skip Telegram scraping"
    )
    parser.add_argument(
        "--skip-central-banks", action="store_true", help="Skip central bank minutes"
    )
    parser.add_argument(
        "--skip-data", action="store_true", help="Skip macro data snapshot"
    )
    parser.add_argument(
        "--drive-max", type=int, default=15, help="Max Drive files to add (default: 15)"
    )
    parser.add_argument(
        "--language", type=str, default="en", help="Output language (default: en)"
    )
    args = parser.parse_args()

    if args.date:
        target_date = datetime.strptime(args.date, "%Y-%m-%d")
    else:
        target_date = datetime.now()

    report_label = target_date.strftime("%Y-%m-%d")
    date_before = target_date.strftime("%Y%m%d")
    date_after = (target_date - timedelta(days=args.days)).strftime("%Y%m%d")

    import tempfile

    tmp_dir = Path(tempfile.mkdtemp(prefix="ix_research_"))

    total_steps = 8
    print(f"{'='*60}")
    print(f"  Macro Research Pipeline")
    print(f"  Date: {report_label}  |  Range: {date_after}–{date_before}")
    src_parts = []
    if not args.skip_youtube:
        src_parts.append("YouTube")
    if not args.skip_drive:
        src_parts.append("Drive")
    if not args.skip_news:
        src_parts.append("News(RSS)")
    if not args.skip_telegram:
        src_parts.append("Telegram")
    if not args.skip_central_banks:
        src_parts.append("Central Banks")
    if not args.skip_data:
        src_parts.append("Macro Data")
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

    # ── Step 2: Fetch & score YouTube videos ──
    selected = []
    if not args.skip_youtube:
        print(f"\n[2/{total_steps}] Fetching videos from {len(CHANNELS)} channels...")
        all_videos = []
        for ch in CHANNELS:
            print(f"  Scanning: {ch['name']}...", end=" ", flush=True)
            videos = fetch_channel_videos(
                ch["url"], args.max_per_channel, date_after, date_before
            )
            for v in videos:
                v["channel"] = ch["name"]
            all_videos.extend(videos)
            print(f"{len(videos)} videos")

        print(f"\n  Total videos fetched: {len(all_videos)}")
        print(f"  Scoring and ranking...")
        for v in all_videos:
            v["score"] = score_video(v, args.topic)
        all_videos.sort(key=lambda v: v["score"], reverse=True)
        selected = all_videos[: args.max_videos]

        print(f"  Selected top {len(selected)} videos:")
        for i, v in enumerate(selected):
            print(f"    {i+1:2d}. [{v['score']:2d}] {v['channel']}: {v['title'][:70]}")

        with open(tmp_dir / "selected_videos.json", "w", encoding="utf-8") as f:
            json.dump(selected, f, indent=2, ensure_ascii=False)
    else:
        print(f"\n[2/{total_steps}] Skipping YouTube.")

    # ── Step 3: Create NotebookLM notebook ──
    print(f"\n[3/{total_steps}] Creating NotebookLM notebook...")
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

    # ── Step 4: Add all sources ──
    print(f"\n[4/{total_steps}] Adding sources to NotebookLM...")

    added_yt = 0
    added_drive = 0
    added_news = 0
    added_telegram = 0
    added_cb = 0
    added_data = 0
    drive_files = []

    # 4a: YouTube videos (parallel batches for speed)
    if selected:
        print(f"\n  --- YouTube Videos ({len(selected)}) ---")
        BATCH_SIZE = 5  # Add 5 videos concurrently

        async def _add_video(idx, v):
            """Add a single video source (async subprocess)."""
            import shlex

            cmd_str = f'source add --notebook "{nb_id}" "{v["url"]}"'
            cmd = ["notebooklm"] + shlex.split(cmd_str)
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            out, err = await asyncio.wait_for(proc.communicate(), timeout=60)
            return idx, v, proc.returncode

        for batch_start in range(0, len(selected), BATCH_SIZE):
            batch = selected[batch_start : batch_start + BATCH_SIZE]
            tasks = [_add_video(batch_start + i, v) for i, v in enumerate(batch)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    print(f"  [err] {r}")
                    continue
                idx, v, rc = r
                label = f"[{idx+1}/{len(selected)}] {v['title'][:55]}"
                if rc == 0:
                    added_yt += 1
                    print(f"  {label}... OK")
                else:
                    print(f"  {label}... FAILED")
        print(f"  YouTube: {added_yt}/{len(selected)} added")

    # 4b: Google Drive files (via Drive API, sorted by modifiedTime desc)
    if not args.skip_drive:
        print(f"\n  --- Google Drive (most recently modified) ---")
        print(f"  Listing files modified between {date_after} and {date_before}...")
        drive_files = list_drive_files(
            max_files=args.drive_max,
            date_after=date_after,
            date_before=date_before,
        )

        if drive_files:
            print(f"  Found {len(drive_files)} file(s):")
            for i, f in enumerate(drive_files):
                mod = f.get("modified_time", "")[:10]
                print(f"    {i+1:2d}. [{mod}] {f['title'][:65]}")

            with open(tmp_dir / "drive_files.json", "w", encoding="utf-8") as fp:
                json.dump(drive_files, fp, indent=2, ensure_ascii=False)
            print(f"\n  Adding Drive files as sources...")
            added_drive = await add_drive_files_to_notebook(
                client, nb_id, drive_files
            )
            print(f"  Drive: {added_drive}/{len(drive_files)} added")
        else:
            print(f"  No Drive files found in date range.")

    # 4c: Central bank minutes (URLs)
    if not args.skip_central_banks:
        print(f"\n  --- Central Bank Minutes ---")
        cb_urls = fetch_central_bank_urls(days=90)
        if cb_urls:
            print(f"  Found {len(cb_urls)} recent document(s):")
            for i, cb in enumerate(cb_urls):
                print(f"    {i+1:2d}. [{cb['name']}] {cb['title'][:60]}")

            async def _add_cb(cb):
                import shlex

                cmd_str = f'source add --notebook "{nb_id}" "{cb["url"]}"'
                cmd = ["notebooklm"] + shlex.split(cmd_str)
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                out, err = await asyncio.wait_for(proc.communicate(), timeout=60)
                return cb, proc.returncode

            cb_results = await asyncio.gather(
                *[_add_cb(cb) for cb in cb_urls], return_exceptions=True
            )
            for r in cb_results:
                if isinstance(r, Exception):
                    print(f"  [err] {r}")
                    continue
                cb, rc = r
                if rc == 0:
                    added_cb += 1
                    print(f"  {cb['title'][:55]}... OK")
                else:
                    print(f"  {cb['title'][:55]}... FAILED")
            print(f"  Central banks: {added_cb}/{len(cb_urls)} added")
        else:
            print(f"  No recent central bank documents found.")

    # 4d: RSS News (scraped directly)
    if not args.skip_news:
        print(f"\n  --- RSS News (last {args.days} days) ---")
        news_text, news_count = scrape_rss_news(args.days)
        if news_text:
            print(
                f"  Scraped {news_count} articles. Adding as source...",
                end=" ",
                flush=True,
            )
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
            print(f"  No news articles scraped.")

    # 4e: Telegram (scraped directly via telethon)
    if not args.skip_telegram:
        print(f"\n  --- Telegram (last {args.days} days) ---")
        telegram_text, tg_count = await scrape_telegram_direct(args.days)
        if telegram_text:
            print(
                f"  Scraped {tg_count} messages. Adding as source...",
                end=" ",
                flush=True,
            )
            tg_file = tmp_dir / "_telegram_source.md"
            with open(tg_file, "w", encoding="utf-8") as f:
                f.write(telegram_text)
            stdout, rc = notebooklm_cmd(
                f'source add --notebook "{nb_id}" --type text --title "Telegram Messages ({report_label})" "{tg_file}"',
                timeout=60,
            )
            if rc == 0:
                added_telegram = tg_count
                print("OK")
            else:
                print("FAILED")
            tg_file.unlink(missing_ok=True)
        else:
            print(f"  No Telegram messages scraped.")

    # 4f: Macro data snapshot (timeseries DB)
    if not args.skip_data:
        print(f"\n  --- Macro Data Snapshot ---")
        data_text, data_count = build_macro_data_snapshot()
        if data_text:
            print(
                f"  Built snapshot ({data_count} indicators). Adding as source...",
                end=" ",
                flush=True,
            )
            data_file = tmp_dir / "_macro_data.md"
            with open(data_file, "w", encoding="utf-8") as f:
                f.write(data_text)
            stdout, rc = notebooklm_cmd(
                f'source add --notebook "{nb_id}" --type text --title "Macro Data Snapshot ({report_label})" "{data_file}"',
                timeout=60,
            )
            if rc == 0:
                added_data = data_count
                print("OK")
            else:
                print("FAILED")
            data_file.unlink(missing_ok=True)
        else:
            print(f"  No macro data available.")

    print(f"\n  ── Source Summary ──")
    print(f"  YouTube:       {added_yt}")
    print(f"  Drive:         {added_drive}")
    print(f"  Central Banks: {added_cb}")
    print(f"  News (RSS):    {added_news}")
    print(f"  Telegram:      {added_telegram}")
    print(f"  Macro Data:    {added_data} indicators")

    # ── Step 5: Ask NotebookLM for analysis ──
    print(f"\n[5/{total_steps}] Requesting NotebookLM analysis...")

    briefing_text = None
    scorecard_text = None
    takeaways_text = None

    print("  Generating comprehensive briefing...")
    briefing_prompt = (
        "Based on ALL sources, create a comprehensive macro intelligence briefing covering: "
        "1) Current state of global markets and key risks, "
        "2) Key themes - where experts agree and disagree, "
        "3) Geopolitics and their market impact, "
        "4) Credit and financial system risks, "
        "5) Capital rotation trends, "
        "6) AI and technology impact on markets, "
        "7) Fed and central bank monetary policy outlook (including ECB, BOJ, BOK), "
        "8) CFTC positioning signals and what they indicate, "
        "9) Forward-looking predictions and what to watch. "
        "Be specific, cite which experts said what. Reference the macro data where applicable."
    )
    stdout, rc = notebooklm_cmd(
        f'ask --notebook "{nb_id}" "{briefing_prompt}"', timeout=180
    )
    if rc == 0:
        briefing_text = (
            f"# Macro Intelligence Briefing — {report_label}\n\n"
            + stdout.replace("Answer:", "").strip()
        )
        print("  Briefing OK.")

    print("  Generating risk scorecard...")
    risk_prompt = (
        "Create a risk scorecard rating these areas 1-10: "
        "Geopolitical Risk, Credit Market Risk, Equity Market Risk, "
        "Inflation Risk, Liquidity Risk, Technology Disruption Risk, "
        "Currency Risk, Emerging Market Risk. "
        "For each cite the key evidence from sources and explain why. "
        "Reference specific data points from the macro data snapshot."
    )
    stdout, rc = notebooklm_cmd(
        f'ask --notebook "{nb_id}" "{risk_prompt}"', timeout=120
    )
    if rc == 0:
        scorecard_text = (
            f"# Risk Scorecard — {report_label}\n\n"
            + stdout.replace("Answer:", "").strip()
        )
        print("  Risk scorecard OK.")

    print("  Generating executive takeaways...")
    takeaway_prompt = (
        "In exactly 5 bullet points, give the most important actionable takeaways "
        "an institutional investor should focus on this week. Be specific about: "
        "1) asset class positioning, 2) regional allocation, 3) risk hedges to consider, "
        "4) key data releases or events to watch, 5) contrarian or consensus trade to be aware of. "
        "Reference CFTC positioning data and central bank guidance where relevant."
    )
    stdout, rc = notebooklm_cmd(
        f'ask --notebook "{nb_id}" "{takeaway_prompt}"', timeout=120
    )
    if rc == 0:
        takeaways_text = (
            f"# Executive Takeaways — {report_label}\n\n"
            + stdout.replace("Answer:", "").strip()
        )
        print("  Takeaways OK.")

    # ── Generation prompts ──
    _INFOGRAPHIC_PROMPT = (
        "Create an institutional-grade macro market analysis infographic. "
        "Structure it as a professional research dashboard with these sections: "
        "1) MARKET REGIME — current macro regime classification (risk-on, risk-off, transition) "
        "with a clear visual indicator and supporting data points. "
        "2) RISK HEATMAP — a matrix rating Geopolitical, Credit, Equity, Inflation, Liquidity, "
        "and Systemic risk from 1-10, color-coded green/amber/red. "
        "3) ASSET CLASS SIGNALS — directional consensus for Equities, Fixed Income, Commodities, "
        "FX, and Alternatives with bull/bear/neutral indicators. "
        "4) CAPITAL FLOWS & ROTATION — where institutional capital is moving (sector rotation, "
        "geographic shifts, risk-on vs. defensive positioning). "
        "5) KEY EXPERT POSITIONS — summarize the most impactful views from named sources, "
        "highlighting where experts agree and where they diverge. "
        "6) FORWARD-LOOKING OUTLOOK (1-4 weeks) — probability-weighted scenarios for markets "
        "including base case, bull case, and tail risk scenario with catalysts for each. "
        "7) ACTIONABLE TAKEAWAYS — top 3 institutional positioning recommendations with "
        "specific asset classes, direction, and conviction level. "
        "Use clean, professional formatting. Cite specific sources. Be data-driven and precise."
    )

    _SLIDE_DECK_PROMPT = (
        "Create an institutional-grade macro strategy slide deck suitable for a weekly "
        "investment committee presentation. Structure the deck as follows: "
        "SLIDE 1: Executive Summary — one-paragraph macro thesis with key conclusion. "
        "SLIDE 2: Market Regime & Macro Dashboard — current regime (risk-on/off/transition), "
        "leading indicator readings, and regime probability. "
        "SLIDE 3: Risk Assessment — heatmap of Geopolitical, Credit, Equity, Inflation, "
        "Liquidity, and Systemic risk rated 1-10 with brief rationale for each. "
        "SLIDE 4: Cross-Asset Review — performance and outlook for Equities, Rates, Credit, "
        "FX, and Commodities with directional signals. "
        "SLIDE 5: Thematic Deep Dive — the 2-3 dominant themes this week (e.g. Fed policy, "
        "earnings, geopolitics, AI/tech, China) with expert commentary and data. "
        "SLIDE 6: Capital Flows & Positioning — institutional flow data, sector rotation, "
        "geographic allocation shifts, CFTC positioning, and crowding indicators. "
        "SLIDE 7: Forward Outlook & Scenarios — base case (60%), bull case (25%), bear case "
        "(15%) for the next 1-4 weeks with specific catalysts and trigger levels. "
        "SLIDE 8: Actionable Recommendations — top 3-5 positioning ideas with asset class, "
        "direction, conviction level, and risk/reward framing. "
        "SLIDE 9: Key Events Calendar — upcoming catalysts (data releases, central bank "
        "decisions, earnings, geopolitical events) for the next 2 weeks. "
        "Use professional, concise language. Cite sources. Include specific levels and data."
    )

    # ── Step 6: Generate infographic ──
    infographic_bytes = None
    if not args.skip_infographic:
        print(f"\n[6/{total_steps}] Generating infographic via NotebookLM...")
        infographic_bytes = generate_and_download(
            nb_id,
            "infographic",
            _INFOGRAPHIC_PROMPT,
            tmp_dir / "infographic.png",
            language=args.language,
            max_retries=8,
            poll_interval=30,
            gen_timeout=600,
        )
        if infographic_bytes:
            print(f"  Infographic OK.")
        else:
            print(f"  Infographic generation failed.")
    else:
        print(f"\n[6/{total_steps}] Skipping infographic generation.")

    # ── Step 7: Generate slide deck ──
    slide_deck_bytes = None
    if not args.skip_slides:
        print(f"\n[7/{total_steps}] Generating slide deck via NotebookLM...")
        slide_deck_bytes = generate_and_download(
            nb_id,
            "slide-deck",
            _SLIDE_DECK_PROMPT,
            tmp_dir / "slide_deck.pdf",
            language=args.language,
            max_retries=12,
            poll_interval=45,
            gen_timeout=900,
        )
        if slide_deck_bytes:
            print(f"  Slide deck OK.")
        else:
            print(f"  Slide deck generation failed.")
    else:
        print(f"\n[7/{total_steps}] Skipping slide deck generation.")

    # ── Step 8: Save to database ──
    print(f"\n[8/{total_steps}] Saving report to database...")
    try:
        from ix.db.conn import Session as DBSession
        from ix.db.models.research_report import ResearchReport

        report_date = (
            target_date.date() if hasattr(target_date, "date") else target_date
        )

        sources_data = {}
        if selected:
            sources_data["selected_videos"] = selected
        if drive_files:
            sources_data["drive_files"] = drive_files
        if added_cb:
            sources_data["central_bank_docs"] = cb_urls if "cb_urls" in dir() else []
        sources_data["counts"] = {
            "youtube": added_yt,
            "drive": added_drive,
            "central_banks": added_cb,
            "news": added_news,
            "telegram": added_telegram,
            "macro_data": added_data,
        }

        def _sanitize_text(text):
            if text:
                return text.replace("\x00", "")
            return text

        briefing_safe = _sanitize_text(briefing_text)
        scorecard_safe = _sanitize_text(scorecard_text)
        takeaways_safe = _sanitize_text(takeaways_text)

        for attempt in range(1, 4):
            try:
                with DBSession() as db:
                    existing = (
                        db.query(ResearchReport)
                        .filter(ResearchReport.date == report_date)
                        .first()
                    )
                    if existing:
                        existing.briefing = briefing_safe
                        existing.risk_scorecard = scorecard_safe
                        existing.takeaways = takeaways_safe
                        if infographic_bytes:
                            existing.infographic = infographic_bytes
                        if slide_deck_bytes:
                            existing.slide_deck = slide_deck_bytes
                        existing.sources = sources_data
                        print(f"  Updated existing report for {report_label}.")
                    else:
                        report = ResearchReport(
                            date=report_date,
                            briefing=briefing_safe,
                            risk_scorecard=scorecard_safe,
                            takeaways=takeaways_safe,
                            infographic=infographic_bytes,
                            slide_deck=slide_deck_bytes,
                            sources=sources_data,
                        )
                        db.add(report)
                        print(f"  Saved new report for {report_label}.")

                break  # Exit retry loop on success

            except Exception as e:
                print(f"  [WARN] DB save attempt {attempt}/3 failed: {e}")
                if attempt < 3:
                    import time

                    time.sleep(2)
                else:
                    print(f"  [ERROR] Final attempt to save to database failed.")

    except Exception as e:
        print(f"  [ERROR] Database pipeline failed: {e}")

    # ── Cleanup ──
    print(f"\n  Cleaning up NotebookLM notebook...")
    stdout, rc = notebooklm_cmd(f'delete -n "{nb_id}" -y', timeout=30)
    if rc == 0:
        print(f"  Notebook {nb_id[:12]}... deleted.")
    else:
        print(
            f"  [WARN] Could not delete notebook. Delete manually: notebooklm delete {nb_id}"
        )

    import shutil

    shutil.rmtree(tmp_dir, ignore_errors=True)

    # ── Done ──
    print(f"\n{'='*60}")
    print(f"  DONE! Report saved to database for {report_label}.")
    print(f"  YouTube: {added_yt} | Drive: {added_drive} | Central Banks: {added_cb}")
    print(
        f"  News: {added_news} | Telegram: {added_telegram} | Macro Data: {added_data}"
    )
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
