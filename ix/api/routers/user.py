from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from ix.api.dependencies import get_current_user, get_db
from ix.db.models.user import User

router = APIRouter()


class UserPreferencesUpdate(BaseModel):
    settings: Optional[Dict[str, Any]] = None


@router.get("/user/preferences")
def get_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == current_user.id).first()
    prefs = user.preferences if user and user.preferences else {}
    return {"settings": prefs}


@router.put("/user/preferences")
def update_preferences(
    payload: UserPreferencesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == current_user.id).first()
    if payload.settings is not None:
        current = user.preferences.copy() if user.preferences else {}
        current.update(payload.settings)
        user.preferences = current
    db.commit()
    return {"ok": True}
