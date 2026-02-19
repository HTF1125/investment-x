from datetime import datetime
from typing import Dict, Optional, List
from enum import Enum
import uuid
import asyncio
import traceback
from pydantic import BaseModel

from fastapi import APIRouter, BackgroundTasks, HTTPException
from ix.misc.task import (
    daily,
    send_data_reports,
    send_daily_market_brief,
    run_daily_tasks,
)

router = APIRouter()

# ═══════════════════════════════════════════════════════════
# Process Registry — unified task tracking
# ═══════════════════════════════════════════════════════════


class ProcessStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessInfo(BaseModel):
    id: str
    name: str
    status: ProcessStatus
    start_time: str
    end_time: Optional[str] = None
    message: Optional[str] = None
    progress: Optional[str] = None
    user_id: Optional[str] = None


# Global in-memory registry
PROCESS_REGISTRY: Dict[str, ProcessInfo] = {}


def start_process(name: str, user_id: str = None) -> str:
    """Register a new process as running. Returns process ID."""
    pid = str(uuid.uuid4())
    PROCESS_REGISTRY[pid] = ProcessInfo(
        id=pid,
        name=name,
        status=ProcessStatus.RUNNING,
        start_time=datetime.now().isoformat(),
        user_id=user_id,
        message="Started",
    )
    # Prune old entries to cap memory
    _prune_registry()
    return pid


def update_process(
    pid: str,
    status: ProcessStatus | None = None,
    message: str | None = None,
    progress: str | None = None,
):
    """Update a tracked process with new status, message, or progress."""
    proc = PROCESS_REGISTRY.get(pid)
    if not proc:
        return
    if status:
        proc.status = status
    if message:
        proc.message = message
    if progress is not None:
        proc.progress = progress
    if status in (ProcessStatus.COMPLETED, ProcessStatus.FAILED):
        proc.end_time = datetime.now().isoformat()


def _prune_registry(max_items: int = 100):
    """Keep only the most recent N processes to avoid unbounded memory growth."""
    if len(PROCESS_REGISTRY) <= max_items:
        return
    sorted_pids = sorted(
        PROCESS_REGISTRY.keys(),
        key=lambda k: PROCESS_REGISTRY[k].start_time,
    )
    # Remove oldest entries
    for pid in sorted_pids[: len(sorted_pids) - max_items]:
        del PROCESS_REGISTRY[pid]


# ═══════════════════════════════════════════════════════════
# Background task wrappers — each registers in PROCESS_REGISTRY
# ═══════════════════════════════════════════════════════════


def _run_daily_update():
    """Synchronous wrapper for the full daily pipeline with progress tracking."""
    pid = start_process("Daily Data Update")
    try:
        update_process(pid, message="Updating Yahoo data...", progress="1/4")
        from ix.misc.task import update_yahoo_data

        update_yahoo_data()

        update_process(pid, message="Updating FRED data...", progress="2/4")
        from ix.misc.task import update_fred_data

        update_fred_data()

        update_process(pid, message="Updating Naver data...", progress="3/4")
        from ix.misc.task import update_naver_data

        update_naver_data()

        update_process(pid, message="Refreshing charts...", progress="4/4")
        from ix.misc.task import refresh_all_charts

        refresh_all_charts()

        update_process(
            pid,
            status=ProcessStatus.COMPLETED,
            message="Daily update completed.",
            progress="4/4",
        )
    except Exception as e:
        update_process(pid, status=ProcessStatus.FAILED, message=str(e))


def _run_send_reports():
    """Synchronous wrapper for email report sending."""
    pid = start_process("Send Email Reports")
    try:
        update_process(pid, message="Preparing data exports...")
        send_data_reports()
        update_process(
            pid, status=ProcessStatus.COMPLETED, message="Reports sent successfully."
        )
    except Exception as e:
        update_process(pid, status=ProcessStatus.FAILED, message=str(e))


def _run_send_brief():
    """Synchronous wrapper for daily market brief."""
    pid = start_process("Daily Market Brief")
    try:
        update_process(pid, message="Generating market brief...")
        send_daily_market_brief()
        update_process(
            pid, status=ProcessStatus.COMPLETED, message="Brief sent successfully."
        )
    except Exception as e:
        update_process(pid, status=ProcessStatus.FAILED, message=str(e))


async def _run_telegram_scrape():
    """Async wrapper for Telegram channel scraping."""
    pid = start_process("Telegram Sync")
    try:
        from ix.misc.telegram import scrape_all_channels

        update_process(pid, message="Syncing Telegram channels...")
        await scrape_all_channels()
        update_process(
            pid, status=ProcessStatus.COMPLETED, message="Telegram sync completed."
        )
    except Exception as e:
        update_process(pid, status=ProcessStatus.FAILED, message=str(e))


def _run_refresh_charts():
    """Synchronous wrapper for chart refresh."""
    pid = start_process("Refresh Charts")
    try:
        from ix.misc.task import refresh_all_charts

        update_process(pid, message="Refreshing all charts...")
        refresh_all_charts()
        update_process(pid, status=ProcessStatus.COMPLETED, message="Charts refreshed.")
    except Exception as e:
        update_process(pid, status=ProcessStatus.FAILED, message=str(e))


# ═══════════════════════════════════════════════════════════
# API Endpoints
# ═══════════════════════════════════════════════════════════


@router.get("/task/processes", response_model=List[ProcessInfo])
async def get_processes():
    """Get all tracked processes, sorted by start time desc (max 30)."""
    procs = sorted(
        PROCESS_REGISTRY.values(),
        key=lambda x: x.start_time,
        reverse=True,
    )
    return procs[:30]


def _is_task_running(name_prefix: str) -> bool:
    """Check if any process with the given name prefix is currently running."""
    return any(
        p.status == ProcessStatus.RUNNING and p.name.startswith(name_prefix)
        for p in PROCESS_REGISTRY.values()
    )


@router.post("/task/process/start", response_model=Dict[str, str])
async def start_client_process(name: str, user_id: str = None):
    """Allow client to register a new process (e.g. multi-file upload)."""
    pid = start_process(name, user_id)
    return {"id": pid}


@router.patch("/task/process/{pid}")
async def update_client_process(
    pid: str,
    status: Optional[ProcessStatus] = None,
    message: Optional[str] = None,
    progress: Optional[str] = None,
):
    """Allow client to update a registered process."""
    if pid not in PROCESS_REGISTRY:
        raise HTTPException(status_code=404, detail="Process not found")
    update_process(pid, status=status, message=message, progress=progress)
    return {"status": "updated"}


@router.post("/task/daily")
async def run_daily_task(background_tasks: BackgroundTasks):
    """Trigger the full daily routine (update data + refresh charts) in background."""
    if _is_task_running("Daily Data Update"):
        raise HTTPException(status_code=400, detail="Daily task is already running")

    background_tasks.add_task(_run_daily_update)
    return {"message": "Daily task triggered", "status": "started"}


@router.post("/task/report")
async def run_report_task(background_tasks: BackgroundTasks):
    """Trigger email report sending in background."""
    if _is_task_running("Send Email Reports"):
        raise HTTPException(status_code=400, detail="Report task is already running")

    background_tasks.add_task(_run_send_reports)
    return {"message": "Report task triggered", "status": "started"}


@router.post("/task/brief")
async def run_market_brief_task(background_tasks: BackgroundTasks):
    """Trigger the Daily Market Brief in background."""
    if _is_task_running("Daily Market Brief"):
        raise HTTPException(status_code=400, detail="Brief task is already running")

    background_tasks.add_task(_run_send_brief)
    return {"message": "Market brief triggered", "status": "started"}


@router.post("/task/telegram")
async def run_telegram_scrape_task(background_tasks: BackgroundTasks):
    """Trigger Telegram scraping for all configured channels in background."""
    if _is_task_running("Telegram Sync"):
        raise HTTPException(status_code=400, detail="Telegram sync is already running")

    background_tasks.add_task(_run_telegram_scrape)
    return {"message": "Telegram sync triggered", "status": "started"}


@router.post("/task/refresh-charts")
async def run_refresh_charts_task(background_tasks: BackgroundTasks):
    """Trigger a refresh of all charts in background."""
    if _is_task_running("Refresh Charts"):
        raise HTTPException(status_code=400, detail="Chart refresh is already running")

    background_tasks.add_task(_run_refresh_charts)
    return {"message": "Chart refresh triggered", "status": "started"}


# Legacy endpoint for backward compat
@router.get("/task/status")
async def get_task_status():
    """Legacy status check — returns running state for daily/telegram tasks."""
    daily_running = _is_task_running("Daily Data Update")
    telegram_running = _is_task_running("Telegram Sync")

    # Find latest process for each to get the message
    def latest_msg(prefix: str) -> str:
        matches = [p for p in PROCESS_REGISTRY.values() if p.name.startswith(prefix)]
        if not matches:
            return "Idle"
        latest = max(matches, key=lambda x: x.start_time)
        return latest.message or "Idle"

    return {
        "daily": {
            "running": daily_running,
            "message": latest_msg("Daily Data Update"),
        },
        "telegram": {
            "running": telegram_running,
            "message": latest_msg("Telegram Sync"),
        },
    }
