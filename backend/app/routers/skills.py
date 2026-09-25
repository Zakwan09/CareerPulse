from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.services import analytics_service
from backend.app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.get("")
def list_skills(limit: int = 30, db: Session = Depends(get_db),
                 current_user: User = Depends(get_current_user)):
    return {"skills": analytics_service.top_skills(db, limit=limit)}


@router.get("/{skill_name}")
def skill_detail(skill_name: str, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    detail = analytics_service.skill_detail(db, skill_name)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found.")
    return detail


@router.get("/{skill_name}/trend")
def skill_trend(skill_name: str, db: Session = Depends(get_db),
                 current_user: User = Depends(get_current_user)):
    trend = analytics_service.skill_trend(db, skill_name)
    if not trend:
        raise HTTPException(status_code=404, detail=f"No trend data for skill '{skill_name}'.")
    return {"skill": skill_name, "trend": trend}
