import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime
from ix.db.conn import get_session
from ix.db.models.briefing import Briefings
from ix.api.dependencies import get_current_admin_user, get_optional_user
from ix.api.rate_limit import limiter as _limiter
from ix.api.schemas import ensure_tz

logger = logging.getLogger(__name__)

router = APIRouter()


def _is_valid_date(name: str) -> bool:
    if len(name) != 10:
        return False
    try:
        datetime.strptime(name, "%Y-%m-%d")
        return True
    except ValueError:
        return False


@router.get("/briefings")
@_limiter.limit("30/minute")
def list_briefings(
    request: Request,
    db: Session = Depends(get_session),
    _user=Depends(get_optional_user),
):
    """List available briefing dates."""
    rows = (
        db.query(
            Briefings.date,
            Briefings.briefing.isnot(None).label("has_briefing"),
        )
        .order_by(Briefings.date.desc())
        .all()
    )
    return [
        {
            "date": r.date.isoformat(),
            "has_briefing": r.has_briefing,
        }
        for r in rows
    ]


@router.get("/briefings/{date}")
@_limiter.limit("30/minute")
def get_briefing(
    request: Request,
    date: str,
    db: Session = Depends(get_session),
    _user=Depends(get_optional_user),
):
    """Return the full briefing for a given date."""
    if not _is_valid_date(date):
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    report_date = datetime.strptime(date, "%Y-%m-%d").date()
    row = (
        db.query(
            Briefings.briefing,
            Briefings.sources,
            Briefings.updated_at,
        )
        .filter(Briefings.date == report_date)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail=f"No briefing found for {date}")

    return {
        "date": date,
        "briefing": row.briefing,
        "sources": row.sources or {},
        "updated_at": ensure_tz(row.updated_at).isoformat() if row.updated_at else None,
    }


def _send_briefing_email_task(report_date: str) -> None:
    """Background task: render and send the briefing email to all admins."""
    from ix.common.notify.briefing_email import send_briefing_email

    try:
        result = send_briefing_email(report_date)
        logger.info(
            "Briefing email sent for %s to %d recipients (languages=%s)",
            report_date,
            result["recipients_count"],
            ",".join(result["languages"]),
        )
    except Exception:
        logger.exception("Failed to send briefing email for %s", report_date)


@router.post("/briefings/{date}/send-email")
@_limiter.limit("5/minute")
def send_briefing_email_route(
    request: Request,
    date: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_session),
    _user=Depends(get_current_admin_user),
):
    """Queue sending of the briefing email for a given date to all admin users.

    Admin/owner only. Returns immediately; SMTP delivery runs in a background task.
    """
    if not _is_valid_date(date):
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    report_date = datetime.strptime(date, "%Y-%m-%d").date()
    row = (
        db.query(Briefings.briefing)
        .filter(Briefings.date == report_date, Briefings.briefing.isnot(None))
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail=f"No briefing found for {date}")

    # Resolve recipients up-front so we can return the count and surface a
    # clear 400 if none exist — the actual send still happens in background.
    from ix.common.notify.briefing_email import load_admin_recipients

    recipients = load_admin_recipients()
    if not recipients:
        raise HTTPException(
            status_code=400,
            detail="No admin/owner users with email addresses found",
        )

    background_tasks.add_task(_send_briefing_email_task, date)

    return {
        "status": "queued",
        "date": date,
        "recipients_count": len(recipients),
        "message": f"Briefing email queued for {len(recipients)} admin(s).",
    }
