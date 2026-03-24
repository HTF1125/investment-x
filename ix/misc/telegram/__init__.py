import asyncio
import os
from typing import Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv
from ix.misc.terminal import get_logger
from ix.db.conn import Session, conn, Base
from ix.db.models import TelegramMessage

try:
    from telethon import TelegramClient
    from telethon.tl.types import Message
except ImportError:
    TelegramClient = None
    Message = None

from pathlib import Path

logger = get_logger(__name__)

# Ensure .env is loaded (no-op if already loaded by settings.py)
load_dotenv()

# Constants for Telegram API
API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")

# Session file is stored in the same folder as this __init__.py
SESSION_NAME = str(Path(__file__).parent / "ix_session")

CHANNELS_TO_SCRAPE = [
    # ── Korean Broker Research ──
    "t.me/HANAchina",
    "t.me/EMchina",
    "t.me/hanaglobalbottomup",
    "t.me/hanabondview",
    "t.me/HanaResearch",
    "t.me/shinhanresearch",
    "t.me/KISemicon",
    "t.me/strategy_kis",
    "t.me/kiwoom_semibat",
    "t.me/merITz_tech",
    "t.me/meritz_research",
    "t.me/growthresearch",
    "t.me/eugene2team",
    "t.me/Brain_And_Body_Research",
    "t.me/daishinstrategy",
    "t.me/yuantaresearch",
    "t.me/companyreport",
    "t.me/repostory123",
    # ── Korean Analysts & Strategists ──
    "t.me/hermitcrab41",
    "t.me/Yeouido_Lab",
    "t.me/EarlyStock1",
    "t.me/globaletfi",
    "t.me/Inhwan_Ha",
    "t.me/jkc123",
    "t.me/sskimfi",
    "t.me/globalequity1",
    "t.me/sypark_strategy",
    "t.me/bottomupquantapproach",
    "t.me/TNBfolio",
    "t.me/globalbobo",
    "t.me/lim_econ",
    "t.me/Jstockclass",
    "t.me/awake_schedule",
    "t.me/KoreaIB",
    "t.me/buffettlab",
    "t.me/YeouidoStory2",
    "t.me/sejongdata2013",
    "t.me/tRadarnewsdesk",
    # ── Japan / Asia Research ──
    "t.me/aetherjapanresearch",
    # ── Wire Services & Major Media ──
    "t.me/ReutersWorldChannel",
    "t.me/bloomberg",
    "t.me/FinancialNews",
    "t.me/BloombergQ",
    "t.me/wall_street_journal_news",
    "t.me/cnaborsenews",
    "t.me/naborsenews",
    # ── English Macro / Research (P0) ──
    "t.me/MarketEar",
    "t.me/unusual_whales",
    "t.me/CryptoMacroNews",
    "t.me/zaborskychannel",
    "t.me/biancoresearch",
    "t.me/WatcherGuru",
    "t.me/financialjuice",
    # ── English Macro / Research (P1) ──
    "t.me/MacroAlf",
    "t.me/TheTerminal",
    "t.me/BISgram",
    "t.me/FedWatch",
    "t.me/IIF_GlobalDebt",
    "t.me/IMFNews",
    "t.me/WorldBankLive",
    # ── English Macro / Research (P2) ──
    "t.me/realvisionchannel",
    "t.me/GoldTelegraph",
    "t.me/MacroScope",
    "t.me/ZeroHedge",
    "t.me/ForexFactory",
    "t.me/TradingView",
]


def _ensure_db():
    """Dispose stale pool and reconnect with retries."""
    if conn.engine:
        conn.engine.dispose()
    conn._is_connected = False
    return conn.connect(max_retries=3, retry_delay=5.0)


def _db_insert(channel_name: str, new_messages: list) -> int:
    """Insert messages with dedup. Returns count inserted."""
    with Session() as session:
        msg_ids = [m.message_id for m in new_messages]
        existing = (
            session.query(TelegramMessage.message_id)
            .filter(TelegramMessage.channel_name == channel_name)
            .filter(TelegramMessage.message_id.in_(msg_ids))
            .all()
        )
        existing_ids = {r[0] for r in existing}
        to_insert = [m for m in new_messages if m.message_id not in existing_ids]
        if to_insert:
            session.add_all(to_insert)
            session.commit()
            logger.info(f"Inserted {len(to_insert)} new messages.")
            return len(to_insert)
        else:
            logger.info("No new messages to insert (all duplicates).")
            return 0


async def scrape_all_channels(progress_cb=None):
    """Scrape all channels using a single Telegram client session."""
    if TelegramClient is None:
        logger.error("telethon is not installed. pip install telethon")
        return

    if not API_ID or not API_HASH:
        logger.error("TELEGRAM_API_ID and TELEGRAM_API_HASH must be set.")
        return

    # Ensure DB + table
    _ensure_db()
    if conn.engine:
        TelegramMessage.__table__.create(conn.engine, checkfirst=True)
        logger.info("Checked/Created TelegramMessage table.")

    # Single Telegram client for the entire run
    client = TelegramClient(SESSION_NAME, int(API_ID), API_HASH)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            logger.error("Telegram session expired. Run telethon login to re-auth.")
            return
    except Exception as e:
        logger.error(f"Failed to connect Telegram client: {e}")
        return

    total = len(CHANNELS_TO_SCRAPE)
    total_inserted = 0

    try:
        for idx, channel in enumerate(CHANNELS_TO_SCRAPE, start=1):
            if progress_cb:
                progress_cb(idx, total, channel)
            try:
                count = await _scrape_single(client, channel)
                total_inserted += count
            except Exception as e:
                logger.error(f"[{idx}/{total}] Failed {channel}: {e}")
            await asyncio.sleep(2)
    finally:
        await client.disconnect()

    logger.info(f"=== ALL DONE. Total inserted: {total_inserted} across {total} channels ===")


async def _scrape_single(client, channel_name: str) -> int:
    """Scrape one channel. Returns count of inserted messages."""
    logger.info(f"Scraping {channel_name}...")

    # Resolve entity
    try:
        entity = await client.get_input_entity(channel_name)
    except Exception as e:
        logger.error(f"Could not find entity '{channel_name}': {e}")
        return 0

    # Get min_id from DB (with fallback)
    min_id = 0
    try:
        with Session() as session:
            last_msg = (
                session.query(TelegramMessage.message_id)
                .filter(TelegramMessage.channel_name == channel_name)
                .order_by(TelegramMessage.message_id.desc())
                .first()
            )
            if last_msg:
                min_id = last_msg[0]
                logger.info(f"  min_id={min_id}")
            else:
                logger.info(f"  No existing messages. Initial scrape.")
    except Exception:
        logger.warning(f"  DB read failed for min_id, using 0. Will reconnect on insert.")

    # Determine scraping parameters
    offset_date = None
    if min_id == 0:
        offset_date = datetime.utcnow() - timedelta(hours=24)

    # Fetch messages from Telegram
    new_messages = []
    count_processed = 0

    async for msg in client.iter_messages(entity, limit=2000, min_id=min_id):
        if min_id == 0 and offset_date and msg.date:
            if msg.date.replace(tzinfo=None) < offset_date:
                break
        count_processed += 1
        if not msg.message:
            continue

        new_messages.append(TelegramMessage(
            channel_name=channel_name,
            message_id=msg.id,
            sender_id=msg.sender_id,
            sender_name=None,
            date=(msg.date.replace(tzinfo=None) + timedelta(hours=9)) if msg.date else None,
            message=msg.message,
            views=msg.views if hasattr(msg, "views") else None,
        ))

    if not new_messages:
        logger.info(f"  No new messages (processed {count_processed}).")
        return 0

    # Insert with retry (longer delays for Render free-tier recovery)
    for attempt in range(3):
        try:
            count = _db_insert(channel_name, new_messages)
            logger.info(f"  Done. Processed {count_processed}, Inserted {count}.")
            return count
        except Exception as e:
            if attempt < 2:
                wait = 10 * (attempt + 1)  # 10s, 20s
                logger.warning(f"  DB insert attempt {attempt+1} failed, waiting {wait}s: {e}")
                await asyncio.sleep(wait)
                _ensure_db()
            else:
                logger.error(f"  DB insert failed after 3 attempts: {e}")
                return 0

    return 0


def run_scrape_all():
    """Entry point to run all scraping synchronously."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scrape_all_channels())
    finally:
        loop.close()


def create_telegram_table():
    """Create the TelegramMessage table if it doesn't exist."""
    if not conn.is_connected():
        conn.connect()

    if conn.engine:
        TelegramMessage.__table__.create(conn.engine, checkfirst=True)
        logger.info("Checked/Created TelegramMessage table.")
    else:
        logger.error("Could not connect to database to create table.")


async def scrape_channel(channel_name: str, limit: int = 100):
    """Scrape a single channel (standalone, creates its own client)."""
    if TelegramClient is None:
        logger.error("telethon is not installed.")
        return

    if not API_ID or not API_HASH:
        logger.error("TELEGRAM_API_ID and TELEGRAM_API_HASH must be set.")
        return

    create_telegram_table()

    client = TelegramClient(SESSION_NAME, int(API_ID), API_HASH)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            logger.error("Telegram session expired.")
            return
        await _scrape_single(client, channel_name)
    finally:
        await client.disconnect()


def run_scraper(channel_name: str, limit: int = 100):
    """Entry point to run the scraper synchronously."""
    asyncio.run(scrape_channel(channel_name, limit))


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        run_scraper(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 100)
    else:
        print("Usage: python -m ix.misc.telegram [channel_name] [limit]")
