import asyncio
import os
from typing import Optional
from datetime import datetime, timedelta
from ix.misc.terminal import get_logger
from ix.db.conn import Session, conn, Base
from ix.db.models import TelegramMessage

try:
    from telethon import TelegramClient
    from telethon.tl.types import Message
except ImportError:
    TelegramClient = None
    Message = None

logger = get_logger(__name__)

# Constants for Telegram API
# Users should set these in their environment variables
API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
SESSION_NAME = os.getenv("TELEGRAM_SESSION_NAME", "ix_session")


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
    """
    Scrape messages from a Telegram channel and store them in the database.

    Args:
        channel_name (str): The username or URL of the telegram channel (e.g. 'bloomberg').
        limit (int): Number of messages to retrieve.
    """
    if TelegramClient is None:
        logger.error("telethon is not installed. Please run `pip install telethon`.")
        return

    if not API_ID or not API_HASH:
        logger.error(
            "TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in environment variables (e.g. .env file)."
        )
        return

    # Create table if needed
    create_telegram_table()

    client = TelegramClient(SESSION_NAME, int(API_ID), API_HASH)

    try:
        await client.start()
    except Exception as e:
        logger.error(
            f"Failed to start Telegram client. Interaction might be needed for login: {e}"
        )
        return

    logger.info(f"Scraping {channel_name}...")

    count_new = 0
    count_processed = 0
    new_messages = []

    try:
        # Get channel entity
        try:
            entity = await client.get_input_entity(channel_name)
        except Exception as e:
            logger.error(f"Could not find entity '{channel_name}': {e}")
            await client.disconnect()
            return

        # 1. Determine start point (min_id)
        # We want to fetch messages newer than what we already have.
        min_id = 0

        with Session() as session:
            # check the latest message_id for this channel
            last_msg = (
                session.query(TelegramMessage.message_id)
                .filter(TelegramMessage.channel_name == channel_name)
                .order_by(TelegramMessage.message_id.desc())
                .first()
            )
            if last_msg:
                min_id = last_msg[0]
                logger.info(f"Latest known message_id for {channel_name}: {min_id}")
            else:
                logger.info(
                    f"No existing messages found for {channel_name}. Doing initial scrape."
                )

        # 2. Fetch messages
        # Strategy:
        # - If we have min_id (incremental): Fetch newly added messages (up to safety limit).
        # - If NO min_id (initial): Fetch messages from the last 24 hours using offset_date.

        scrape_limit = None
        offset_date = None

        if min_id > 0:
            # Incremental update: Get everything new
            scrape_limit = 2000  # Safety cap
        else:
            # Initial scrape: Get last 24 hours
            offset_date = datetime.utcnow() - timedelta(hours=24)
            logger.info("Doing initial scrape for last 24 hours of messages.")
            # We set a high limit because we want ALL messages in that window
            scrape_limit = 2000

        async for msg in client.iter_messages(
            entity, limit=scrape_limit, min_id=min_id
        ):
            # If doing initial scrape (no min_id), stop if we go beyond 24 hours
            if min_id == 0 and offset_date and msg.date:
                # msg.date is offset-aware usually (UTC), offset_date is naive UTC in my code above?
                # Let's make offset_date offset-aware to match
                if msg.date.replace(tzinfo=None) < offset_date:
                    logger.info(
                        "Reached messages older than 24 hours. Stopping initial scrape."
                    )
                    break
            count_processed += 1
            if not msg.message:
                continue

            # Basic info extraction
            # msg.id is the ID within the channel
            t_msg = TelegramMessage(
                channel_name=channel_name,
                message_id=msg.id,
                sender_id=msg.sender_id,
                sender_name=None,  # Extracting sender name requires more calls usually if it's a user
                # Convert UTC to KST (+9h) before storing
                date=(
                    (msg.date.replace(tzinfo=None) + timedelta(hours=9))
                    if msg.date
                    else None
                ),
                message=msg.message,
                views=msg.views if hasattr(msg, "views") else None,
            )
            new_messages.append(t_msg)

        # Batch insert
        if new_messages:
            with Session() as session:
                # 3. Deduplicate (just in case)
                # Since we used min_id, duplication should be rare, but
                # let's double check to be safe against race conditions or overlapping IDs.
                msg_ids = [m.message_id for m in new_messages]
                existing = (
                    session.query(TelegramMessage.message_id)
                    .filter(TelegramMessage.channel_name == channel_name)
                    .filter(TelegramMessage.message_id.in_(msg_ids))
                    .all()
                )
                existing_ids = {r[0] for r in existing}

                to_insert = [
                    m for m in new_messages if m.message_id not in existing_ids
                ]

                if to_insert:
                    session.add_all(to_insert)
                    session.commit()
                    count_new = len(to_insert)
                    logger.info(f"Inserted {count_new} new messages.")
                else:
                    logger.info("No new messages to insert (filtered duplicates).")
        else:
            logger.info("No new messages found on Telegram.")

    except Exception as e:
        logger.error(f"Error during scraping: {e}")
    finally:
        await client.disconnect()

    logger.info(f"Finished. Processed {count_processed}, Inserted {count_new}.")


def run_scraper(channel_name: str, limit: int = 100):
    """Entry point to run the scraper synchronously."""
    asyncio.run(scrape_channel(channel_name, limit))


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        run_scraper(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 100)
    else:
        print("Usage: python -m ix.misc.telegram [channel_name] [limit]")
