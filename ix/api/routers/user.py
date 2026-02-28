from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any

from ix.api.dependencies import get_current_user, get_db
from ix.db.models.user import User
from ix.db.models.user_preference import UserPreference

router = APIRouter()

@router.get("/user/preferences")
def get_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prefs = db.query(UserPreference).filter(UserPreference.user_id == str(current_user.id)).first()
    if not prefs:
        # Create default preferences if they don't exist
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
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prefs = db.query(UserPreference).filter(UserPreference.user_id == str(current_user.id)).first()
    if not prefs:
        prefs = UserPreference(user_id=str(current_user.id))
        db.add(prefs)

    if "theme" in payload:
        prefs.theme = payload["theme"]
    if "language" in payload:
        prefs.language = payload["language"]
    if "timezone" in payload:
        prefs.timezone = payload["timezone"]
    if "settings" in payload:
        # Merge settings or overwrite? Overwriting for now for simplicity
        prefs.settings = payload["settings"]

    db.commit()
    return {"ok": True}
