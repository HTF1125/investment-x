from datetime import datetime
from typing import Optional, List, Dict
from enum import Enum
import uuid
import asyncio
from threading import RLock
import json
from pydantic import BaseModel

from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from fastapi.responses import StreamingResponse
from ix.api.dependencies import get_current_user
from ix.db.models.user import User
from ix.db.models.task_process import TaskProcess
from ix.db.conn import Session, ensure_connection, conn
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


REGISTRY_LOCK = RLock()
SSE_SUBSCRIBERS: set[asyncio.Queue] = set()


def _ensure_task_table():
    """Create task_process table on demand (safe during rollout)."""
    if not ensure_connection():
        raise ConnectionError("Failed to establish database connection")
    TaskProcess.__table__.create(bind=conn.engine, checkfirst=True)


def _broadcast_task_event(event: str, pid: str):
    payload = {"event": event, "task_id": pid, "ts": datetime.now().isoformat()}
    stale = []
    for q in list(SSE_SUBSCRIBERS):
        try:
            q.put_nowait(payload)
        except Exception:
            stale.append(q)
    for q in stale:
        SSE_SUBSCRIBERS.discard(q)


def start_process(name: str, user_id: str = None) -> str:
    """Register a new process as running. Returns process ID."""
    pid = str(uuid.uuid4())
    _ensure_task_table()
    safe_user_id = user_id
    if safe_user_id:
        try:
            uuid.UUID(str(safe_user_id))
            safe_user_id = str(safe_user_id)
        except Exception:
            safe_user_id = None
    with Session() as db:
        db.add(
            TaskProcess(
                id=pid,
                name=name,
                status=ProcessStatus.RUNNING.value,
                start_time=datetime.now(),
                user_id=safe_user_id,
                message="Started",
            )
        )
    _broadcast_task_event("created", pid)
    return pid


def _get_process(pid: str) -> Optional[ProcessInfo]:
    _ensure_task_table()
    with Session() as db:
        proc = db.query(TaskProcess).filter(TaskProcess.id == pid).first()
        if not proc:
            return None
        return ProcessInfo(
            id=pid,
            name=proc.name,
            status=ProcessStatus(proc.status),
            start_time=proc.start_time.isoformat(),
            end_time=proc.end_time.isoformat() if proc.end_time else None,
            message=proc.message,
            progress=proc.progress,
            user_id=proc.user_id,
        )


def update_process(
    pid: str,
    status: ProcessStatus | None = None,
    message: str | None = None,
    progress: str | None = None,
):
    """Update a tracked process with new status, message, or progress."""
    _ensure_task_table()
    with Session() as db:
        proc = db.query(TaskProcess).filter(TaskProcess.id == pid).first()
        if not proc:
            return
        if status:
            proc.status = status.value if isinstance(status, ProcessStatus) else status
        if message:
            proc.message = message
        if progress is not None:
            proc.progress = progress
        if status in (ProcessStatus.COMPLETED, ProcessStatus.FAILED):
            proc.end_time = datetime.now()
    _broadcast_task_event("updated", pid)


# ═══════════════════════════════════════════════════════════
# Background task wrappers — each registers in persistent task storage
# ═══════════════════════════════════════════════════════════


def _run_daily_update():
    """Synchronous wrapper for the full daily pipeline with progress tracking."""
    pid = start_process("Daily Data Update")
    try:
        from ix.db.models import Timeseries
        from ix.misc.task import update_yahoo_data, update_fred_data, update_naver_data

        with Session() as db:
            yahoo_total = db.query(Timeseries).filter(Timeseries.source == "Yahoo").count()
            fred_total = db.query(Timeseries).filter(Timeseries.source == "Fred").count()
            naver_total = db.query(Timeseries).filter(Timeseries.source == "Naver").count()

        total_tickers = max(1, yahoo_total + fred_total + naver_total)
        update_process(
            pid,
            message=f"Starting daily update (0/{total_tickers})...",
            progress=f"0/{total_tickers}",
        )

        def _on_ticker_progress(current: int, total: int, ts_code: str):
            update_process(
                pid,
                message=f"Updating {ts_code} ({current}/{total})",
                progress=f"{current}/{total}",
            )

        update_yahoo_data(progress_cb=_on_ticker_progress, start_index=0, total_count=total_tickers)
        update_fred_data(progress_cb=_on_ticker_progress, start_index=yahoo_total, total_count=total_tickers)
        update_naver_data(progress_cb=_on_ticker_progress, start_index=yahoo_total + fred_total, total_count=total_tickers)

        update_process(
            pid,
            message=f"Refreshing charts ({total_tickers}/{total_tickers})...",
            progress=f"{total_tickers}/{total_tickers}",
        )
        from ix.misc.task import refresh_all_charts

        refresh_all_charts()

        update_process(
            pid,
            status=ProcessStatus.COMPLETED,
            message="Daily update completed.",
            progress=f"{total_tickers}/{total_tickers}",
        )
    except Exception as e:
        update_process(pid, status=ProcessStatus.FAILED, message=str(e))


def _run_send_reports():
    """Synchronous wrapper for email report sending."""
    pid = start_process("Send Email Reports")
    try:
        update_process(pid, message="Loading data for reports...", progress="1/3")
        update_process(pid, message="Building report files...", progress="2/3")
        send_data_reports()
        update_process(
            pid,
            status=ProcessStatus.COMPLETED,
            message="Reports sent successfully.",
            progress="3/3",
        )
    except Exception as e:
        update_process(pid, status=ProcessStatus.FAILED, message=str(e))


def _run_send_brief():
    """Synchronous wrapper for daily market brief."""
    pid = start_process("Daily Market Brief")
    try:
        update_process(pid, message="Collecting latest feed...", progress="1/3")
        update_process(pid, message="Generating market brief...", progress="2/3")
        send_daily_market_brief()
        update_process(
            pid,
            status=ProcessStatus.COMPLETED,
            message="Brief sent successfully.",
            progress="3/3",
        )
    except Exception as e:
        update_process(pid, status=ProcessStatus.FAILED, message=str(e))


async def _run_telegram_scrape():
    """Async wrapper for Telegram channel scraping."""
    pid = start_process("Telegram Sync")
    try:
        from ix.misc.telegram import scrape_all_channels, CHANNELS_TO_SCRAPE

        total_channels = max(1, len(CHANNELS_TO_SCRAPE))
        update_process(
            pid,
            message="Preparing Telegram sync...",
            progress=f"0/{total_channels}",
        )

        def _on_progress(current: int, total: int, channel: str):
            update_process(
                pid,
                message=f"Syncing {channel}...",
                progress=f"{current}/{total}",
            )

        await scrape_all_channels(progress_cb=_on_progress)
        update_process(
            pid,
            status=ProcessStatus.COMPLETED,
            message="Telegram sync completed.",
            progress=f"{total_channels}/{total_channels}",
        )
    except Exception as e:
        update_process(pid, status=ProcessStatus.FAILED, message=str(e))


def _run_refresh_charts(pid: Optional[str] = None):
    """Synchronous wrapper for chart refresh."""
    if pid is None:
        pid = start_process("Refresh Charts")
    try:
        from ix.misc.task import refresh_all_charts

        progress_state = {"current": 0, "total": 0}
        update_process(pid, message="Preparing chart refresh...", progress="0/0")

        def _on_progress(current: int, total: int, chart_code: str):
            progress_state["current"] = current
            progress_state["total"] = total
            update_process(
                pid,
                message=f"Refreshing chart {chart_code}...",
                progress=f"{current}/{total}",
            )

        refresh_all_charts(progress_cb=_on_progress)
        final_total = progress_state["total"]
        if final_total == 0:
            final_progress = "0/0"
        else:
            final_progress = f"{final_total}/{final_total}"
        update_process(
            pid,
            status=ProcessStatus.COMPLETED,
            message="Charts refreshed.",
            progress=final_progress,
        )
    except Exception as e:
        update_process(pid, status=ProcessStatus.FAILED, message=str(e))


# ═══════════════════════════════════════════════════════════
# API Endpoints
# ═══════════════════════════════════════════════════════════


@router.get("/task/processes", response_model=List[ProcessInfo])
async def get_processes(current_user: User = Depends(get_current_user)):
    """Get all tracked processes, sorted by start time desc (max 30)."""
    _ensure_task_table()
    with Session() as db:
        rows = (
            db.query(TaskProcess).order_by(TaskProcess.start_time.desc()).limit(200).all()
        )
    merged = {
        p.id: ProcessInfo(
            id=p.id,
            name=p.name,
            status=ProcessStatus(p.status),
            start_time=p.start_time.isoformat(),
            end_time=p.end_time.isoformat() if p.end_time else None,
            message=p.message,
            progress=p.progress,
            user_id=p.user_id,
        )
        for p in rows
    }
    procs = sorted(merged.values(), key=lambda x: x.start_time, reverse=True)
    return procs[:30]


@router.get("/task/stream")
async def stream_process_events(current_user: User = Depends(get_current_user)):
    """SSE stream for task updates. Client should refetch /task/processes on each event."""
    queue: asyncio.Queue = asyncio.Queue()
    SSE_SUBSCRIBERS.add(queue)

    async def event_generator():
        try:
            # Initial handshake event
            yield "event: ready\ndata: {\"ok\":true}\n\n"
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=20.0)
                    yield f"event: task\ndata: {json.dumps(msg)}\n\n"
                except asyncio.TimeoutError:
                    # Keep-alive comment
                    yield ": keep-alive\n\n"
        finally:
            SSE_SUBSCRIBERS.discard(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _is_task_running(name_prefix: str) -> bool:
    """Check if any process with the given name prefix is currently running."""
    _ensure_task_table()
    with Session() as db:
        row = (
            db.query(TaskProcess.id)
            .filter(
                TaskProcess.status == ProcessStatus.RUNNING.value,
                TaskProcess.name.like(f"{name_prefix}%"),
            )
            .first()
        )
    return row is not None


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
    if not _get_process(pid):
        raise HTTPException(status_code=404, detail="Process not found")
    update_process(pid, status=status, message=message, progress=progress)
    return {"status": "updated"}


@router.delete("/task/process/{pid}")
async def delete_client_process(pid: str):
    """Delete a process from DB-backed task store."""
    _ensure_task_table()
    with Session() as db:
        db.query(TaskProcess).filter(TaskProcess.id == pid).delete()
    _broadcast_task_event("deleted", pid)
    return {"status": "deleted"}


@router.post("/task/process/{pid}/dismiss")
async def dismiss_process(pid: str, current_user: User = Depends(get_current_user)):
    """Dismiss a task by deleting it from persistent DB storage."""
    _ensure_task_table()
    with Session() as db:
        db.query(TaskProcess).filter(TaskProcess.id == pid).delete()
    _broadcast_task_event("deleted", pid)
    return {"status": "dismissed"}


@router.post("/task/process/dismiss-completed")
async def dismiss_completed_processes(current_user: User = Depends(get_current_user)):
    """Clear all completed/failed tasks from persistent store."""
    _ensure_task_table()
    deleted_ids: list[str] = []
    with Session() as db:
        rows = (
            db.query(TaskProcess.id)
            .filter(TaskProcess.status.in_([ProcessStatus.COMPLETED.value, ProcessStatus.FAILED.value]))
            .all()
        )
        deleted_ids = [r.id for r in rows]
        if deleted_ids:
            db.query(TaskProcess).filter(TaskProcess.id.in_(deleted_ids)).delete(synchronize_session=False)

    for pid in deleted_ids:
        _broadcast_task_event("deleted", pid)
    return {"status": "cleared_completed", "count": len(deleted_ids)}


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

    # Register process immediately so clients can see it in the next poll cycle.
    pid = start_process("Refresh Charts")
    background_tasks.add_task(_run_refresh_charts, pid)
    return {"message": "Chart refresh triggered", "status": "started", "task_id": pid}


# Legacy endpoint for backward compat
@router.get("/task/status")
async def get_task_status():
    """Legacy status check — returns running state for daily/telegram tasks."""
    daily_running = _is_task_running("Daily Data Update")
    telegram_running = _is_task_running("Telegram Sync")

    # Find latest process for each to get the message
    def latest_msg(prefix: str) -> str:
        _ensure_task_table()
        with Session() as db:
            latest = (
                db.query(TaskProcess)
                .filter(TaskProcess.name.like(f"{prefix}%"))
                .order_by(TaskProcess.start_time.desc())
                .first()
            )
            if not latest:
                return "Idle"
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
