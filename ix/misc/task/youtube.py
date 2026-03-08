"""
YouTube Intelligence Task
Scans configured channels for new videos, summarizes via NotebookLM, saves to DB.
"""
import json
import subprocess
import time
from datetime import datetime
from ix.db.conn import Session
from ix.db.models import YouTubeIntel
from ix.misc import get_logger

logger = get_logger(__name__)

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

SUMMARY_PROMPT = (
    "Summarize this video for an institutional investor. Cover: "
    "1) Key Thesis (1-2 sentences), "
    "2) Market Implications for equities/bonds/commodities/currencies, "
    "3) Risk Factors highlighted, "
    "4) Actionable Takeaways, "
    "5) Notable quotes or data points. "
    "Be concise but comprehensive. Write in English."
)


def _nlm_cmd(args, timeout=120):
    """Run a notebooklm CLI command."""
    cmd = f"notebooklm {args}"
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, shell=True)
        return result.stdout.strip(), result.returncode
    except Exception as e:
        logger.warning(f"notebooklm command failed: {e}")
        return "", 1


def _fetch_channel_videos(channel_url, max_per_channel=10):
    """Fetch recent videos from a channel using yt-dlp."""
    cmd = f'yt-dlp --flat-playlist -j --playlist-end {max_per_channel} "{channel_url}/videos"'
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, shell=True)
        if result.returncode != 0:
            return []
    except Exception as e:
        logger.warning(f"yt-dlp failed for {channel_url}: {e}")
        return []

    videos = []
    for line in result.stdout.splitlines():
        try:
            d = json.loads(line)
            videos.append({
                "video_id": d.get("id", ""),
                "title": d.get("title", ""),
                "duration": d.get("duration", 0),
                "url": f"https://www.youtube.com/watch?v={d.get('id', '')}",
            })
        except json.JSONDecodeError:
            continue
    return videos


def _summarize_batch_with_nlm(videos):
    """
    Create a NotebookLM notebook, add videos as sources,
    ask for individual summaries, return {video_id: summary}.
    """
    # Create notebook
    title = f"YT Scan {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
    stdout, rc = _nlm_cmd(f'create "{title}"', timeout=60)
    if rc != 0:
        logger.error(f"Failed to create notebook: {stdout}")
        return {}

    # Extract notebook ID
    nb_id = None
    for word in stdout.split():
        if len(word) > 30 and "-" in word:
            nb_id = word
            break
    if not nb_id:
        logger.error(f"Could not parse notebook ID from: {stdout}")
        return {}

    logger.info(f"Created notebook: {nb_id} with {len(videos)} videos")

    # Add all videos as sources
    added_videos = []
    for v in videos:
        stdout, rc = _nlm_cmd(f'source add --notebook "{nb_id}" "{v["url"]}"', timeout=60)
        if rc == 0:
            added_videos.append(v)
        else:
            logger.warning(f"Failed to add source: {v['title'][:50]}")

    if not added_videos:
        logger.warning("No videos added to notebook. Skipping.")
        return {}

    # Wait for NotebookLM to process video transcripts
    wait_secs = min(30 * len(added_videos), 120)
    logger.info(f"  Waiting {wait_secs}s for NotebookLM to process transcripts...")
    time.sleep(wait_secs)

    # Ask NotebookLM to summarize each video
    summaries = {}
    for v in added_videos:
        prompt = (
            f'For the video titled "{v["title"]}", {SUMMARY_PROMPT}'
        )
        # Escape quotes in prompt
        prompt = prompt.replace('"', '\\"')
        stdout, rc = _nlm_cmd(f'ask --notebook "{nb_id}" "{prompt}"', timeout=120)
        if rc == 0:
            # Strip the "Continuing conversation..." prefix
            text = stdout
            if "Answer:" in text:
                text = text.split("Answer:", 1)[1].strip()
            if "Resumed conversation:" in text:
                text = text.rsplit("Resumed conversation:", 1)[0].strip()
            summaries[v["video_id"]] = text
            logger.info(f"  Summarized: {v['title'][:50]}")
        else:
            logger.warning(f"  Failed to summarize: {v['title'][:50]}")

    # Clean up - delete the notebook
    _nlm_cmd(f'delete "{nb_id}" --yes', timeout=30)

    return summaries


def scan_youtube_channels(max_per_channel=10, batch_size=20):
    """
    Scan all configured YouTube channels for new videos,
    summarize new ones with NotebookLM, and save to DB.
    """
    logger.info("Starting YouTube channel scan...")
    new_count = 0
    skip_count = 0

    with Session() as session:
        # Get existing video_ids to skip duplicates
        existing_ids = set(
            row[0] for row in session.query(YouTubeIntel.video_id).all()
        )
        logger.info(f"Found {len(existing_ids)} existing videos in DB.")

        # Collect all new videos across channels
        new_videos = []
        for ch in CHANNELS:
            logger.info(f"Scanning: {ch['name']}...")
            videos = _fetch_channel_videos(ch["url"], max_per_channel)
            for v in videos:
                if v["video_id"] and v["video_id"] not in existing_ids:
                    v["channel"] = ch["name"]
                    new_videos.append(v)
                else:
                    skip_count += 1

        logger.info(f"Found {len(new_videos)} new videos, {skip_count} already in DB.")

        if not new_videos:
            logger.info("No new videos to process.")
            return 0

        # Process in batches (NotebookLM has source limits per notebook)
        for i in range(0, len(new_videos), batch_size):
            batch = new_videos[i:i + batch_size]
            logger.info(f"Processing batch {i // batch_size + 1} ({len(batch)} videos)...")

            summaries = _summarize_batch_with_nlm(batch)

            # Save to DB
            for v in batch:
                vid = v["video_id"]
                summary = summaries.get(vid)
                if not summary:
                    continue

                record = YouTubeIntel(
                    video_id=vid,
                    channel=v["channel"],
                    title=v["title"],
                    url=v["url"],
                    published_at=datetime.utcnow(),
                    duration_seconds=v.get("duration", 0) or 0,
                    summary=summary,
                )
                session.add(record)
                existing_ids.add(vid)
                new_count += 1

            try:
                session.commit()
            except Exception as e:
                logger.error(f"Commit failed: {e}")
                session.rollback()

    logger.info(f"YouTube scan complete: {new_count} new videos summarized and saved.")
    return new_count
