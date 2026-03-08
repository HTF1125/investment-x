"""
Shared task process utilities.

Extracted from ix.api.routers.task to avoid circular imports
when other routers need to track background processes.
"""

from datetime import datetime
from typing import Optional
from enum import Enum
from dataclasses import dataclass
import uuid
import asyncio

from pydantic import BaseModel
from ix.db.models.task_process import TaskProcess
from ix.db.conn import Session, ensure_connection, conn


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


@dataclass(frozen=True)
class TaskEventSubscriber:
    loop: asyncio.AbstractEventLoop
    queue: asyncio.Queue


# SSE subscriber queues — shared across the application
SSE_SUBSCRIBERS: set[TaskEventSubscriber] = set()


def _ensure_task_table():
    """Create task_process table on demand (safe during rollout)."""
    if not ensure_connection():
        raise ConnectionError("Failed to establish database connection")
    TaskProcess.__table__.create(bind=conn.engine, checkfirst=True)


def subscribe_task_events(
    queue: asyncio.Queue,
    loop: Optional[asyncio.AbstractEventLoop] = None,
) -> TaskEventSubscriber:
    subscriber = TaskEventSubscriber(loop=loop or asyncio.get_running_loop(), queue=queue)
    SSE_SUBSCRIBERS.add(subscriber)
    return subscriber


def unsubscribe_task_events(subscriber: TaskEventSubscriber) -> None:
    SSE_SUBSCRIBERS.discard(subscriber)


def _deliver_task_event(subscriber: TaskEventSubscriber, payload: dict) -> None:
    if subscriber.queue.full():
        try:
            subscriber.queue.get_nowait()
        except asyncio.QueueEmpty:
            pass
    try:
        subscriber.queue.put_nowait(payload)
    except asyncio.QueueFull:
        try:
            subscriber.queue.get_nowait()
        except asyncio.QueueEmpty:
            pass
        try:
            subscriber.queue.put_nowait(payload)
        except asyncio.QueueFull:
            pass


def _broadcast_task_event(event: str, pid: str):
    payload = {"event": event, "task_id": pid, "ts": datetime.now().isoformat()}
    stale = []
    for subscriber in list(SSE_SUBSCRIBERS):
        try:
            if subscriber.loop.is_closed():
                stale.append(subscriber)
                continue
            subscriber.loop.call_soon_threadsafe(
                _deliver_task_event,
                subscriber,
                payload,
            )
        except Exception:
            stale.append(subscriber)
    for subscriber in stale:
        SSE_SUBSCRIBERS.discard(subscriber)


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


def get_process(pid: str) -> Optional[ProcessInfo]:
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
