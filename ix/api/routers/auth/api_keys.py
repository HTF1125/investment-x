"""API key management endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ix.api.dependencies import get_current_user
from ix.api.rate_limit import limiter as _limiter
from ix.db.models.api_key import ApiKey
from ix.db.models.user import User

router = APIRouter()

MAX_KEYS_PER_USER = 5


class ApiKeyCreate(BaseModel):
    name: str = "Default"


class ApiKeyCreatedResponse(BaseModel):
    id: str
    name: str
    key: str
    key_prefix: str
    created_at: Optional[datetime] = None


class ApiKeyListItem(BaseModel):
    id: str
    name: str
    key_prefix: str
    created_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None


@router.post("/auth/api-keys", status_code=201)
@_limiter.limit("5/minute")
def create_api_key(
    request: Request,
    body: ApiKeyCreate,
    current_user: User = Depends(get_current_user),
):
    """Generate a new API key. The raw key is returned once and cannot be retrieved again."""
    user_id = str(current_user.id)

    if ApiKey.count_active(user_id) >= MAX_KEYS_PER_USER:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum of {MAX_KEYS_PER_USER} active API keys allowed",
        )

    api_key, raw_key = ApiKey.create_key(user_id, body.name)

    return ApiKeyCreatedResponse(
        id=str(api_key.id),
        name=api_key.name,
        key=raw_key,
        key_prefix=api_key.key_prefix,
        created_at=api_key.created_at,
    )


@router.get("/auth/api-keys")
def list_api_keys(
    current_user: User = Depends(get_current_user),
):
    """List all active API keys for the current user."""
    keys = ApiKey.list_for_user(str(current_user.id))
    return {
        "keys": [
            ApiKeyListItem(
                id=str(k.id),
                name=k.name,
                key_prefix=k.key_prefix,
                created_at=k.created_at,
                last_used_at=k.last_used_at,
            )
            for k in keys
        ]
    }


@router.delete("/auth/api-keys/{key_id}")
def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
):
    """Revoke an API key."""
    revoked = ApiKey.revoke(key_id, str(current_user.id))
    if not revoked:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"ok": True, "message": "API key revoked"}
