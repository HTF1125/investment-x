import asyncio
import json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session as SessionType

from ix.api.dependencies import get_current_admin_user, get_db
from ix.db.conn import Session
from ix.db.models.runtime_log import RuntimeLog
from ix.db.models.user import User
from ix.db.models.system_setting import SystemSetting
from ix.misc import get_logger

logger = get_logger(__name__)

router = APIRouter()

# ─────────────────────────────────────────────────────────────────────────────
# Role permissions — feature-level access control
# ─────────────────────────────────────────────────────────────────────────────

ROLE_PERMISSIONS_KEY = "role_permissions"

# Features and their default minimum role (who can access).
# "general" = all users, "admin" = admin+owner, "owner" = owner only.
FEATURE_DEFAULTS: dict[str, str] = {
    "dashboard": "general",
    "intel": "general",
    "technical": "general",
    "notes": "general",
}

VALID_ROLES = {"general", "admin", "owner"}


class RolePermissionsPayload(BaseModel):
    permissions: dict[str, str]


def _load_permissions(db: SessionType) -> dict[str, str]:
    setting = db.query(SystemSetting).filter_by(key=ROLE_PERMISSIONS_KEY).first()
    stored: dict = setting.value if setting else {}
    return {**FEATURE_DEFAULTS, **{k: v for k, v in stored.items() if k in FEATURE_DEFAULTS and v in VALID_ROLES}}


@router.get("/admin/settings/role_permissions")
def get_role_permissions(
    db: SessionType = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> dict:
    return _load_permissions(db)


@router.put("/admin/settings/role_permissions")
def set_role_permissions(
    payload: RolePermissionsPayload,
    db: SessionType = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> dict:
    # Validate: only known features and valid roles
    validated = {}
    for feature, role in payload.permissions.items():
        if feature not in FEATURE_DEFAULTS:
            raise HTTPException(status_code=400, detail=f"Unknown feature: {feature!r}")
        if role not in VALID_ROLES:
            raise HTTPException(status_code=400, detail=f"Invalid role: {role!r}")
        validated[feature] = role

    merged = {**FEATURE_DEFAULTS, **validated}

    setting = db.query(SystemSetting).filter_by(key=ROLE_PERMISSIONS_KEY).first()
    if setting:
        setting.value = merged
    else:
        db.add(SystemSetting(key=ROLE_PERMISSIONS_KEY, value=merged))
    db.commit()

    logger.info(f"Admin {current_user.email} updated role permissions: {merged}")
    return merged


class AdminUserResponse(BaseModel):
    id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str = User.ROLE_GENERAL
    is_admin: bool = False
    disabled: bool = False
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[str] = None
    is_admin: bool = False
    disabled: bool = False


class AdminUserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[str] = None
    is_admin: Optional[bool] = None
    disabled: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=6)


class RuntimeLogResponse(BaseModel):
    id: str
    level: str
    logger_name: str
    module: Optional[str] = None
    function: Optional[str] = None
    message: str
    path: Optional[str] = None
    line_no: Optional[int] = None
    service: Optional[str] = None
    exception: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


def _parse_role_or_raise(role: str) -> str:
    role_clean = (role or "").strip().lower()
    if role_clean not in User.VALID_ROLES:
        raise HTTPException(
            status_code=400,
            detail="Invalid role. Allowed values: owner, admin, general",
        )
    return role_clean


def _resolve_role_for_create(payload: AdminUserCreate) -> str:
    if payload.role is not None:
        return _parse_role_or_raise(payload.role)
    return User.ROLE_ADMIN if bool(payload.is_admin) else User.ROLE_GENERAL


def _resolve_role_for_update(
    payload: AdminUserUpdate,
    current_role: str,
) -> str:
    if payload.role is not None:
        return _parse_role_or_raise(payload.role)
    if payload.is_admin is not None:
        return User.ROLE_ADMIN if bool(payload.is_admin) else User.ROLE_GENERAL
    return current_role


def _active_admin_count(db: SessionType) -> int:
    return (
        db.query(func.count(User.id))
        .filter(
            User.role.in_(list(User.ADMIN_ROLES)),
            User.disabled == False,
        )
        .scalar()
        or 0
    )


def _normalize_log_level(level: Optional[str]) -> Optional[str]:
    level_clean = (level or "").strip().upper()
    return level_clean or None


def _runtime_logs_query(
    db: SessionType,
    *,
    level: Optional[str] = None,
    search: Optional[str] = None,
):
    query = db.query(RuntimeLog)

    normalized_level = _normalize_log_level(level)
    if normalized_level:
        query = query.filter(RuntimeLog.level == normalized_level)

    search_term = (search or "").strip()
    if search_term:
        pattern = f"%{search_term}%"
        query = query.filter(
            or_(
                RuntimeLog.message.ilike(pattern),
                RuntimeLog.logger_name.ilike(pattern),
                RuntimeLog.module.ilike(pattern),
                RuntimeLog.function.ilike(pattern),
                RuntimeLog.service.ilike(pattern),
                RuntimeLog.exception.ilike(pattern),
            )
        )

    return query


def _latest_runtime_log_signature(
    *,
    level: Optional[str] = None,
    search: Optional[str] = None,
) -> Optional[dict[str, str]]:
    with Session() as db:
        row = (
            _runtime_logs_query(db, level=level, search=search)
            .order_by(RuntimeLog.created_at.desc(), RuntimeLog.id.desc())
            .first()
        )
        if not row:
            return None
        return {
            "id": str(row.id),
            "created_at": row.created_at.isoformat() if row.created_at else "",
            "level": row.level,
        }


def _to_response(user: User) -> AdminUserResponse:
    role = user.effective_role
    return AdminUserResponse(
        id=str(user.id),
        email=str(user.email),
        first_name=user.first_name,
        last_name=user.last_name,
        role=role,
        is_admin=bool(role in User.ADMIN_ROLES),
        disabled=bool(user.disabled),
        created_at=user.created_at,
    )


@router.get("/admin/logs", response_model=List[RuntimeLogResponse])
def list_runtime_logs(
    level: Optional[str] = Query(None, description="Filter by log level"),
    search: Optional[str] = Query(None, description="Search logger, module, or message"),
    limit: int = Query(200, ge=1, le=1000),
    db: SessionType = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    logs = (
        _runtime_logs_query(db, level=level, search=search)
        .order_by(RuntimeLog.created_at.desc(), RuntimeLog.id.desc())
        .limit(limit)
        .all()
    )
    return [
        RuntimeLogResponse(
            id=str(log.id),
            level=log.level,
            logger_name=log.logger_name,
            module=log.module,
            function=log.function,
            message=log.message,
            path=log.path,
            line_no=log.line_no,
            service=log.service,
            exception=log.exception,
            created_at=log.created_at,
        )
        for log in logs
    ]


@router.get("/admin/logs/stream")
async def stream_runtime_logs(
    level: Optional[str] = Query(None, description="Filter by log level"),
    search: Optional[str] = Query(None, description="Search logger, module, or message"),
    current_user: User = Depends(get_current_admin_user),
):
    async def event_generator():
        last_signature = _latest_runtime_log_signature(level=level, search=search)
        keep_alive = 0
        yield "event: ready\ndata: {\"ok\":true}\n\n"

        while True:
            await asyncio.sleep(2)
            try:
                latest_signature = _latest_runtime_log_signature(level=level, search=search)
            except Exception as exc:
                logger.warning("Runtime log stream poll failed: %s", exc)
                yield f"event: error\ndata: {json.dumps({'message': str(exc)})}\n\n"
                continue

            if latest_signature != last_signature:
                last_signature = latest_signature
                keep_alive = 0
                yield (
                    "event: log\n"
                    f"data: {json.dumps(latest_signature or {'id': None})}\n\n"
                )
                continue

            keep_alive += 1
            if keep_alive >= 10:
                keep_alive = 0
                yield ": keep-alive\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/admin/users", response_model=List[AdminUserResponse])
def list_users(
    search: Optional[str] = Query(None, description="Search by email or name"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: SessionType = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    query = db.query(User)

    if search:
        term = search.strip()
        if term:
            pattern = f"%{term}%"
            query = query.filter(
                or_(
                    User.email.ilike(pattern),
                    User.first_name.ilike(pattern),
                    User.last_name.ilike(pattern),
                )
            )

    role_order = case(
        (User.role == User.ROLE_OWNER, 0),
        (User.role == User.ROLE_ADMIN, 1),
        else_=2,
    )
    users = (
        query.order_by(
            role_order.asc(),
            User.disabled.asc(),
            User.created_at.desc().nullslast(),
            User.email.asc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [_to_response(u) for u in users]


@router.post("/admin/users", response_model=AdminUserResponse, status_code=201)
def create_user(
    payload: AdminUserCreate,
    db: SessionType = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    email = payload.email.strip().lower()
    exists = db.query(User).filter(func.lower(User.email) == email).first()
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )

    resolved_role = _resolve_role_for_create(payload)
    new_user = User(
        email=email,
        password=User.hash_password(payload.password),
        first_name=payload.first_name,
        last_name=payload.last_name,
        role=resolved_role,
        is_admin=bool(resolved_role in User.ADMIN_ROLES),
        disabled=bool(payload.disabled),
        created_at=datetime.utcnow(),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(f"Admin {current_user.email} created user {new_user.email} (role={new_user.role})")
    return _to_response(new_user)


@router.patch("/admin/users/{user_id}", response_model=AdminUserResponse)
def update_user(
    user_id: str,
    payload: AdminUserUpdate,
    db: SessionType = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    is_self = str(user.id) == str(current_user.id)

    current_role = user.effective_role
    target_role = _resolve_role_for_update(payload, current_role=current_role)
    target_was_active_admin = current_role in User.ADMIN_ROLES and not bool(user.disabled)
    target_will_be_admin = target_role in User.ADMIN_ROLES
    target_will_be_disabled = bool(user.disabled) if payload.disabled is None else bool(payload.disabled)
    target_will_be_active_admin = target_will_be_admin and not target_will_be_disabled

    # Prevent self lockout.
    if is_self and payload.disabled is True:
        raise HTTPException(status_code=400, detail="You cannot disable your own account")
    if is_self and target_role not in User.ADMIN_ROLES:
        raise HTTPException(status_code=400, detail="You cannot revoke your own admin role")

    # Ensure there is always at least one active admin.
    if target_was_active_admin and not target_will_be_active_admin:
        if _active_admin_count(db) <= 1:
            raise HTTPException(
                status_code=400,
                detail="At least one active admin account is required",
            )

    if payload.first_name is not None:
        user.first_name = payload.first_name
    if payload.last_name is not None:
        user.last_name = payload.last_name
    user.role = target_role
    user.is_admin = bool(target_role in User.ADMIN_ROLES)
    if payload.disabled is not None:
        user.disabled = bool(payload.disabled)
    if payload.password:
        user.password = User.hash_password(payload.password)

    db.commit()
    db.refresh(user)

    logger.info(
        f"Admin {current_user.email} updated user {user.email} "
        f"(role={user.role}, disabled={user.disabled})"
    )
    return _to_response(user)


@router.delete("/admin/users/{user_id}")
def delete_user(
    user_id: str,
    db: SessionType = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    is_self = str(user.id) == str(current_user.id)
    if is_self:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")

    if user.effective_role in User.ADMIN_ROLES and not bool(user.disabled):
        if _active_admin_count(db) <= 1:
            raise HTTPException(
                status_code=400,
                detail="At least one active admin account is required",
            )

    db.delete(user)
    db.commit()

    logger.info(f"Admin {current_user.email} deleted user {user.email}")
    return {"message": "User deleted successfully"}
