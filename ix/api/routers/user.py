from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from ix.api.dependencies import get_current_user, get_db
from ix.db.models.user import User
from ix.db.models.user_preference import UserPreference

router = APIRouter()


class UserPreferencesUpdate(BaseModel):
    theme: Optional[str] = Field(None, max_length=20)
    language: Optional[str] = Field(None, max_length=10)
    timezone: Optional[str] = Field(None, max_length=50)
    settings: Optional[Dict[str, Any]] = None


@router.get("/user/preferences")
def get_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prefs = db.query(UserPreference).filter(UserPreference.user_id == str(current_user.id)).first()
    if not prefs:
        prefs = UserPreference(user_id=str(current_user.id))
        db.add(prefs)
        db.commit()
        db.refresh(prefs)

    return {
        "theme": prefs.theme,
        "language": prefs.language,
        "timezone": prefs.timezone,
        "settings": prefs.settings
    }

@router.put("/user/preferences")
def update_preferences(
    payload: UserPreferencesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prefs = db.query(UserPreference).filter(UserPreference.user_id == str(current_user.id)).first()
    if not prefs:
        prefs = UserPreference(user_id=str(current_user.id))
        db.add(prefs)

    if payload.theme is not None:
        prefs.theme = payload.theme
    if payload.language is not None:
        prefs.language = payload.language
    if payload.timezone is not None:
        prefs.timezone = payload.timezone
    if payload.settings is not None:
        prefs.settings = payload.settings

    db.commit()
    return {"ok": True}
